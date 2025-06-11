import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import aiohttp
import aioredis
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class ProxyRule(str, Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    IP_HASH = "ip_hash"
    HEALTH_BASED = "health_based"

class BackendStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    MAINTENANCE = "maintenance"

@dataclass
class Backend:
    """Représente un backend pour le load balancing"""
    host: str
    port: int
    weight: int = 1
    max_connections: int = 100
    current_connections: int = 0
    status: BackendStatus = BackendStatus.HEALTHY
    last_health_check: Optional[datetime] = None
    response_time: float = 0.0
    error_count: int = 0
    success_count: int = 0
    
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"
    
    @property
    def health_ratio(self) -> float:
        total = self.success_count + self.error_count
        return self.success_count / total if total > 0 else 1.0

@dataclass
class ProxyTarget:
    """Configuration d'un target de proxy"""
    name: str
    backends: List[Backend]
    rule: ProxyRule = ProxyRule.ROUND_ROBIN
    health_check_path: str = "/health"
    health_check_interval: int = 30
    health_check_timeout: int = 5
    max_retries: int = 3
    retry_timeout: int = 1
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    sticky_sessions: bool = False
    
    def get_healthy_backends(self) -> List[Backend]:
        """Retourne uniquement les backends en bonne santé"""
        return [b for b in self.backends if b.status == BackendStatus.HEALTHY]

class CircuitBreaker:
    """Circuit breaker pour protéger les backends"""
    
    def __init__(self, threshold: int = 5, timeout: int = 60):
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def call_succeeded(self):
        """Marque un appel comme réussi"""
        self.failure_count = 0
        self.state = "closed"
    
    def call_failed(self):
        """Marque un appel comme échoué"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.threshold:
            self.state = "open"
    
    def can_attempt(self) -> bool:
        """Vérifie si on peut tenter un appel"""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            if self.last_failure_time and \
               (datetime.now() - self.last_failure_time).total_seconds() > self.timeout:
                self.state = "half-open"
                return True
            return False
        
        # half-open state
        return True

class ProxyManager:
    """Gestionnaire de proxy intelligent avec load balancing"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = None
        self.redis_url = redis_url
        
        # Configuration
        self.targets: Dict[str, ProxyTarget] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.session_store: Dict[str, str] = {}  # session_id -> backend_url
        
        # Métriques
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        
        # Workers
        self.health_check_task: Optional[asyncio.Task] = None
        self.running = False

    async def start(self):
        """Démarre le gestionnaire de proxy"""
        try:
            self.redis = await aioredis.from_url(self.redis_url)
            self.running = True
            
            # Charger les configurations
            await self._load_targets()
            
            # Démarrer le health checker
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            
            logger.info("Proxy Manager démarré")
            
        except Exception as e:
            logger.error(f"Erreur démarrage proxy manager: {e}")
            raise

    async def stop(self):
        """Arrête le gestionnaire de proxy"""
        self.running = False
        
        if self.health_check_task:
            self.health_check_task.cancel()
        
        if self.redis:
            await self.redis.close()
        
        logger.info("Proxy Manager arrêté")

    async def register_target(self, target: ProxyTarget):
        """Enregistre un nouveau target de proxy"""
        self.targets[target.name] = target
        
        # Initialiser les circuit breakers
        for backend in target.backends:
            key = f"{target.name}:{backend.host}:{backend.port}"
            self.circuit_breakers[key] = CircuitBreaker(
                target.circuit_breaker_threshold,
                target.circuit_breaker_timeout
            )
        
        # Sauvegarder en Redis
        await self._save_target(target)
        
        logger.info(f"Target {target.name} enregistré avec {len(target.backends)} backends")

    async def proxy_request(self, target_name: str, path: str, method: str = "GET", 
                          headers: Dict[str, str] = None, body: bytes = None,
                          client_ip: str = None, session_id: str = None) -> Tuple[int, Dict[str, str], bytes]:
        """Proxifie une requête vers un backend"""
        if target_name not in self.targets:
            return 404, {}, b"Target not found"
        
        target = self.targets[target_name]
        backend = await self._select_backend(target, client_ip, session_id)
        
        if not backend:
            return 503, {}, b"No healthy backends available"
        
        # Incrémenter les connexions
        backend.current_connections += 1
        
        try:
            return await self._make_request(target, backend, path, method, headers, body)
        finally:
            # Décrémenter les connexions
            backend.current_connections = max(0, backend.current_connections - 1)

    async def _select_backend(self, target: ProxyTarget, client_ip: str = None, 
                            session_id: str = None) -> Optional[Backend]:
        """Sélectionne un backend selon la règle configurée"""
        healthy_backends = target.get_healthy_backends()
        
        if not healthy_backends:
            return None
        
        # Sessions sticky
        if target.sticky_sessions and session_id:
            if session_id in self.session_store:
                backend_url = self.session_store[session_id]
                for backend in healthy_backends:
                    if backend.url == backend_url:
                        return backend
        
        # Sélection selon la règle
        if target.rule == ProxyRule.ROUND_ROBIN:
            return await self._round_robin_select(healthy_backends)
        elif target.rule == ProxyRule.LEAST_CONNECTIONS:
            return min(healthy_backends, key=lambda b: b.current_connections)
        elif target.rule == ProxyRule.WEIGHTED:
            return await self._weighted_select(healthy_backends)
        elif target.rule == ProxyRule.IP_HASH:
            return await self._ip_hash_select(healthy_backends, client_ip)
        elif target.rule == ProxyRule.HEALTH_BASED:
            return max(healthy_backends, key=lambda b: b.health_ratio)
        
        return healthy_backends[0]

    async def _round_robin_select(self, backends: List[Backend]) -> Backend:
        """Sélection round-robin"""
        # Utiliser Redis pour maintenir l'index global
        if self.redis:
            try:
                key = "selfstart:proxy:round_robin_index"
                index = await self.redis.incr(key)
                await self.redis.expire(key, 3600)
                return backends[index % len(backends)]
            except:
                pass
        
        # Fallback local
        return backends[int(time.time()) % len(backends)]

    async def _weighted_select(self, backends: List[Backend]) -> Backend:
        """Sélection pondérée"""
        total_weight = sum(b.weight for b in backends)
        if total_weight == 0:
            return backends[0]
        
        import random
        r = random.randint(1, total_weight)
        
        for backend in backends:
            r -= backend.weight
            if r <= 0:
                return backend
        
        return backends[-1]

    async def _ip_hash_select(self, backends: List[Backend], client_ip: str) -> Backend:
        """Sélection basée sur le hash de l'IP"""
        if not client_ip:
            return backends[0]
        
        import hashlib
        hash_value = int(hashlib.md5(client_ip.encode()).hexdigest(), 16)
        return backends[hash_value % len(backends)]

    async def _make_request(self, target: ProxyTarget, backend: Backend, 
                          path: str, method: str, headers: Dict[str, str], 
                          body: bytes) -> Tuple[int, Dict[str, str], bytes]:
        """Effectue la requête vers le backend"""
        circuit_breaker_key = f"{target.name}:{backend.host}:{backend.port}"
        circuit_breaker = self.circuit_breakers.get(circuit_breaker_key)
        
        if circuit_breaker and not circuit_breaker.can_attempt():
            return 503, {}, b"Circuit breaker open"
        
        url = f"{backend.url}{path}"
        start_time = time.time()
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    data=body
                ) as response:
                    response_body = await response.read()
                    response_headers = dict(response.headers)
                    
                    # Supprimer les headers problématiques
                    response_headers.pop('content-encoding', None)
                    response_headers.pop('transfer-encoding', None)
                    
                    # Métriques
                    response_time = time.time() - start_time
                    backend.response_time = response_time
                    backend.success_count += 1
                    
                    if circuit_breaker:
                        circuit_breaker.call_succeeded()
                    
                    # Métriques globales
                    self.request_count += 1
                    self.total_response_time += response_time
                    
                    return response.status, response_headers, response_body
        
        except Exception as e:
            logger.error(f"Erreur requête vers {backend.url}: {e}")
            
            # Métriques d'erreur
            backend.error_count += 1
            self.error_count += 1
            
            if circuit_breaker:
                circuit_breaker.call_failed()
            
            # Retry logic
            if target.max_retries > 0:
                return await self._retry_request(target, backend, path, method, headers, body)
            
            return 502, {}, b"Backend error"

    async def _retry_request(self, target: ProxyTarget, failed_backend: Backend,
                           path: str, method: str, headers: Dict[str, str], 
                           body: bytes) -> Tuple[int, Dict[str, str], bytes]:
        """Retry la requête sur d'autres backends"""
        healthy_backends = [b for b in target.get_healthy_backends() if b != failed_backend]
        
        for i in range(target.max_retries):
            if not healthy_backends:
                break
            
            backend = healthy_backends[i % len(healthy_backends)]
            
            try:
                await asyncio.sleep(target.retry_timeout)
                return await self._make_request(target, backend, path, method, headers, body)
            except:
                continue
        
        return 502, {}, b"All backends failed"

    async def _health_check_loop(self):
        """Boucle de vérification de santé des backends"""
        while self.running:
            try:
                for target in self.targets.values():
                    await self._check_target_health(target)
                
                await asyncio.sleep(10)  # Check toutes les 10 secondes
                
            except Exception as e:
                logger.error(f"Erreur health check loop: {e}")
                await asyncio.sleep(10)

    async def _check_target_health(self, target: ProxyTarget):
        """Vérifie la santé d'un target"""
        for backend in target.backends:
            if (datetime.now() - (backend.last_health_check or datetime.min)).total_seconds() \
               >= target.health_check_interval:
                await self._check_backend_health(target, backend)

    async def _check_backend_health(self, target: ProxyTarget, backend: Backend):
        """Vérifie la santé d'un backend"""
        url = f"{backend.url}{target.health_check_path}"
        
        try:
            timeout = aiohttp.ClientTimeout(total=target.health_check_timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        if backend.status != BackendStatus.HEALTHY:
                            logger.info(f"Backend {backend.url} est maintenant healthy")
                        backend.status = BackendStatus.HEALTHY
                    else:
                        backend.status = BackendStatus.UNHEALTHY
        
        except Exception as e:
            if backend.status == BackendStatus.HEALTHY:
                logger.warning(f"Backend {backend.url} est maintenant unhealthy: {e}")
            backend.status = BackendStatus.UNHEALTHY
        
        backend.last_health_check = datetime.now()

    async def _load_targets(self):
        """Charge les targets depuis Redis"""
        if not self.redis:
            return
        
        try:
            keys = await self.redis.keys("selfstart:proxy:target:*")
            for key in keys:
                data = await self.redis.get(key)
                if data:
                    import json
                    target_dict = json.loads(data)
                    # Reconstruction du target (simplifiée)
                    # Dans une vraie implémentation, utiliser un sérialiseur plus robuste
                    pass
            
        except Exception as e:
            logger.error(f"Erreur chargement targets: {e}")

    async def _save_target(self, target: ProxyTarget):
        """Sauvegarde un target en Redis"""
        if not self.redis:
            return
        
        try:
            import json
            key = f"selfstart:proxy:target:{target.name}"
            data = json.dumps(target.__dict__, default=str)
            await self.redis.set(key, data)
        except Exception as e:
            logger.error(f"Erreur sauvegarde target {target.name}: {e}")

    # API publique
    
    async def add_backend(self, target_name: str, backend: Backend):
        """Ajoute un backend à un target"""
        if target_name in self.targets:
            self.targets[target_name].backends.append(backend)
            
            # Initialiser le circuit breaker
            key = f"{target_name}:{backend.host}:{backend.port}"
            self.circuit_breakers[key] = CircuitBreaker()
            
            await self._save_target(self.targets[target_name])
            logger.info(f"Backend {backend.url} ajouté au target {target_name}")

    async def remove_backend(self, target_name: str, backend_url: str):
        """Retire un backend d'un target"""
        if target_name in self.targets:
            target = self.targets[target_name]
            target.backends = [b for b in target.backends if b.url != backend_url]
            await self._save_target(target)
            logger.info(f"Backend {backend_url} retiré du target {target_name}")

    async def set_backend_maintenance(self, target_name: str, backend_url: str, maintenance: bool):
        """Met un backend en maintenance"""
        if target_name in self.targets:
            for backend in self.targets[target_name].backends:
                if backend.url == backend_url:
                    backend.status = BackendStatus.MAINTENANCE if maintenance else BackendStatus.HEALTHY
                    logger.info(f"Backend {backend_url} {'en' if maintenance else 'hors'} maintenance")
                    break

    def get_target_status(self, target_name: str) -> Optional[Dict[str, Any]]:
        """Récupère le statut d'un target"""
        if target_name not in self.targets:
            return None
        
        target = self.targets[target_name]
        backends_status = []
        
        for backend in target.backends:
            backends_status.append({
                "url": backend.url,
                "status": backend.status.value,
                "current_connections": backend.current_connections,
                "response_time": backend.response_time,
                "health_ratio": backend.health_ratio,
                "last_health_check": backend.last_health_check.isoformat() if backend.last_health_check else None
            })
        
        return {
            "name": target.name,
            "rule": target.rule.value,
            "backends": backends_status,
            "healthy_backends": len(target.get_healthy_backends()),
            "total_backends": len(target.backends)
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Récupère les métriques du proxy"""
        avg_response_time = self.total_response_time / self.request_count if self.request_count > 0 else 0
        error_rate = self.error_count / self.request_count if self.request_count > 0 else 0
        
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": error_rate,
            "average_response_time": avg_response_time,
            "active_targets": len(self.targets),
            "total_backends": sum(len(t.backends) for t in self.targets.values()),
            "healthy_backends": sum(len(t.get_healthy_backends()) for t in self.targets.values())
        }