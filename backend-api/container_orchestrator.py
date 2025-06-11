import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import docker
import aioredis
from docker_manager import DockerManager

logger = logging.getLogger(__name__)

class ContainerState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    UNHEALTHY = "unhealthy"

class StartupStrategy(str, Enum):
    IMMEDIATE = "immediate"
    LAZY = "lazy"
    SCHEDULED = "scheduled"
    DEPENDENCY_BASED = "dependency_based"

@dataclass
class ContainerConfig:
    """Configuration avancée pour un container"""
    name: str
    image: str
    ports: Dict[int, int]
    environment: Dict[str, str]
    volumes: Dict[str, str]
    labels: Dict[str, str]
    dependencies: List[str]
    startup_strategy: StartupStrategy
    health_check: Optional[Dict[str, Any]]
    resource_limits: Optional[Dict[str, Any]]
    auto_remove: bool = False
    restart_policy: str = "unless-stopped"
    startup_timeout: int = 120
    shutdown_timeout: int = 30

@dataclass
class ContainerStatus:
    """État détaillé d'un container"""
    name: str
    state: ContainerState
    container_id: Optional[str]
    started_at: Optional[datetime]
    last_health_check: Optional[datetime]
    health_status: str = "unknown"
    resource_usage: Dict[str, float] = None
    error_message: Optional[str] = None
    restart_count: int = 0

