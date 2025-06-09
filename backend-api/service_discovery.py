import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from enum import Enum
import docker
import aioredis
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ServiceStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class ServiceType(str, Enum):
    WEB = "web"
    API = "api" 
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    MONITORING = "monitoring"
    UTILITY = "utility"

@dataclass
class ServiceEndpoint:
    """Représente un endpoint d'un service"""
    protocol: str = "http"
    host: str = "localhost"
    port: int = 80
    path: str = "/"
    health_check_path: str = "/health"
    
    @property
    def url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}{self.path}"
    
    @property
    def health_url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}{self.health_check_path}"

@dataclass
class ServiceDefinition:
    """Définition complète d'un service découvert"""
    name: str
    container_id: str
    image: str
    status: ServiceStatus
    service_type: ServiceType
    endpoints: List[ServiceEndpoint]
    labels: Dict[str, str]
    dependencies: List[str]
    environment: Dict[str, str]
    created_at: datetime
    last_seen: datetime
    health_score: float = 1.0
    auto_scale_enabled: bool = False
    min_replicas: int = 1
    max_replicas: int = 5
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour sérialisation"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['last_seen'] = self.last_seen.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceDefinition':
        """Crée une instance depuis un dictionnaire"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_seen'] = datetime.fromisoformat(data['last_seen'])
        data['endpoints'] = [ServiceEndpoint(**ep) for ep in data['endpoints']]
        return cls(**data)

class ServiceDiscovery:
    """Service Discovery automatique pour containers Docker"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.docker_client = docker.from_env()
        self.redis = None
        self.redis_url = redis_url
        self.services: Dict[str, ServiceDefinition] = {}
        self.discovery_interval = 30  # secondes
        self.health_check_interval = 60  # secondes
        self.service_ttl = 300  # TTL en secondes
        self.running = False
        
        # Labels requis pour qu'un container soit découvert
        self.required_labels = {
            "selfstart.enable": "true"
        }
        
        # Labels optionnels pour enrichir la découverte
        self.optional_labels = {
            "selfstart.type": ServiceType.WEB,
            "selfstart.port": "80",
            "selfstart.path": "/",
            "selfstart.health_path": "/health",
            "selfstart.protocol": "http",
            "selfstart.dependencies": "",
            "selfstart.auto_scale": "false",
            "selfstart.min_replicas": "1",
            "selfstart.max_replicas": "5"
        }

    async def start(self):
        """Démarre le service discovery"""
        try:
            self.redis = await aioredis.from_url(self.redis_url)
            self.running = True
            logger.info("Service Discovery démarré")
            
            # Lancer les tâches de découverte en arrière-plan
            asyncio.create_task(self._discovery_loop())
            asyncio.create_task(self._health_check_loop())
            asyncio.create_task(self._cleanup_loop())
            
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du Service Discovery: {e}")
            raise

    async def stop(self):
        """Arrête le service discovery"""
        self.running = False
        if self.redis:
            await self.redis.close()
        logger.info("Service Discovery arrêté")

    async def _discovery_loop(self):
        """Boucle principale de découverte des services"""
        while self.running:
            try:
                await self._discover_services()
                await asyncio.sleep(self.discovery_interval)
            except Exception as e:
                logger.error(f"Erreur dans la boucle de découverte: {e}")
                await asyncio.sleep(self.discovery_interval)

    async def _health_check_loop(self):
        """Boucle de vérification de santé des services"""
        while self.running:
            try:
                await self._check_services_health()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Erreur dans la vérification de santé: {e}")
                await asyncio.sleep(self.health_check_interval)

    async def _cleanup_loop(self):
        """Boucle de nettoyage des services obsolètes"""
        while self.running:
            try:
                await self._cleanup_stale_services()
                await asyncio.sleep(self.service_ttl)
            except Exception as e:
                logger.error(f"Erreur dans le nettoyage: {e}")
                await asyncio.sleep(self.service_ttl)

    async def _discover_services(self):
        """Découvre automatiquement les services disponibles"""
        try:
            discovered_services = {}
            
            # Parcourir tous les containers
            for container in self.docker_client.containers.list(all=True):
                if self._should_discover_container(container):
                    service = await self._create_service_definition(container)
                    if service:
                        discovered_services[service.name] = service
                        await self._store_service(service)
            
            # Mettre à jour le cache local
            self.services = discovered_services
            logger.info(f"Découverte terminée: {len(discovered_services)} services trouvés")
            
        except Exception as e:
            logger.error(f"Erreur lors de la découverte: {e}")

    def _should_discover_container(self, container) -> bool:
        """Détermine si un container doit être découvert"""
        labels = container.labels or {}
        
        # Vérifier les labels requis
        for label, value in self.required_labels.items():
            if labels.get(label) != value:
                return False
        
        return True

    async def _create_service_definition(self, container) -> Optional[ServiceDefinition]:
        """Crée une définition de service à partir d'un container"""
        try:
            labels = container.labels or {}
            
            # Extraire les informations du container
            name = container.name
            container_id = container.id[:12]
            image = container.image.tags[0] if container.image.tags else "unknown"
            
            # Déterminer le statut
            status_map = {
                "running": ServiceStatus.RUNNING,
                "exited": ServiceStatus.STOPPED,
                "created": ServiceStatus.STOPPED,
                "restarting": ServiceStatus.STARTING,
                "paused": ServiceStatus.STOPPED,
                "dead": ServiceStatus.UNHEALTHY
            }
            status = status_map.get(container.status, ServiceStatus.UNKNOWN)
            
            # Extraire le type de service
            service_type = ServiceType(labels.get("selfstart.type", "web"))
            
            # Créer les endpoints
            endpoints = self._extract_endpoints(container, labels)
            
            # Extraire les dépendances
            dependencies = []
            deps_str = labels.get("selfstart.dependencies", "")
            if deps_str:
                dependencies = [dep.strip() for dep in deps_str.split(",")]
            
            # Configuration auto-scaling
            auto_scale_enabled = labels.get("selfstart.auto_scale", "false").lower() == "true"
            min_replicas = int(labels.get("selfstart.min_replicas", "1"))
            max_replicas = int(labels.get("selfstart.max_replicas", "5"))
            
            # Variables d'environnement
            environment = {}
            if hasattr(container, 'attrs') and 'Config' in container.attrs:
                env_list = container.attrs['Config'].get('Env', [])
                for env_var in env_list:
                    if '=' in env_var:
                        key, value = env_var.split('=', 1)
                        environment[key] = value
            
            now = datetime.now()
            
            service = ServiceDefinition(
                name=name,
                container_id=container_id,
                image=image,
                status=status,
                service_type=service_type,
                endpoints=endpoints,
                labels=labels,
                dependencies=dependencies,
                environment=environment,
                created_at=now,
                last_seen=now,
                auto_scale_enabled=auto_scale_enabled,
                min_replicas=min_replicas,
                max_replicas=max_replicas
            )
            
            return service
            
        except Exception as e:
            logger.error(f"Erreur création service pour {container.name}: {e}")
            return None

    def _extract_endpoints(self, container, labels: Dict[str, str]) -> List[ServiceEndpoint]:
        """Extrait les endpoints d'un container"""
        endpoints = []
        
        try:
            # Port principal depuis les labels
            main_port = int(labels.get("selfstart.port", "80"))
            protocol = labels.get("selfstart.protocol", "http")
            path = labels.get("selfstart.path", "/")
            health_path = labels.get("selfstart.health_path", "/health")
            
            # Essayer de récupérer l'IP du container
            host = container.name  # Utiliser le nom du container par défaut
            
            # Si le container a une IP dans le réseau SelfStart
            if hasattr(container, 'attrs') and 'NetworkSettings' in container.attrs:
                networks = container.attrs['NetworkSettings'].get('Networks', {})
                for network_name, network_info in networks.items():
                    if 'selfstart' in network_name.lower():
                        host = network_info.get('IPAddress', host)
                        break
            
            main_endpoint = ServiceEndpoint(
                protocol=protocol,
                host=host,
                port=main_port,
                path=path,
                health_check_path=health_path
            )
            endpoints.append(main_endpoint)
            
            # Endpoints additionnels depuis les ports exposés
            if hasattr(container, 'ports') and container.ports:
                for port_binding in container.ports:
                    if port_binding != f"{main_port}/tcp":
                        try:
                            port_num = int(port_binding.split('/')[0])
                            additional_endpoint = ServiceEndpoint(
                                protocol="http",
                                host=host,
                                port=port_num,
                                path="/",
                                health_check_path="/health"
                            )
                            endpoints.append(additional_endpoint)
                        except:
                            pass
            
        except Exception as e:
            logger.error(f"Erreur extraction endpoints: {e}")
            # Endpoint par défaut
            endpoints = [ServiceEndpoint()]
        
        return endpoints

    async def _store_service(self, service: ServiceDefinition):
        """Stocke un service dans Redis"""
        try:
            if self.redis:
                key = f"selfstart:service:{service.name}"
                data = json.dumps(service.to_dict())
                await self.redis.setex(key, self.service_ttl, data)
                
                # Ajouter à l'index des services
                await self.redis.sadd("selfstart:services", service.name)
                
        except Exception as e:
            logger.error(f"Erreur stockage service {service.name}: {e}")

    async def _check_services_health(self):
        """Vérifie la santé de tous les services découverts"""
        import aiohttp
        
        for service_name, service in self.services.items():
            try:
                health_score = 0.0
                endpoint_count = len(service.endpoints)
                
                async with aiohttp.ClientSession() as session:
                    for endpoint in service.endpoints:
                        try:
                            async with session.get(
                                endpoint.health_url,
                                timeout=aiohttp.ClientTimeout(total=5)
                            ) as response:
                                if response.status == 200:
                                    health_score += 1.0
                        except:
                            pass
                
                # Calculer le score de santé
                if endpoint_count > 0:
                    service.health_score = health_score / endpoint_count
                else:
                    service.health_score = 0.0
                
                # Mettre à jour le statut si nécessaire
                if service.health_score == 0 and service.status == ServiceStatus.RUNNING:
                    service.status = ServiceStatus.UNHEALTHY
                elif service.health_score > 0 and service.status == ServiceStatus.UNHEALTHY:
                    service.status = ServiceStatus.RUNNING
                
                service.last_seen = datetime.now()
                await self._store_service(service)
                
            except Exception as e:
                logger.error(f"Erreur vérification santé {service_name}: {e}")

    async def _cleanup_stale_services(self):
        """Nettoie les services obsolètes"""
        try:
            cutoff_time = datetime.now() - timedelta(seconds=self.service_ttl)
            stale_services = []
            
            for service_name, service in self.services.items():
                if service.last_seen < cutoff_time:
                    stale_services.append(service_name)
            
            for service_name in stale_services:
                del self.services[service_name]
                if self.redis:
                    await self.redis.delete(f"selfstart:service:{service_name}")
                    await self.redis.srem("selfstart:services", service_name)
            
            if stale_services:
                logger.info(f"Nettoyage: {len(stale_services)} services obsolètes supprimés")
                
        except Exception as e:
            logger.error(f"Erreur nettoyage: {e}")

    # API publique
    
    async def get_service(self, name: str) -> Optional[ServiceDefinition]:
        """Récupère un service par nom"""
        if name in self.services:
            return self.services[name]
        
        # Essayer de récupérer depuis Redis
        if self.redis:
            try:
                key = f"selfstart:service:{name}"
                data = await self.redis.get(key)
                if data:
                    service_dict = json.loads(data)
                    return ServiceDefinition.from_dict(service_dict)
            except Exception as e:
                logger.error(f"Erreur récupération service {name}: {e}")
        
        return None

    async def get_all_services(self) -> List[ServiceDefinition]:
        """Récupère tous les services découverts"""
        return list(self.services.values())

    async def get_services_by_type(self, service_type: ServiceType) -> List[ServiceDefinition]:
        """Récupère les services d'un type donné"""
        return [s for s in self.services.values() if s.service_type == service_type]

    async def get_healthy_services(self) -> List[ServiceDefinition]:
        """Récupère uniquement les services en bonne santé"""
        return [s for s in self.services.values() if s.health_score > 0.5]

    async def register_service_manually(self, service: ServiceDefinition):
        """Enregistre manuellement un service"""
        self.services[service.name] = service
        await self._store_service(service)
        logger.info(f"Service {service.name} enregistré manuellement")

    async def unregister_service(self, name: str):
        """Désenregistre un service"""
        if name in self.services:
            del self.services[name]
        
        if self.redis:
            await self.redis.delete(f"selfstart:service:{name}")
            await self.redis.srem("selfstart:services", name)
        
        logger.info(f"Service {name} désenregistré")

    async def get_service_dependencies(self, name: str) -> List[ServiceDefinition]:
        """Récupère les dépendances d'un service"""
        service = await self.get_service(name)
        if not service:
            return []
        
        dependencies = []
        for dep_name in service.dependencies:
            dep_service = await self.get_service(dep_name)
            if dep_service:
                dependencies.append(dep_service)
        
        return dependencies

    async def get_service_dependents(self, name: str) -> List[ServiceDefinition]:
        """Récupère les services qui dépendent de ce service"""
        dependents = []
        for service in self.services.values():
            if name in service.dependencies:
                dependents.append(service)
        return dependents

    def get_service_metrics(self) -> Dict[str, Any]:
        """Récupère les métriques du service discovery"""
        total_services = len(self.services)
        healthy_services = len([s for s in self.services.values() if s.health_score > 0.5])
        running_services = len([s for s in self.services.values() if s.status == ServiceStatus.RUNNING])
        
        return {
            "total_services": total_services,
            "healthy_services": healthy_services,
            "running_services": running_services,
            "health_ratio": healthy_services / total_services if total_services > 0 else 0,
            "services_by_type": {
                service_type.value: len([s for s in self.services.values() if s.service_type == service_type])
                for service_type in ServiceType
            },
            "last_discovery": max([s.last_seen for s in self.services.values()], default=datetime.now()).isoformat()
        }
