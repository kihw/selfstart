import asyncio
import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
import docker
import psutil
import aioredis
from service_discovery import ServiceDiscovery, ServiceDefinition, ServiceStatus

logger = logging.getLogger(__name__)

class ScalingDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    NONE = "none"

class ScalingTrigger(str, Enum):
    CPU_THRESHOLD = "cpu_threshold"
    MEMORY_THRESHOLD = "memory_threshold"
    NETWORK_THRESHOLD = "network_threshold"
    CUSTOM_METRIC = "custom_metric"
    SCHEDULED = "scheduled"
    MANUAL = "manual"

@dataclass
class ScalingMetrics:
    """Métriques utilisées pour les décisions de scaling"""
    cpu_percent: float
    memory_percent: float
    network_in_mbps: float
    network_out_mbps: float
    request_rate: float = 0.0
    response_time_ms: float = 0.0
    error_rate: float = 0.0
    queue_length: int = 0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class ScalingPolicy:
    """Politique de scaling pour un service"""
    service_name: str
    enabled: bool = True
    
    # Seuils de scaling up
    cpu_scale_up_threshold: float = 80.0
    memory_scale_up_threshold: float = 85.0
    network_scale_up_threshold: float = 100.0  # Mbps
    
    # Seuils de scaling down
    cpu_scale_down_threshold: float = 30.0
    memory_scale_down_threshold: float = 40.0
    network_scale_down_threshold: float = 20.0  # Mbps
    
    # Configuration cooldown
    scale_up_cooldown: int = 300  # 5 minutes
    scale_down_cooldown: int = 600  # 10 minutes
    
    # Limites de replicas
    min_replicas: int = 1
    max_replicas: int = 10
    
    # Configuration avancée
    evaluation_periods: int = 3  # Nombre de périodes à évaluer
    evaluation_interval: int = 60  # Intervalle entre évaluations (secondes)
    
    # Prédiction ML
    enable_prediction: bool = True
    prediction_window: int = 300  # Fenêtre de prédiction (secondes)

@dataclass
class ScalingEvent:
    """Événement de scaling"""
    service_name: str
    direction: ScalingDirection
    trigger: ScalingTrigger
    from_replicas: int
    to_replicas: int
    metrics: ScalingMetrics
    timestamp: datetime
    success: bool = False
    error_message: Optional[str] = None