class ContainerOrchestrator:
    """Orchestrateur avancé pour la gestion des containers"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.docker_manager = DockerManager()
        self.docker_client = docker.from_env()
        self.redis = None
        self.redis_url = redis_url
        
        # État des containers
        self.containers: Dict[str, ContainerStatus] = {}
        self.configs: Dict[str, ContainerConfig] = {}
        self.startup_queue: asyncio.Queue = asyncio.Queue()
        
        # Configuration
        self.max_concurrent_starts = 3
        self.health_check_interval = 30
        self.dependency_timeout = 300
        
        # Workers
        self.startup_workers: List[asyncio.Task] = []
        self.health_check_task: Optional[asyncio.Task] = None
        self.running = False

    async def start(self):
        """Démarre l'orchestrateur"""
        try:
            self.redis = await aioredis.from_url(self.redis_url)
            self.running = True
            
            # Charger les configurations
            await self._load_configurations()
            
            # Démarrer les workers
            for i in range(self.max_concurrent_starts):
                worker = asyncio.create_task(self._startup_worker(f"worker-{i}"))
                self.startup_workers.append(worker)
            
            # Démarrer le health checker
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            
            logger.info("Container Orchestrator démarré")
            
        except Exception as e:
            logger.error(f"Erreur démarrage orchestrateur: {e}")
            raise

    async def stop(self):
        """Arrête l'orchestrateur"""
        self.running = False
        
        # Arrêter les workers
        for worker in self.startup_workers:
            worker.cancel()
        
        if self.health_check_task:
            self.health_check_task.cancel()
        
        if self.redis:
            await self.redis.close()
        
        logger.info("Container Orchestrator arrêté")

    async def register_container(self, config: ContainerConfig):
        """Enregistre une nouvelle configuration de container"""
        self.configs[config.name] = config
        
        # Initialiser le status
        if config.name not in self.containers:
            self.containers[config.name] = ContainerStatus(
                name=config.name,
                state=ContainerState.STOPPED,
                container_id=None,
                started_at=None,
                last_health_check=None
            )
        
        # Sauvegarder en Redis
        await self._save_config(config)
        
        logger.info(f"Container {config.name} enregistré")

    async def start_container(self, name: str, force: bool = False) -> bool:
        """Démarre un container avec gestion des dépendances"""
        if name not in self.configs:
            logger.error(f"Container {name} non configuré")
            return False
        
        config = self.configs[name]
        status = self.containers[name]
        
        # Vérifier l'état actuel
        if status.state == ContainerState.RUNNING and not force:
            logger.info(f"Container {name} déjà en cours d'exécution")
            return True
        
        if status.state == ContainerState.STARTING:
            logger.info(f"Container {name} déjà en cours de démarrage")
            return True
        
        # Marquer comme en cours de démarrage
        status.state = ContainerState.STARTING
        await self._update_status(status)
        
        try:
            # Démarrer les dépendances d'abord
            if config.dependencies:
                await self._start_dependencies(config.dependencies)
            
            # Ajouter à la queue de démarrage
            await self.startup_queue.put((name, config))
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur démarrage {name}: {e}")
            status.state = ContainerState.ERROR
            status.error_message = str(e)
            await self._update_status(status)
            return False

    async def stop_container(self, name: str, force: bool = False) -> bool:
        """Arrête un container"""
        if name not in self.containers:
            return False
        
        status = self.containers[name]
        
        if status.state == ContainerState.STOPPED:
            return True
        
        try:
            status.state = ContainerState.STOPPING
            await self._update_status(status)
            
            # Arrêter le container Docker
            if status.container_id:
                container = self.docker_client.containers.get(status.container_id)
                container.stop(timeout=self.configs[name].shutdown_timeout)
            
            status.state = ContainerState.STOPPED
            status.container_id = None
            await self._update_status(status)
            
            logger.info(f"Container {name} arrêté")
            return True
            
        except Exception as e:
            logger.error(f"Erreur arrêt {name}: {e}")
            status.state = ContainerState.ERROR
            status.error_message = str(e)
            await self._update_status(status)
            return False

    async def get_container_status(self, name: str) -> Optional[ContainerStatus]:
        """Récupère le statut d'un container"""
        return self.containers.get(name)

    async def _startup_worker(self, worker_name: str):
        """Worker pour démarrer les containers"""
        logger.info(f"Startup worker {worker_name} démarré")
        
        while self.running:
            try:
                # Attendre un container à démarrer
                name, config = await asyncio.wait_for(
                    self.startup_queue.get(), 
                    timeout=1.0
                )
                
                await self._execute_startup(name, config)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Erreur worker {worker_name}: {e}")

    async def _execute_startup(self, name: str, config: ContainerConfig):
        """Exécute le démarrage d'un container"""
        status = self.containers[name]
        
        try:
            logger.info(f"Démarrage de {name}...")
            
            # Vérifier si le container existe déjà
            existing_container = None
            try:
                existing_container = self.docker_client.containers.get(name)
                if existing_container.status == "running":
                    status.state = ContainerState.RUNNING
                    status.container_id = existing_container.id
                    status.started_at = datetime.now()
                    await self._update_status(status)
                    return
                elif existing_container.status in ["exited", "created"]:
                    existing_container.remove()
            except docker.errors.NotFound:
                pass
            
            # Créer et démarrer le container
            container = self.docker_client.containers.run(
                image=config.image,
                name=name,
                ports=config.ports,
                environment=config.environment,
                volumes=config.volumes,
                labels=config.labels,
                detach=True,
                restart_policy={"Name": config.restart_policy},
                remove=config.auto_remove
            )
            
            # Attendre que le container soit prêt
            await self._wait_for_container_ready(container, config)
            
            # Mettre à jour le statut
            status.state = ContainerState.RUNNING
            status.container_id = container.id
            status.started_at = datetime.now()
            status.error_message = None
            await self._update_status(status)
            
            logger.info(f"Container {name} démarré avec succès")
            
        except Exception as e:
            logger.error(f"Erreur démarrage {name}: {e}")
            status.state = ContainerState.ERROR
            status.error_message = str(e)
            await self._update_status(status)

    async def _wait_for_container_ready(self, container, config: ContainerConfig):
        """Attend qu'un container soit prêt"""
        timeout = config.startup_timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            container.reload()
            
            if container.status == "running":
                # Vérifier le health check si configuré
                if config.health_check:
                    if await self._check_container_health(container, config.health_check):
                        return
                else:
                    # Attendre un peu pour que l'application soit prête
                    await asyncio.sleep(5)
                    return
            elif container.status in ["exited", "dead"]:
                raise Exception(f"Container {container.name} a échoué au démarrage")
            
            await asyncio.sleep(2)
        
        raise Exception(f"Timeout démarrage container {container.name}")

    async def _check_container_health(self, container, health_config: Dict[str, Any]) -> bool:
        """Vérifie la santé d'un container"""
        try:
            if health_config.get("type") == "http":
                import aiohttp
                url = health_config.get("url", "http://localhost/health")
                timeout = health_config.get("timeout", 5)
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=timeout) as response:
                        return response.status == 200
            
            elif health_config.get("type") == "command":
                command = health_config.get("command")
                result = container.exec_run(command)
                return result.exit_code == 0
            
            return True
            
        except Exception as e:
            logger.debug(f"Health check échoué: {e}")
            return False

    async def _start_dependencies(self, dependencies: List[str]):
        """Démarre les dépendances d'un container"""
        for dep_name in dependencies:
            if dep_name in self.containers:
                dep_status = self.containers[dep_name]
                if dep_status.state != ContainerState.RUNNING:
                    logger.info(f"Démarrage de la dépendance {dep_name}")
                    await self.start_container(dep_name)
                    
                    # Attendre que la dépendance soit prête
                    timeout = self.dependency_timeout
                    start_time = time.time()
                    
                    while time.time() - start_time < timeout:
                        if self.containers[dep_name].state == ContainerState.RUNNING:
                            break
                        await asyncio.sleep(2)
                    else:
                        raise Exception(f"Timeout dépendance {dep_name}")

    async def _health_check_loop(self):
        """Boucle de vérification de santé"""
        while self.running:
            try:
                for name, status in self.containers.items():
                    if status.state == ContainerState.RUNNING and status.container_id:
                        await self._perform_health_check(name, status)
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Erreur health check loop: {e}")
                await asyncio.sleep(self.health_check_interval)

    async def _perform_health_check(self, name: str, status: ContainerStatus):
        """Effectue un health check sur un container"""
        try:
            container = self.docker_client.containers.get(status.container_id)
            container.reload()
            
            if container.status != "running":
                status.state = ContainerState.UNHEALTHY
                status.health_status = f"Container status: {container.status}"
            else:
                # Health check personnalisé si configuré
                config = self.configs.get(name)
                if config and config.health_check:
                    is_healthy = await self._check_container_health(container, config.health_check)
                    status.health_status = "healthy" if is_healthy else "unhealthy"
                    if not is_healthy:
                        status.state = ContainerState.UNHEALTHY
                else:
                    status.health_status = "healthy"
            
            status.last_health_check = datetime.now()
            await self._update_status(status)
            
        except docker.errors.NotFound:
            status.state = ContainerState.STOPPED
            status.container_id = None
            await self._update_status(status)
        except Exception as e:
            logger.error(f"Erreur health check {name}: {e}")

    async def _load_configurations(self):
        """Charge les configurations depuis Redis"""
        if not self.redis:
            return
        
        try:
            keys = await self.redis.keys("selfstart:container:*")
            for key in keys:
                data = await self.redis.get(key)
                if data:
                    config_dict = json.loads(data)
                    config = ContainerConfig(**config_dict)
                    self.configs[config.name] = config
                    
                    # Initialiser le status
                    if config.name not in self.containers:
                        self.containers[config.name] = ContainerStatus(
                            name=config.name,
                            state=ContainerState.STOPPED,
                            container_id=None,
                            started_at=None,
                            last_health_check=None
                        )
            
            logger.info(f"Chargé {len(self.configs)} configurations")
            
        except Exception as e:
            logger.error(f"Erreur chargement configurations: {e}")

    async def _save_config(self, config: ContainerConfig):
        """Sauvegarde une configuration en Redis"""
        if not self.redis:
            return
        
        try:
            key = f"selfstart:container:{config.name}"
            data = json.dumps(config.__dict__, default=str)
            await self.redis.set(key, data)
        except Exception as e:
            logger.error(f"Erreur sauvegarde config {config.name}: {e}")

    async def _update_status(self, status: ContainerStatus):
        """Met à jour le statut d'un container"""
        if not self.redis:
            return
        
        try:
            key = f"selfstart:status:{status.name}"
            data = json.dumps(status.__dict__, default=str)
            await self.redis.setex(key, 3600, data)  # TTL 1 heure
        except Exception as e:
            logger.error(f"Erreur mise à jour status {status.name}: {e}")

    # API publique
    
    async def get_all_containers(self) -> Dict[str, ContainerStatus]:
        """Récupère tous les statuts de containers"""
        return self.containers.copy()

    async def get_container_logs(self, name: str, lines: int = 100) -> str:
        """Récupère les logs d'un container"""
        status = self.containers.get(name)
        if not status or not status.container_id:
            return f"Container {name} non trouvé ou arrêté"
        
        try:
            container = self.docker_client.containers.get(status.container_id)
            logs = container.logs(tail=lines, timestamps=True).decode('utf-8')
            return logs
        except Exception as e:
            return f"Erreur récupération logs: {e}"

    async def restart_container(self, name: str) -> bool:
        """Redémarre un container"""
        await self.stop_container(name)
        await asyncio.sleep(2)
        return await self.start_container(name)

    def get_metrics(self) -> Dict[str, Any]:
        """Récupère les métriques de l'orchestrateur"""
        states = {}
        for status in self.containers.values():
            state = status.state.value
            states[state] = states.get(state, 0) + 1
        
        return {
            "total_containers": len(self.containers),
            "states": states,
            "queue_size": self.startup_queue.qsize(),
            "active_workers": len([w for w in self.startup_workers if not w.done()]),
            "last_update": datetime.now().isoformat()
        }