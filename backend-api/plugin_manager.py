import asyncio
import importlib
import inspect
import json
import logging
import os
import sys
import tempfile
import zipfile
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Type
from dataclasses import dataclass
from enum import Enum
import aiofiles
import aiohttp
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class PluginStatus(str, Enum):
    INSTALLED = "installed"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    UPDATING = "updating"

class PluginType(str, Enum):
    MONITORING = "monitoring"
    NOTIFICATION = "notification"
    STORAGE = "storage"
    SECURITY = "security"
    AUTOMATION = "automation"
    INTEGRATION = "integration"
    UI_EXTENSION = "ui_extension"

class HookType(str, Enum):
    BEFORE_CONTAINER_START = "before_container_start"
    AFTER_CONTAINER_START = "after_container_start"
    BEFORE_CONTAINER_STOP = "before_container_stop"
    AFTER_CONTAINER_STOP = "after_container_stop"
    ON_SERVICE_DISCOVERY = "on_service_discovery"
    ON_SCALING_EVENT = "on_scaling_event"
    ON_HEALTH_CHECK = "on_health_check"
    ON_METRICS_COLLECTION = "on_metrics_collection"
    ON_API_REQUEST = "on_api_request"
    ON_WEBHOOK_TRIGGER = "on_webhook_trigger"

@dataclass
class PluginManifest:
    """Manifeste d'un plugin"""
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    entry_point: str
    dependencies: List[str] = None
    permissions: List[str] = None
    config_schema: Dict[str, Any] = None
    hooks: List[HookType] = None
    min_selfstart_version: str = "0.3.0"
    max_selfstart_version: str = None
    website: str = None
    repository: str = None
    license: str = "MIT"
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.permissions is None:
            self.permissions = []
        if self.config_schema is None:
            self.config_schema = {}
        if self.hooks is None:
            self.hooks = []

@dataclass
class PluginInfo:
    """Informations sur un plugin installé"""
    manifest: PluginManifest
    status: PluginStatus
    installed_at: datetime
    last_updated: datetime
    config: Dict[str, Any]
    error_message: Optional[str] = None
    module_path: Optional[str] = None

class SelfStartPlugin(ABC):
    """Classe de base pour tous les plugins SelfStart"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"plugin.{self.__class__.__name__}")
        self.selfstart_api = None  # Sera injecté par le PluginManager
        
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialise le plugin. Retourne True si succès."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> bool:
        """Nettoie les ressources du plugin."""
        pass
    
    async def on_config_update(self, new_config: Dict[str, Any]):
        """Appelé quand la configuration change."""
        self.config = new_config
    
    def get_hooks(self) -> Dict[HookType, Callable]:
        """Retourne les hooks implémentés par ce plugin."""
        hooks = {}
        for hook_type in HookType:
            method_name = f"hook_{hook_type.value}"
            if hasattr(self, method_name):
                hooks[hook_type] = getattr(self, method_name)
        return hooks

class PluginAPI:
    """API exposée aux plugins pour interagir avec SelfStart"""
    
    def __init__(self, service_discovery, auto_scaler, webhook_manager):
        self.service_discovery = service_discovery
        self.auto_scaler = auto_scaler
        self.webhook_manager = webhook_manager
        self._event_bus = {}
    
    async def get_service(self, name: str):
        """Récupère un service"""
        return await self.service_discovery.get_service(name)
    
    async def get_all_services(self):
        """Récupère tous les services"""
        return await self.service_discovery.get_all_services()
    
    async def trigger_webhook(self, event_type: str, data: Dict[str, Any]):
        """Déclenche un webhook"""
        return await self.webhook_manager.trigger_event(event_type, data=data)
    
    async def scale_service(self, service_name: str, replicas: int):
        """Scale un service"""
        return await self.auto_scaler.manual_scale(service_name, replicas)
    
    async def emit_event(self, event_name: str, data: Any):
        """Émet un événement sur le bus d'événements"""
        if event_name in self._event_bus:
            for callback in self._event_bus[event_name]:
                try:
                    await callback(data)
                except Exception as e:
                    logger.error(f"Erreur callback événement {event_name}: {e}")
    
    def subscribe_event(self, event_name: str, callback: Callable):
        """S'abonne à un événement"""
        if event_name not in self._event_bus:
            self._event_bus[event_name] = []
        self._event_bus[event_name].append(callback)