class AutoScaler:
    """Système d'auto-scaling intelligent pour les services"""
    
    def __init__(self, service_discovery: ServiceDiscovery, redis_url: str = "redis://localhost:6379"):
        self.service_discovery = service_discovery
        self.docker_client = docker.from_env()
        self.redis = None
        self.redis_url = redis_url
        
        # Cache des métriques et politiques
        self.metrics_history: Dict[str, List[ScalingMetrics]] = {}
        self.scaling_policies: Dict[str, ScalingPolicy] = {}
        self.last_scaling_actions: Dict[str, datetime] = {}
        self.current_replicas: Dict[str, int] = {}
        
        # Configuration
        self.running = False
        self.evaluation_interval = 60  # secondes
        self.metrics_retention = 3600  # 1 heure de métriques
        
        # Prédicteur simple (Moving Average)
        self.prediction_enabled = True
        self.prediction_samples = 10

    async def start(self):
        """Démarre l'auto-scaler"""
        try:
            self.redis = await aioredis.from_url(self.redis_url)
            self.running = True
            
            # Charger les politiques existantes
            await self._load_scaling_policies()
            
            logger.info("Auto-scaler démarré")
            
            # Lancer les tâches d'auto-scaling
            asyncio.create_task(self._metrics_collection_loop())
            asyncio.create_task(self._scaling_evaluation_loop())
            asyncio.create_task(self._cleanup_loop())
            
        except Exception as e:
            logger.error(f"Erreur démarrage auto-scaler: {e}")
            raise

    async def stop(self):
        """Arrête l'auto-scaler"""
        self.running = False
        if self.redis:
            await self.redis.close()
        logger.info("Auto-scaler arrêté")

    async def _metrics_collection_loop(self):
        """Collecte périodique des métriques"""
        while self.running:
            try:
                await self._collect_metrics()
                await asyncio.sleep(30)  # Collecte toutes les 30 secondes
            except Exception as e:
                logger.error(f"Erreur collecte métriques: {e}")
                await asyncio.sleep(30)

    async def _scaling_evaluation_loop(self):
        """Évaluation périodique pour les décisions de scaling"""
        while self.running:
            try:
                await self._evaluate_scaling_decisions()
                await asyncio.sleep(self.evaluation_interval)
            except Exception as e:
                logger.error(f"Erreur évaluation scaling: {e}")
                await asyncio.sleep(self.evaluation_interval)

    async def _cleanup_loop(self):
        """Nettoyage des anciennes métriques"""
        while self.running:
            try:
                await self._cleanup_old_metrics()
                await asyncio.sleep(300)  # Nettoyage toutes les 5 minutes
            except Exception as e:
                logger.error(f"Erreur nettoyage: {e}")
                await asyncio.sleep(300)

    async def _collect_metrics(self):
        """Collecte les métriques pour tous les services"""
        services = await self.service_discovery.get_all_services()
        
        for service in services:
            if service.auto_scale_enabled and service.status == ServiceStatus.RUNNING:
                try:
                    metrics = await self._get_service_metrics(service)
                    if metrics:
                        await self._store_metrics(service.name, metrics)
                except Exception as e:
                    logger.error(f"Erreur collecte métriques {service.name}: {e}")

    async def _get_service_metrics(self, service: ServiceDefinition) -> Optional[ScalingMetrics]:
        """Collecte les métriques d'un service spécifique"""
        try:
            container = self.docker_client.containers.get(service.container_id)
            
            # Récupérer les stats du container
            stats = container.stats(stream=False)
            
            # Calculer CPU %
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                       stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                          stats["precpu_stats"]["system_cpu_usage"]
            cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0
            
            # Calculer mémoire %
            memory_usage = stats["memory_stats"]["usage"]
            memory_limit = stats["memory_stats"]["limit"]
            memory_percent = (memory_usage / memory_limit) * 100 if memory_limit > 0 else 0
            
            # Calculer réseau
            network_stats = stats["networks"]
            network_in_bytes = sum(net["rx_bytes"] for net in network_stats.values())
            network_out_bytes = sum(net["tx_bytes"] for net in network_stats.values())
            
            # Convertir en Mbps (approximation basée sur la dernière mesure)
            network_in_mbps = (network_in_bytes * 8) / (1024 * 1024) / 30  # sur 30 secondes
            network_out_mbps = (network_out_bytes * 8) / (1024 * 1024) / 30
            
            # Métriques applicatives (à implémenter selon le service)
            request_rate = await self._get_request_rate(service)
            response_time = await self._get_response_time(service)
            error_rate = await self._get_error_rate(service)
            
            return ScalingMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                network_in_mbps=network_in_mbps,
                network_out_mbps=network_out_mbps,
                request_rate=request_rate,
                response_time_ms=response_time,
                error_rate=error_rate
            )
            
        except Exception as e:
            logger.error(f"Erreur métriques service {service.name}: {e}")
            return None

    async def _get_request_rate(self, service: ServiceDefinition) -> float:
        """Récupère le taux de requêtes (à implémenter selon le service)"""
        # Placeholder - à implémenter avec des métriques réelles
        return 0.0

    async def _get_response_time(self, service: ServiceDefinition) -> float:
        """Récupère le temps de réponse moyen"""
        # Placeholder - à implémenter avec des métriques réelles
        return 0.0

    async def _get_error_rate(self, service: ServiceDefinition) -> float:
        """Récupère le taux d'erreur"""
        # Placeholder - à implémenter avec des métriques réelles
        return 0.0

    async def _store_metrics(self, service_name: str, metrics: ScalingMetrics):
        """Stocke les métriques en mémoire et Redis"""
        # Stockage en mémoire
        if service_name not in self.metrics_history:
            self.metrics_history[service_name] = []
        
        self.metrics_history[service_name].append(metrics)
        
        # Limiter la taille de l'historique
        max_history = self.metrics_retention // 30  # 30 secondes par mesure
        if len(self.metrics_history[service_name]) > max_history:
            self.metrics_history[service_name] = self.metrics_history[service_name][-max_history:]
        
        # Stockage Redis
        if self.redis:
            try:
                key = f"selfstart:metrics:{service_name}"
                data = {
                    "cpu_percent": metrics.cpu_percent,
                    "memory_percent": metrics.memory_percent,
                    "network_in_mbps": metrics.network_in_mbps,
                    "network_out_mbps": metrics.network_out_mbps,
                    "request_rate": metrics.request_rate,
                    "response_time_ms": metrics.response_time_ms,
                    "error_rate": metrics.error_rate,
                    "timestamp": metrics.timestamp.isoformat()
                }
                await self.redis.lpush(key, json.dumps(data))
                await self.redis.ltrim(key, 0, max_history - 1)
                await self.redis.expire(key, self.metrics_retention)
            except Exception as e:
                logger.error(f"Erreur stockage Redis métriques {service_name}: {e}")

    async def _evaluate_scaling_decisions(self):
        """Évalue les décisions de scaling pour tous les services"""
        for service_name, policy in self.scaling_policies.items():
            if policy.enabled:
                try:
                    decision = await self._make_scaling_decision(service_name, policy)
                    if decision != ScalingDirection.NONE:
                        await self._execute_scaling_action(service_name, decision, policy)
                except Exception as e:
                    logger.error(f"Erreur décision scaling {service_name}: {e}")

    async def _make_scaling_decision(self, service_name: str, policy: ScalingPolicy) -> ScalingDirection:
        """Prend une décision de scaling pour un service"""
        # Vérifier le cooldown
        if not await self._is_cooldown_expired(service_name, policy):
            return ScalingDirection.NONE
        
        # Récupérer les métriques récentes
        recent_metrics = self._get_recent_metrics(service_name, policy.evaluation_periods)
        if len(recent_metrics) < policy.evaluation_periods:
            return ScalingDirection.NONE
        
        # Calculer les moyennes
        avg_cpu = statistics.mean([m.cpu_percent for m in recent_metrics])
        avg_memory = statistics.mean([m.memory_percent for m in recent_metrics])
        avg_network = statistics.mean([
            max(m.network_in_mbps, m.network_out_mbps) for m in recent_metrics
        ])
        
        # Prédiction si activée
        if policy.enable_prediction and self.prediction_enabled:
            predicted_cpu = await self._predict_metric(service_name, "cpu_percent")
            predicted_memory = await self._predict_metric(service_name, "memory_percent")
            
            # Pondérer les décisions avec la prédiction
            avg_cpu = (avg_cpu * 0.7) + (predicted_cpu * 0.3)
            avg_memory = (avg_memory * 0.7) + (predicted_memory * 0.3)
        
        # Récupérer le nombre actuel de replicas
        current_replicas = await self._get_current_replicas(service_name)
        
        # Décision de scaling up
        if (avg_cpu > policy.cpu_scale_up_threshold or 
            avg_memory > policy.memory_scale_up_threshold or
            avg_network > policy.network_scale_up_threshold):
            
            if current_replicas < policy.max_replicas:
                logger.info(f"Scaling UP décidé pour {service_name}: "
                           f"CPU={avg_cpu:.1f}%, MEM={avg_memory:.1f}%, NET={avg_network:.1f}Mbps")
                return ScalingDirection.UP
        
        # Décision de scaling down
        elif (avg_cpu < policy.cpu_scale_down_threshold and 
              avg_memory < policy.memory_scale_down_threshold and
              avg_network < policy.network_scale_down_threshold):
            
            if current_replicas > policy.min_replicas:
                logger.info(f"Scaling DOWN décidé pour {service_name}: "
                           f"CPU={avg_cpu:.1f}%, MEM={avg_memory:.1f}%, NET={avg_network:.1f}Mbps")
                return ScalingDirection.DOWN
        
        return ScalingDirection.NONE

    async def _predict_metric(self, service_name: str, metric_name: str) -> float:
        """Prédiction simple basée sur la moyenne mobile"""
        metrics = self._get_recent_metrics(service_name, self.prediction_samples)
        if len(metrics) < 3:
            return 0.0
        
        values = [getattr(m, metric_name) for m in metrics[-self.prediction_samples:]]
        
        # Moyenne mobile pondérée
        weights = [i + 1 for i in range(len(values))]
        weighted_avg = sum(w * v for w, v in zip(weights, values)) / sum(weights)
        
        # Tendance simple
        if len(values) >= 2:
            trend = (values[-1] - values[0]) / len(values)
            return max(0, weighted_avg + trend * 3)  # Prédiction 3 périodes en avant
        
        return weighted_avg

    def _get_recent_metrics(self, service_name: str, count: int) -> List[ScalingMetrics]:
        """Récupère les métriques récentes d'un service"""
        if service_name not in self.metrics_history:
            return []
        return self.metrics_history[service_name][-count:]

    async def _is_cooldown_expired(self, service_name: str, policy: ScalingPolicy) -> bool:
        """Vérifie si la période de cooldown est expirée"""
        if service_name not in self.last_scaling_actions:
            return True
        
        last_action = self.last_scaling_actions[service_name]
        now = datetime.now()
        
        # Utiliser le cooldown approprié selon la dernière action
        # (Logique simplifiée - à améliorer pour distinguer up/down)
        cooldown = min(policy.scale_up_cooldown, policy.scale_down_cooldown)
        
        return (now - last_action).total_seconds() >= cooldown

    async def _get_current_replicas(self, service_name: str) -> int:
        """Récupère le nombre actuel de replicas d'un service"""
        if service_name in self.current_replicas:
            return self.current_replicas[service_name]
        
        # Pour l'instant, on considère 1 replica par défaut (Docker simple)
        # À améliorer pour Docker Swarm ou Kubernetes
        service = await self.service_discovery.get_service(service_name)
        return 1 if service and service.status == ServiceStatus.RUNNING else 0

    async def _execute_scaling_action(self, service_name: str, direction: ScalingDirection, policy: ScalingPolicy):
        """Exécute une action de scaling"""
        try:
            current_replicas = await self._get_current_replicas(service_name)
            
            if direction == ScalingDirection.UP:
                new_replicas = min(current_replicas + 1, policy.max_replicas)
            else:  # DOWN
                new_replicas = max(current_replicas - 1, policy.min_replicas)
            
            if new_replicas == current_replicas:
                return
            
            # Récupérer les métriques actuelles
            recent_metrics = self._get_recent_metrics(service_name, 1)
            current_metrics = recent_metrics[0] if recent_metrics else ScalingMetrics(0, 0, 0, 0)
            
            # Exécuter le scaling
            success = await self._scale_service(service_name, new_replicas)
            
            # Enregistrer l'événement
            event = ScalingEvent(
                service_name=service_name,
                direction=direction,
                trigger=ScalingTrigger.CPU_THRESHOLD,  # Simplification
                from_replicas=current_replicas,
                to_replicas=new_replicas,
                metrics=current_metrics,
                timestamp=datetime.now(),
                success=success
            )
            
            await self._record_scaling_event(event)
            
            if success:
                self.current_replicas[service_name] = new_replicas
                self.last_scaling_actions[service_name] = datetime.now()
                logger.info(f"Scaling {direction.value} réussi pour {service_name}: "
                           f"{current_replicas} -> {new_replicas}")
            else:
                logger.error(f"Échec scaling {direction.value} pour {service_name}")
                
        except Exception as e:
            logger.error(f"Erreur exécution scaling {service_name}: {e}")

    async def _scale_service(self, service_name: str, target_replicas: int) -> bool:
        """Effectue le scaling d'un service"""
        try:
            # Pour Docker simple, on ne peut que start/stop
            # Pour un vrai scaling, il faudrait Docker Swarm ou Kubernetes
            
            service = await self.service_discovery.get_service(service_name)
            if not service:
                return False
            
            current_replicas = await self._get_current_replicas(service_name)
            
            if target_replicas > current_replicas:
                # Scale up - pour l'instant, on se contente de s'assurer que le service tourne
                container = self.docker_client.containers.get(service.container_id)
                if container.status != "running":
                    container.start()
                return True
                
            elif target_replicas < current_replicas:
                # Scale down - arrêter le container si target = 0
                if target_replicas == 0:
                    container = self.docker_client.containers.get(service.container_id)
                    container.stop()
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur scaling service {service_name}: {e}")
            return False

    async def _record_scaling_event(self, event: ScalingEvent):
        """Enregistre un événement de scaling"""
        if self.redis:
            try:
                key = f"selfstart:scaling_events:{event.service_name}"
                data = {
                    "direction": event.direction.value,
                    "trigger": event.trigger.value,
                    "from_replicas": event.from_replicas,
                    "to_replicas": event.to_replicas,
                    "timestamp": event.timestamp.isoformat(),
                    "success": event.success,
                    "error_message": event.error_message
                }
                await self.redis.lpush(key, json.dumps(data))
                await self.redis.ltrim(key, 0, 100)  # Garder les 100 derniers événements
                await self.redis.expire(key, 86400 * 7)  # 7 jours
            except Exception as e:
                logger.error(f"Erreur enregistrement événement: {e}")

    async def _load_scaling_policies(self):
        """Charge les politiques de scaling depuis Redis"""
        if not self.redis:
            return
        
        try:
            keys = await self.redis.keys("selfstart:scaling_policy:*")
            for key in keys:
                service_name = key.decode().split(":")[-1]
                data = await self.redis.get(key)
                if data:
                    policy_dict = json.loads(data)
                    policy = ScalingPolicy(**policy_dict)
                    self.scaling_policies[service_name] = policy
            
            logger.info(f"Chargé {len(self.scaling_policies)} politiques de scaling")
        except Exception as e:
            logger.error(f"Erreur chargement politiques: {e}")

    async def _cleanup_old_metrics(self):
        """Nettoie les anciennes métriques"""
        cutoff = datetime.now() - timedelta(seconds=self.metrics_retention)
        
        for service_name in list(self.metrics_history.keys()):
            metrics = self.metrics_history[service_name]
            # Filtrer les métriques trop anciennes
            self.metrics_history[service_name] = [
                m for m in metrics if m.timestamp > cutoff
            ]
            
            # Supprimer l'entrée si vide
            if not self.metrics_history[service_name]:
                del self.metrics_history[service_name]

    # API publique
    
    async def set_scaling_policy(self, service_name: str, policy: ScalingPolicy):
        """Définit une politique de scaling pour un service"""
        self.scaling_policies[service_name] = policy
        
        if self.redis:
            try:
                key = f"selfstart:scaling_policy:{service_name}"
                data = json.dumps(policy.__dict__)
                await self.redis.set(key, data)
            except Exception as e:
                logger.error(f"Erreur sauvegarde politique {service_name}: {e}")
        
        logger.info(f"Politique de scaling mise à jour pour {service_name}")

    async def get_scaling_policy(self, service_name: str) -> Optional[ScalingPolicy]:
        """Récupère la politique de scaling d'un service"""
        return self.scaling_policies.get(service_name)

    async def get_all_scaling_policies(self) -> Dict[str, ScalingPolicy]:
        """Récupère toutes les politiques de scaling"""
        return self.scaling_policies.copy()

    async def manual_scale(self, service_name: str, target_replicas: int) -> bool:
        """Effectue un scaling manuel"""
        try:
            current_replicas = await self._get_current_replicas(service_name)
            success = await self._scale_service(service_name, target_replicas)
            
            if success:
                # Enregistrer l'événement manuel
                recent_metrics = self._get_recent_metrics(service_name, 1)
                current_metrics = recent_metrics[0] if recent_metrics else ScalingMetrics(0, 0, 0, 0)
                
                direction = ScalingDirection.UP if target_replicas > current_replicas else ScalingDirection.DOWN
                event = ScalingEvent(
                    service_name=service_name,
                    direction=direction,
                    trigger=ScalingTrigger.MANUAL,
                    from_replicas=current_replicas,
                    to_replicas=target_replicas,
                    metrics=current_metrics,
                    timestamp=datetime.now(),
                    success=True
                )
                
                await self._record_scaling_event(event)
                self.current_replicas[service_name] = target_replicas
                self.last_scaling_actions[service_name] = datetime.now()
                
                logger.info(f"Scaling manuel réussi pour {service_name}: {current_replicas} -> {target_replicas}")
            
            return success
            
        except Exception as e:
            logger.error(f"Erreur scaling manuel {service_name}: {e}")
            return False

    async def get_scaling_events(self, service_name: str, limit: int = 20) -> List[ScalingEvent]:
        """Récupère l'historique des événements de scaling"""
        events = []
        
        if self.redis:
            try:
                key = f"selfstart:scaling_events:{service_name}"
                data_list = await self.redis.lrange(key, 0, limit - 1)
                
                for data in data_list:
                    event_dict = json.loads(data)
                    # Reconstruction simplifiée de l'événement
                    events.append(ScalingEvent(
                        service_name=service_name,
                        direction=ScalingDirection(event_dict["direction"]),
                        trigger=ScalingTrigger(event_dict["trigger"]),
                        from_replicas=event_dict["from_replicas"],
                        to_replicas=event_dict["to_replicas"],
                        metrics=ScalingMetrics(0, 0, 0, 0),  # Placeholder
                        timestamp=datetime.fromisoformat(event_dict["timestamp"]),
                        success=event_dict["success"],
                        error_message=event_dict.get("error_message")
                    ))
            except Exception as e:
                logger.error(f"Erreur récupération événements {service_name}: {e}")
        
        return events

    def get_scaling_metrics(self) -> Dict[str, Any]:
        """Récupère les métriques globales de l'auto-scaler"""
        total_services = len(self.scaling_policies)
        active_services = len([p for p in self.scaling_policies.values() if p.enabled])
        
        return {
            "total_policies": total_services,
            "active_policies": active_services,
            "services_with_metrics": len(self.metrics_history),
            "total_metrics_points": sum(len(metrics) for metrics in self.metrics_history.values()),
            "last_evaluation": datetime.now().isoformat(),
            "prediction_enabled": self.prediction_enabled
        }