class PluginManager:
    """Gestionnaire de plugins extensible"""
    
    def __init__(self, plugins_dir: str = "plugins", marketplace_url: str = None):
        self.plugins_dir = plugins_dir
        self.marketplace_url = marketplace_url or "https://plugins.selfstart.dev"
        
        # Storage
        self.installed_plugins: Dict[str, PluginInfo] = {}
        self.active_plugins: Dict[str, SelfStartPlugin] = {}
        self.hooks: Dict[HookType, List[Callable]] = {}
        
        # API pour les plugins
        self.plugin_api = None
        
        # Configuration
        self.enable_hot_reload = True
        self.max_plugin_size = 50 * 1024 * 1024  # 50MB
        self.allowed_permissions = [
            "read_services", "write_services", "read_metrics", 
            "write_metrics", "execute_commands", "network_access"
        ]
        
        # Initialisation
        os.makedirs(plugins_dir, exist_ok=True)

    def set_plugin_api(self, service_discovery, auto_scaler, webhook_manager):
        """Configure l'API disponible pour les plugins"""
        self.plugin_api = PluginAPI(service_discovery, auto_scaler, webhook_manager)

    async def start(self):
        """Démarre le gestionnaire de plugins"""
        logger.info("Démarrage du gestionnaire de plugins")
        
        # Charger les plugins installés
        await self._load_installed_plugins()
        
        # Activer les plugins configurés comme actifs
        for plugin_name, plugin_info in self.installed_plugins.items():
            if plugin_info.status == PluginStatus.ACTIVE:
                await self._activate_plugin(plugin_name)
        
        logger.info(f"Gestionnaire de plugins démarré - {len(self.active_plugins)} plugins actifs")

    async def stop(self):
        """Arrête le gestionnaire de plugins"""
        logger.info("Arrêt du gestionnaire de plugins")
        
        # Désactiver tous les plugins
        for plugin_name in list(self.active_plugins.keys()):
            await self._deactivate_plugin(plugin_name)

    async def _load_installed_plugins(self):
        """Charge la liste des plugins installés"""
        try:
            for plugin_dir in os.listdir(self.plugins_dir):
                plugin_path = os.path.join(self.plugins_dir, plugin_dir)
                if os.path.isdir(plugin_path):
                    manifest_path = os.path.join(plugin_path, "manifest.json")
                    if os.path.exists(manifest_path):
                        try:
                            with open(manifest_path, 'r') as f:
                                manifest_data = json.load(f)
                            
                            manifest = PluginManifest(**manifest_data)
                            
                            # Charger la configuration
                            config_path = os.path.join(plugin_path, "config.json")
                            config = {}
                            if os.path.exists(config_path):
                                with open(config_path, 'r') as f:
                                    config = json.load(f)
                            
                            plugin_info = PluginInfo(
                                manifest=manifest,
                                status=PluginStatus.INSTALLED,
                                installed_at=datetime.fromtimestamp(os.path.getctime(plugin_path)),
                                last_updated=datetime.fromtimestamp(os.path.getmtime(plugin_path)),
                                config=config,
                                module_path=plugin_path
                            )
                            
                            self.installed_plugins[manifest.name] = plugin_info
                            
                        except Exception as e:
                            logger.error(f"Erreur chargement plugin {plugin_dir}: {e}")
                            
        except Exception as e:
            logger.error(f"Erreur chargement plugins: {e}")

    async def install_plugin(self, source: str, enable: bool = True) -> bool:
        """Installe un plugin depuis une source (URL, fichier local, marketplace)"""
        try:
            # Déterminer le type de source
            if source.startswith("http"):
                return await self._install_from_url(source, enable)
            elif source.endswith(".zip"):
                return await self._install_from_zip(source, enable)
            else:
                # Essayer depuis le marketplace
                return await self._install_from_marketplace(source, enable)
                
        except Exception as e:
            logger.error(f"Erreur installation plugin {source}: {e}")
            return False

    async def _install_from_url(self, url: str, enable: bool) -> bool:
        """Installe un plugin depuis une URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Erreur téléchargement plugin: {response.status}")
                        return False
                    
                    # Vérifier la taille
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > self.max_plugin_size:
                        logger.error(f"Plugin trop volumineux: {content_length} bytes")
                        return False
                    
                    # Télécharger dans un fichier temporaire
                    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
                        async for chunk in response.content.iter_chunked(8192):
                            tmp_file.write(chunk)
                        tmp_file.flush()
                        
                        return await self._install_from_zip(tmp_file.name, enable)
                        
        except Exception as e:
            logger.error(f"Erreur installation depuis URL {url}: {e}")
            return False

    async def _install_from_zip(self, zip_path: str, enable: bool) -> bool:
        """Installe un plugin depuis un fichier ZIP"""
        try:
            # Extraire et valider
            with tempfile.TemporaryDirectory() as tmp_dir:
                with zipfile.ZipFile(zip_path, 'r') as zip_file:
                    zip_file.extractall(tmp_dir)
                
                # Chercher le manifest
                manifest_path = os.path.join(tmp_dir, "manifest.json")
                if not os.path.exists(manifest_path):
                    logger.error("Manifest.json manquant dans le plugin")
                    return False
                
                # Charger et valider le manifest
                with open(manifest_path, 'r') as f:
                    manifest_data = json.load(f)
                
                manifest = PluginManifest(**manifest_data)
                
                # Vérifier la compatibilité
                if not self._is_compatible(manifest):
                    logger.error(f"Plugin {manifest.name} incompatible")
                    return False
                
                # Vérifier les permissions
                if not self._check_permissions(manifest):
                    logger.error(f"Permissions non autorisées pour {manifest.name}")
                    return False
                
                # Installer
                plugin_dir = os.path.join(self.plugins_dir, manifest.name)
                if os.path.exists(plugin_dir):
                    # Mise à jour
                    import shutil
                    shutil.rmtree(plugin_dir)
                
                import shutil
                shutil.copytree(tmp_dir, plugin_dir)
                
                # Créer l'info du plugin
                plugin_info = PluginInfo(
                    manifest=manifest,
                    status=PluginStatus.ACTIVE if enable else PluginStatus.INSTALLED,
                    installed_at=datetime.now(),
                    last_updated=datetime.now(),
                    config={},
                    module_path=plugin_dir
                )
                
                self.installed_plugins[manifest.name] = plugin_info
                
                # Activer si demandé
                if enable:
                    await self._activate_plugin(manifest.name)
                
                logger.info(f"Plugin {manifest.name} installé avec succès")
                return True
                
        except Exception as e:
            logger.error(f"Erreur installation ZIP {zip_path}: {e}")
            return False

    async def _install_from_marketplace(self, plugin_name: str, enable: bool) -> bool:
        """Installe un plugin depuis le marketplace"""
        try:
            # Récupérer les infos du marketplace
            url = f"{self.marketplace_url}/api/plugins/{plugin_name}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Plugin {plugin_name} introuvable sur le marketplace")
                        return False
                    
                    plugin_data = await response.json()
                    download_url = plugin_data.get("download_url")
                    
                    if not download_url:
                        logger.error(f"URL de téléchargement manquante pour {plugin_name}")
                        return False
                    
                    return await self._install_from_url(download_url, enable)
                    
        except Exception as e:
            logger.error(f"Erreur installation marketplace {plugin_name}: {e}")
            return False

    def _is_compatible(self, manifest: PluginManifest) -> bool:
        """Vérifie la compatibilité d'un plugin"""
        # Vérification de version simplifiée
        current_version = "0.3.0"  # Version actuelle de SelfStart
        
        if manifest.min_selfstart_version:
            # Comparaison de version simplifiée
            min_parts = [int(x) for x in manifest.min_selfstart_version.split('.')]
            current_parts = [int(x) for x in current_version.split('.')]
            
            if current_parts < min_parts:
                return False
        
        return True

    def _check_permissions(self, manifest: PluginManifest) -> bool:
        """Vérifie les permissions d'un plugin"""
        for permission in manifest.permissions:
            if permission not in self.allowed_permissions:
                return False
        return True

    async def _activate_plugin(self, plugin_name: str) -> bool:
        """Active un plugin"""
        try:
            if plugin_name not in self.installed_plugins:
                logger.error(f"Plugin {plugin_name} non installé")
                return False
            
            plugin_info = self.installed_plugins[plugin_name]
            
            # Ajouter le répertoire du plugin au path Python
            plugin_path = plugin_info.module_path
            if plugin_path not in sys.path:
                sys.path.insert(0, plugin_path)
            
            # Importer le module
            module_name = plugin_info.manifest.entry_point.split('.')[0]
            class_name = plugin_info.manifest.entry_point.split('.')[1]
            
            spec = importlib.util.spec_from_file_location(
                module_name, 
                os.path.join(plugin_path, f"{module_name}.py")
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Instancier la classe du plugin
            plugin_class = getattr(module, class_name)
            plugin_instance = plugin_class(plugin_info.config)
            
            # Injecter l'API SelfStart
            plugin_instance.selfstart_api = self.plugin_api
            
            # Initialiser
            if await plugin_instance.initialize():
                self.active_plugins[plugin_name] = plugin_instance
                plugin_info.status = PluginStatus.ACTIVE
                
                # Enregistrer les hooks
                hooks = plugin_instance.get_hooks()
                for hook_type, callback in hooks.items():
                    if hook_type not in self.hooks:
                        self.hooks[hook_type] = []
                    self.hooks[hook_type].append(callback)
                
                logger.info(f"Plugin {plugin_name} activé avec succès")
                return True
            else:
                plugin_info.status = PluginStatus.ERROR
                plugin_info.error_message = "Échec de l'initialisation"
                return False
                
        except Exception as e:
            logger.error(f"Erreur activation plugin {plugin_name}: {e}")
            if plugin_name in self.installed_plugins:
                self.installed_plugins[plugin_name].status = PluginStatus.ERROR
                self.installed_plugins[plugin_name].error_message = str(e)
            return False

    async def _deactivate_plugin(self, plugin_name: str) -> bool:
        """Désactive un plugin"""
        try:
            if plugin_name not in self.active_plugins:
                return True
            
            plugin_instance = self.active_plugins[plugin_name]
            
            # Nettoyer les hooks
            for hook_type in list(self.hooks.keys()):
                self.hooks[hook_type] = [
                    callback for callback in self.hooks[hook_type]
                    if callback.__self__ != plugin_instance
                ]
                if not self.hooks[hook_type]:
                    del self.hooks[hook_type]
            
            # Nettoyer le plugin
            await plugin_instance.cleanup()
            
            # Retirer de la liste active
            del self.active_plugins[plugin_name]
            
            # Mettre à jour le statut
            if plugin_name in self.installed_plugins:
                self.installed_plugins[plugin_name].status = PluginStatus.INSTALLED
            
            logger.info(f"Plugin {plugin_name} désactivé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur désactivation plugin {plugin_name}: {e}")
            return False

    async def trigger_hook(self, hook_type: HookType, *args, **kwargs) -> List[Any]:
        """Déclenche un hook et retourne les résultats"""
        results = []
        
        if hook_type in self.hooks:
            for callback in self.hooks[hook_type]:
                try:
                    if inspect.iscoroutinefunction(callback):
                        result = await callback(*args, **kwargs)
                    else:
                        result = callback(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Erreur hook {hook_type}: {e}")
                    results.append({"error": str(e)})
        
        return results

    # API publique

    async def enable_plugin(self, plugin_name: str) -> bool:
        """Active un plugin"""
        return await self._activate_plugin(plugin_name)

    async def disable_plugin(self, plugin_name: str) -> bool:
        """Désactive un plugin"""
        return await self._deactivate_plugin(plugin_name)

    async def uninstall_plugin(self, plugin_name: str) -> bool:
        """Désinstalle un plugin"""
        try:
            # Désactiver d'abord
            await self._deactivate_plugin(plugin_name)
            
            # Supprimer les fichiers
            if plugin_name in self.installed_plugins:
                plugin_path = self.installed_plugins[plugin_name].module_path
                if plugin_path and os.path.exists(plugin_path):
                    import shutil
                    shutil.rmtree(plugin_path)
                
                del self.installed_plugins[plugin_name]
            
            logger.info(f"Plugin {plugin_name} désinstallé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur désinstallation plugin {plugin_name}: {e}")
            return False

    async def update_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> bool:
        """Met à jour la configuration d'un plugin"""
        try:
            if plugin_name not in self.installed_plugins:
                return False
            
            plugin_info = self.installed_plugins[plugin_name]
            plugin_info.config = config
            
            # Sauvegarder la configuration
            config_path = os.path.join(plugin_info.module_path, "config.json")
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Notifier le plugin actif si applicable
            if plugin_name in self.active_plugins:
                plugin_instance = self.active_plugins[plugin_name]
                await plugin_instance.on_config_update(config)
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur mise à jour config {plugin_name}: {e}")
            return False

    def get_installed_plugins(self) -> Dict[str, PluginInfo]:
        """Retourne la liste des plugins installés"""
        return self.installed_plugins.copy()

    def get_active_plugins(self) -> List[str]:
        """Retourne la liste des plugins actifs"""
        return list(self.active_plugins.keys())

    async def get_marketplace_plugins(self) -> List[Dict[str, Any]]:
        """Récupère la liste des plugins disponibles sur le marketplace"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.marketplace_url}/api/plugins") as response:
                    if response.status == 200:
                        return await response.json()
                    return []
        except Exception as e:
            logger.error(f"Erreur récupération marketplace: {e}")
            return []

    def get_plugin_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques du système de plugins"""
        total_installed = len(self.installed_plugins)
        total_active = len(self.active_plugins)
        total_hooks = sum(len(hooks) for hooks in self.hooks.values())
        
        return {
            "total_installed": total_installed,
            "total_active": total_active,
            "total_hooks": total_hooks,
            "hooks_by_type": {
                hook_type.value: len(callbacks) 
                for hook_type, callbacks in self.hooks.items()
            },
            "plugins_by_type": {
                plugin_type.value: len([
                    p for p in self.installed_plugins.values() 
                    if p.manifest.plugin_type == plugin_type
                ])
                for plugin_type in PluginType
            },
            "plugins_by_status": {
                status.value: len([
                    p for p in self.installed_plugins.values() 
                    if p.status == status
                ])
                for status in PluginStatus
            }
        }

# Plugins de base fournis avec SelfStart

class PrometheusMetricsPlugin(SelfStartPlugin):
    """Plugin pour exposer les métriques Prometheus"""
    
    async def initialize(self) -> bool:
        try:
            from prometheus_client import start_http_server, Counter, Gauge, Histogram
            
            self.request_counter = Counter('selfstart_requests_total', 'Total requests', ['method', 'endpoint'])
            self.container_gauge = Gauge('selfstart_containers_total', 'Total containers', ['status'])
            self.response_time = Histogram('selfstart_response_time_seconds', 'Response time')
            
            # Démarrer le serveur Prometheus
            port = self.config.get('port', 9090)
            start_http_server(port)
            
            self.logger.info(f"Serveur Prometheus démarré sur le port {port}")
            return True
        except Exception as e:
            self.logger.error(f"Erreur initialisation Prometheus: {e}")
            return False
    
    async def cleanup(self) -> bool:
        # Le serveur Prometheus se ferme automatiquement
        return True
    
    async def hook_on_api_request(self, method: str, endpoint: str, response_time: float):
        """Hook appelé sur chaque requête API"""
        self.request_counter.labels(method=method, endpoint=endpoint).inc()
        self.response_time.observe(response_time)
    
    async def hook_on_service_discovery(self, services: List):
        """Hook appelé lors de la découverte de services"""
        status_counts = {}
        for service in services:
            status = service.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            self.container_gauge.labels(status=status).set(count)

class SlackNotificationPlugin(SelfStartPlugin):
    """Plugin pour les notifications Slack"""
    
    async def initialize(self) -> bool:
        self.webhook_url = self.config.get('webhook_url')
        if not self.webhook_url:
            self.logger.error("URL webhook Slack manquante")
            return False
        return True
    
    async def cleanup(self) -> bool:
        return True
    
    async def hook_after_container_start(self, container_name: str, success: bool):
        """Notifie Slack après le démarrage d'un container"""
        if success:
            message = f"✅ Container `{container_name}` démarré avec succès"
            color = "good"
        else:
            message = f"❌ Échec du démarrage du container `{container_name}`"
            color = "danger"
        
        await self._send_slack_message(message, color)
    
    async def hook_on_scaling_event(self, service_name: str, direction: str, replicas: int):
        """Notifie Slack lors d'un événement de scaling"""
        message = f"📈 Scaling {direction} du service `{service_name}` vers {replicas} replicas"
        await self._send_slack_message(message, "warning")
    
    async def _send_slack_message(self, message: str, color: str = "good"):
        """Envoie un message à Slack"""
        try:
            payload = {
                "attachments": [{
                    "color": color,
                    "text": message,
                    "footer": "SelfStart",
                    "ts": int(datetime.now().timestamp())
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status != 200:
                        self.logger.error(f"Erreur envoi Slack: {response.status}")
        except Exception as e:
            self.logger.error(f"Erreur notification Slack: {e}")
