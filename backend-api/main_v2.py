from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import asyncio
import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import aioredis
import uvicorn

# Imports des nouveaux modules
from docker_manager import DockerManager
from service_discovery import ServiceDiscovery, ServiceDefinition, ServiceStatus, ServiceType
from auto_scaler import AutoScaler, ScalingPolicy, ScalingDirection, ScalingTrigger
from plugin_manager import PluginManager, PluginInfo, PluginStatus, HookType
from template_engine import TemplateEngine, ConfigurationRenderer, TemplateContext, initialize_default_templates
from webhook_manager import WebhookManager
from autoshutdown_manager import AutoShutdownManager

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Modèles Pydantic v2
class ServiceCreate(BaseModel):
    name: str
    image: str
    port: int
    environment: Dict[str, str] = {}
    labels: Dict[str, str] = {}

class ScalingPolicyCreate(BaseModel):
    service_name: str
    enabled: bool = True
    cpu_scale_up_threshold: float = 80.0
    cpu_scale_down_threshold: float = 30.0
    memory_scale_up_threshold: float = 85.0
    memory_scale_down_threshold: float = 40.0
    min_replicas: int = 1
    max_replicas: int = 10

class PluginInstall(BaseModel):
    source: str
    enable: bool = True

class TemplateCreate(BaseModel):
    name: str
    content: str

class WebhookCreate(BaseModel):
    name: str
    url: str
    events: List[str]
    enabled: bool = True

# Initialisation de l'application FastAPI v2
app = FastAPI(
    title="SelfStart API v2",
    description="API avancée pour la gestion automatique de containers Docker avec découverte de services, auto-scaling et plugins",
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sécurité basique
security = HTTPBearer(auto_error=False)

# Variables globales pour les gestionnaires
docker_manager = None
service_discovery = None
auto_scaler = None
plugin_manager = None
template_engine = None
config_renderer = None
webhook_manager = None
autoshutdown_manager = None
redis_client = None

# WebSocket pour les événements temps réel
websocket_connections: List[WebSocket] = []

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    global docker_manager, service_discovery, auto_scaler, plugin_manager
    global template_engine, config_renderer, webhook_manager, autoshutdown_manager, redis_client
    
    logger.info("🚀 Démarrage de SelfStart API v2...")
    
    try:
        # Redis pour le cache et les données partagées
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_client = await aioredis.from_url(redis_url)
        
        # Initialisation des gestionnaires
        docker_manager = DockerManager()
        
        service_discovery = ServiceDiscovery(redis_url)
        await service_discovery.start()
        
        auto_scaler = AutoScaler(service_discovery, redis_url)
        await auto_scaler.start()
        
        webhook_manager = WebhookManager()
        
        autoshutdown_manager = AutoShutdownManager()
        
        plugin_manager = PluginManager()
        plugin_manager.set_plugin_api(service_discovery, auto_scaler, webhook_manager)
        await plugin_manager.start()
        
        template_engine = TemplateEngine()
        await initialize_default_templates(template_engine)
        
        config_renderer = ConfigurationRenderer(template_engine, service_discovery)
        
        logger.info("✅ SelfStart API v2 initialisé avec succès")
        
    except Exception as e:
        logger.error(f"❌ Erreur initialisation: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage à l'arrêt"""
    logger.info("🛑 Arrêt de SelfStart API v2...")
    
    try:
        if plugin_manager:
            await plugin_manager.stop()
        if auto_scaler:
            await auto_scaler.stop()
        if service_discovery:
            await service_discovery.stop()
        if redis_client:
            await redis_client.close()
        
        logger.info("✅ SelfStart API v2 arrêté proprement")
    except Exception as e:
        logger.error(f"❌ Erreur arrêt: {e}")

# Middleware pour authentification (optionnel)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Authentification basique (à améliorer)"""
    if os.getenv("ENABLE_AUTH", "false").lower() == "true":
        if not credentials:
            raise HTTPException(status_code=401, detail="Authentication required")
        # Validation du token (simplifiée)
        expected_token = os.getenv("API_TOKEN", "secret")
        if credentials.credentials != expected_token:
            raise HTTPException(status_code=401, detail="Invalid token")
    return "authenticated"

# WebSocket pour événements temps réel
@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket pour les événements temps réel"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        while True:
            # Garder la connexion ouverte
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)

async def broadcast_event(event_type: str, data: Any):
    """Diffuse un événement à tous les clients WebSocket connectés"""
    if websocket_connections:
        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        
        for websocket in websocket_connections.copy():
            try:
                await websocket.send_text(message)
            except:
                websocket_connections.remove(websocket)

# ===============================
# ENDPOINTS API v1 (Compatibilité)
# ===============================

@app.get("/health")
async def health_check():
    """Point de santé pour les health checks"""
    return {"status": "healthy", "service": "selfstart-api-v2", "version": "0.3.0"}

@app.get("/")
async def root():
    """Point d'entrée racine de l'API"""
    return {
        "message": "SelfStart API v2",
        "version": "0.3.0",
        "docs": "/docs",
        "websocket": "/ws/events",
        "features": [
            "service_discovery",
            "auto_scaling", 
            "plugin_system",
            "template_engine",
            "webhooks",
            "auto_shutdown"
        ]
    }

@app.get("/api/status")
async def get_container_status(name: str = Query(..., description="Nom du container")):
    """Vérifie l'état d'un container (v1 compat)"""
    status_info = await docker_manager.get_container_status(name)
    
    # Déclencher hook plugin
    await plugin_manager.trigger_hook(HookType.ON_HEALTH_CHECK, name, status_info)
    
    return {
        "status": status_info["status"],
        "container_name": name,
        "uptime": status_info.get("uptime"),
        "port": status_info.get("port"),
        "message": status_info.get("message")
    }

@app.post("/api/start")
async def start_container(
    background_tasks: BackgroundTasks,
    name: str = Query(..., description="Nom du container"),
    user = Depends(get_current_user)
):
    """Démarre un container (v1 compat)"""
    
    # Hook avant démarrage
    await plugin_manager.trigger_hook(HookType.BEFORE_CONTAINER_START, name)
    
    result = await docker_manager.start_container(name)
    
    # Hook après démarrage
    await plugin_manager.trigger_hook(HookType.AFTER_CONTAINER_START, name, result["success"])
    
    # Événement WebSocket
    await broadcast_event("container_start", {"name": name, "success": result["success"]})
    
    return {
        "success": result["success"],
        "message": result["message"],
        "container_name": name
    }

@app.post("/api/stop")
async def stop_container(
    name: str = Query(..., description="Nom du container"),
    user = Depends(get_current_user)
):
    """Arrête un container (v1 compat)"""
    
    # Hook avant arrêt
    await plugin_manager.trigger_hook(HookType.BEFORE_CONTAINER_STOP, name)
    
    result = await docker_manager.stop_container(name)
    
    # Hook après arrêt
    await plugin_manager.trigger_hook(HookType.AFTER_CONTAINER_STOP, name, result["success"])
    
    # Événement WebSocket
    await broadcast_event("container_stop", {"name": name, "success": result["success"]})
    
    return {
        "success": result["success"],
        "message": result["message"],
        "container_name": name
    }

@app.get("/api/containers")
async def list_containers():
    """Liste tous les containers (v1 compat)"""
    containers = await docker_manager.list_all_containers()
    return {"containers": containers, "total": len(containers)}

@app.get("/api/logs/{container_name}")
async def get_container_logs(container_name: str, lines: int = Query(100, description="Nombre de lignes")):
    """Récupère les logs d'un container (v1 compat)"""
    logs = await docker_manager.get_container_logs(container_name, lines)
    return {"container_name": container_name, "logs": logs, "lines_requested": lines}

# ===============================
# ENDPOINTS API v2 - SERVICE DISCOVERY
# ===============================

@app.get("/api/v2/discovery")
async def get_discovered_services(
    service_type: Optional[ServiceType] = Query(None, description="Filtrer par type"),
    status: Optional[ServiceStatus] = Query(None, description="Filtrer par statut"),
    user = Depends(get_current_user)
):
    """Récupère tous les services découverts"""
    
    services = await service_discovery.get_all_services()
    
    # Filtrage
    if service_type:
        services = [s for s in services if s.service_type == service_type]
    if status:
        services = [s for s in services if s.status == status]
    
    return {
        "services": [s.to_dict() for s in services],
        "total": len(services),
        "discovery_metrics": service_discovery.get_service_metrics()
    }

@app.get("/api/v2/discovery/{service_name}")
async def get_service_details(service_name: str):
    """Récupère les détails d'un service spécifique"""
    
    service = await service_discovery.get_service(service_name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service {service_name} introuvable")
    
    # Récupérer les dépendances
    dependencies = await service_discovery.get_service_dependencies(service_name)
    dependents = await service_discovery.get_service_dependents(service_name)
    
    return {
        "service": service.to_dict(),
        "dependencies": [d.to_dict() for d in dependencies],
        "dependents": [d.to_dict() for d in dependents]
    }

@app.post("/api/v2/discovery/register")
async def register_service_manually(service: ServiceCreate, user = Depends(get_current_user)):
    """Enregistre manuellement un service"""
    
    # Créer la définition de service
    from service_discovery import ServiceEndpoint
    
    endpoint = ServiceEndpoint(
        protocol="http",
        host=service.name,
        port=service.port,
        path="/",
        health_check_path="/health"
    )
    
    service_def = ServiceDefinition(
        name=service.name,
        container_id="manual",
        image=service.image,
        status=ServiceStatus.STOPPED,
        service_type=ServiceType.WEB,
        endpoints=[endpoint],
        labels=service.labels,
        dependencies=[],
        environment=service.environment,
        created_at=datetime.now(),
        last_seen=datetime.now()
    )
    
    await service_discovery.register_service_manually(service_def)
    
    return {"success": True, "message": f"Service {service.name} enregistré"}

# ===============================
# ENDPOINTS API v2 - AUTO-SCALING
# ===============================

@app.get("/api/v2/scaling/policies")
async def get_scaling_policies(user = Depends(get_current_user)):
    """Récupère toutes les politiques de scaling"""
    
    policies = await auto_scaler.get_all_scaling_policies()
    
    return {
        "policies": [p.__dict__ for p in policies.values()],
        "total": len(policies),
        "metrics": auto_scaler.get_scaling_metrics()
    }

@app.post("/api/v2/scaling/policies")
async def create_scaling_policy(policy: ScalingPolicyCreate, user = Depends(get_current_user)):
    """Crée une nouvelle politique de scaling"""
    
    scaling_policy = ScalingPolicy(
        service_name=policy.service_name,
        enabled=policy.enabled,
        cpu_scale_up_threshold=policy.cpu_scale_up_threshold,
        cpu_scale_down_threshold=policy.cpu_scale_down_threshold,
        memory_scale_up_threshold=policy.memory_scale_up_threshold,
        memory_scale_down_threshold=policy.memory_scale_down_threshold,
        min_replicas=policy.min_replicas,
        max_replicas=policy.max_replicas
    )
    
    await auto_scaler.set_scaling_policy(policy.service_name, scaling_policy)
    
    return {"success": True, "message": f"Politique de scaling créée pour {policy.service_name}"}

@app.post("/api/v2/scaling/{service_name}/scale")
async def manual_scale_service(
    service_name: str, 
    replicas: int = Query(..., description="Nombre de replicas cible"),
    user = Depends(get_current_user)
):
    """Effectue un scaling manuel d'un service"""
    
    success = await auto_scaler.manual_scale(service_name, replicas)
    
    if success:
        # Déclencher hook plugin
        await plugin_manager.trigger_hook(HookType.ON_SCALING_EVENT, service_name, "manual", replicas)
        
        # Événement WebSocket
        await broadcast_event("scaling_event", {
            "service": service_name,
            "direction": "manual",
            "replicas": replicas
        })
        
        return {"success": True, "message": f"Scaling manuel de {service_name} vers {replicas} replicas"}
    else:
        raise HTTPException(status_code=500, detail="Échec du scaling manuel")

@app.get("/api/v2/scaling/{service_name}/events")
async def get_scaling_events(service_name: str, limit: int = Query(20, description="Nombre d'événements")):
    """Récupère l'historique des événements de scaling"""
    
    events = await auto_scaler.get_scaling_events(service_name, limit)
    
    return {
        "service": service_name,
        "events": [
            {
                "direction": e.direction.value,
                "trigger": e.trigger.value,
                "from_replicas": e.from_replicas,
                "to_replicas": e.to_replicas,
                "timestamp": e.timestamp.isoformat(),
                "success": e.success
            }
            for e in events
        ],
        "total": len(events)
    }

# ===============================
# ENDPOINTS API v2 - PLUGINS
# ===============================

@app.get("/api/v2/plugins")
async def get_installed_plugins():
    """Liste tous les plugins installés"""
    
    plugins = plugin_manager.get_installed_plugins()
    active_plugins = plugin_manager.get_active_plugins()
    
    return {
        "plugins": [
            {
                "name": name,
                "version": info.manifest.version,
                "description": info.manifest.description,
                "author": info.manifest.author,
                "type": info.manifest.plugin_type.value,
                "status": info.status.value,
                "active": name in active_plugins,
                "installed_at": info.installed_at.isoformat(),
                "last_updated": info.last_updated.isoformat(),
                "error_message": info.error_message
            }
            for name, info in plugins.items()
        ],
        "metrics": plugin_manager.get_plugin_metrics()
    }

@app.post("/api/v2/plugins/install")
async def install_plugin(plugin: PluginInstall, user = Depends(get_current_user)):
    """Installe un nouveau plugin"""
    
    success = await plugin_manager.install_plugin(plugin.source, plugin.enable)
    
    if success:
        return {"success": True, "message": f"Plugin installé depuis {plugin.source}"}
    else:
        raise HTTPException(status_code=500, detail="Échec de l'installation du plugin")

@app.post("/api/v2/plugins/{plugin_name}/enable")
async def enable_plugin(plugin_name: str, user = Depends(get_current_user)):
    """Active un plugin"""
    
    success = await plugin_manager.enable_plugin(plugin_name)
    
    if success:
        return {"success": True, "message": f"Plugin {plugin_name} activé"}
    else:
        raise HTTPException(status_code=500, detail=f"Échec de l'activation du plugin {plugin_name}")

@app.post("/api/v2/plugins/{plugin_name}/disable")
async def disable_plugin(plugin_name: str, user = Depends(get_current_user)):
    """Désactive un plugin"""
    
    success = await plugin_manager.disable_plugin(plugin_name)
    
    if success:
        return {"success": True, "message": f"Plugin {plugin_name} désactivé"}
    else:
        raise HTTPException(status_code=500, detail=f"Échec de la désactivation du plugin {plugin_name}")

@app.delete("/api/v2/plugins/{plugin_name}")
async def uninstall_plugin(plugin_name: str, user = Depends(get_current_user)):
    """Désinstalle un plugin"""
    
    success = await plugin_manager.uninstall_plugin(plugin_name)
    
    if success:
        return {"success": True, "message": f"Plugin {plugin_name} désinstallé"}
    else:
        raise HTTPException(status_code=500, detail=f"Échec de la désinstallation du plugin {plugin_name}")

@app.get("/api/v2/plugins/marketplace")
async def get_marketplace_plugins():
    """Récupère les plugins disponibles sur le marketplace"""
    
    plugins = await plugin_manager.get_marketplace_plugins()
    return {"plugins": plugins, "total": len(plugins)}

# ===============================
# ENDPOINTS API v2 - TEMPLATES
# ===============================

@app.get("/api/v2/templates")
async def get_templates():
    """Liste tous les templates disponibles"""
    
    templates = await template_engine.list_templates()
    return {"templates": templates, "total": len(templates)}

@app.post("/api/v2/templates")
async def create_template(template: TemplateCreate, user = Depends(get_current_user)):
    """Crée un nouveau template"""
    
    success = await template_engine.create_template(template.name, template.content)
    
    if success:
        return {"success": True, "message": f"Template {template.name} créé"}
    else:
        raise HTTPException(status_code=500, detail="Échec de la création du template")

@app.get("/api/v2/templates/{template_name}/validate")
async def validate_template(template_name: str):
    """Valide un template"""
    
    validation = await template_engine.validate_template(template_name)
    return validation

@app.post("/api/v2/templates/render")
async def render_configurations(user = Depends(get_current_user)):
    """Rend toutes les configurations automatiquement"""
    
    results = await config_renderer.render_all_configurations()
    
    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    return {
        "success": success_count == total_count,
        "results": results,
        "rendered": success_count,
        "total": total_count
    }

@app.post("/api/v2/templates/{template_name}/render")
async def render_single_template(template_name: str, user = Depends(get_current_user)):
    """Rend un template spécifique"""
    
    try:
        rendered_content = await config_renderer.render_single_config(template_name)
        return {
            "success": True,
            "template": template_name,
            "content": rendered_content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur rendu template: {str(e)}")

# ===============================
# ENDPOINTS API v2 - METRICS & MONITORING
# ===============================

@app.get("/api/v2/metrics")
async def get_system_metrics():
    """Récupère toutes les métriques système"""
    
    import psutil
    
    # Métriques système
    system_metrics = {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": {
            "percent": psutil.virtual_memory().percent,
            "total": psutil.virtual_memory().total,
            "used": psutil.virtual_memory().used,
            "available": psutil.virtual_memory().available
        },
        "disk": {
            "percent": psutil.disk_usage('/').percent,
            "total": psutil.disk_usage('/').total,
            "used": psutil.disk_usage('/').used,
            "free": psutil.disk_usage('/').free
        },
        "network": psutil.net_io_counters()._asdict(),
        "timestamp": datetime.now().isoformat()
    }
    
    # Métriques des composants
    component_metrics = {
        "service_discovery": service_discovery.get_service_metrics(),
        "auto_scaler": auto_scaler.get_scaling_metrics(),
        "plugin_manager": plugin_manager.get_plugin_metrics()
    }
    
    return {
        "system": system_metrics,
        "components": component_metrics
    }

@app.get("/api/v2/metrics/prometheus")
async def get_prometheus_metrics():
    """Expose les métriques au format Prometheus"""
    
    # Déclencher hook pour les plugins de métriques
    await plugin_manager.trigger_hook(HookType.ON_METRICS_COLLECTION)
    
    # Format Prometheus basique
    metrics = []
    
    # Métriques des services
    services = await service_discovery.get_all_services()
    for service in services:
        metrics.append(f'selfstart_service_status{{name="{service.name}",status="{service.status.value}"}} 1')
        if service.health_score is not None:
            metrics.append(f'selfstart_service_health{{name="{service.name}"}} {service.health_score}')
    
    # Métriques générales
    metrics.append(f'selfstart_services_total {len(services)}')
    metrics.append(f'selfstart_websocket_connections {len(websocket_connections)}')
    
    content = '\n'.join(metrics)
    
    return StreamingResponse(
        iter([content.encode()]),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )

# ===============================
# ENDPOINTS API v2 - WEBHOOKS
# ===============================

@app.get("/api/v2/webhooks")
async def get_webhooks():
    """Liste tous les webhooks configurés"""
    
    webhooks = await webhook_manager.get_webhooks()
    
    return {
        "webhooks": [
            {
                "id": w.id,
                "name": w.name,
                "provider": w.provider.value,
                "url": str(w.url),
                "events": [e.value for e in w.events],
                "enabled": w.enabled,
                "created_at": w.created_at.isoformat() if w.created_at else None
            }
            for w in webhooks
        ],
        "total": len(webhooks)
    }

@app.post("/api/v2/webhooks")
async def create_webhook(webhook: WebhookCreate, user = Depends(get_current_user)):
    """Crée un nouveau webhook"""
    
    from webhook_manager import WebhookConfig, WebhookProvider, WebhookEvent
    
    webhook_config = WebhookConfig(
        name=webhook.name,
        provider=WebhookProvider.WEBHOOK,  # Par défaut
        url=webhook.url,
        events=[WebhookEvent(event) for event in webhook.events],
        enabled=webhook.enabled
    )
    
    webhook_id = await webhook_manager.create_webhook(webhook_config)
    
    return {"success": True, "webhook_id": webhook_id, "message": f"Webhook {webhook.name} créé"}

# ===============================
# MIDDLEWARE ET HOOKS
# ===============================

@app.middleware("http")
async def add_process_time_header(request, call_next):
    """Middleware pour mesurer le temps de traitement"""
    start_time = datetime.now()
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds()
    
    response.headers["X-Process-Time"] = str(process_time)
    
    # Déclencher hook pour les plugins de métriques
    await plugin_manager.trigger_hook(
        HookType.ON_API_REQUEST, 
        request.method, 
        str(request.url.path),
        process_time
    )
    
    return response

# ===============================
# DEMARRAGE DE L'APPLICATION
# ===============================

if __name__ == "__main__":
    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("API_HOST", "0.0.0.0")
    reload = os.getenv("DEV_MODE", "false").lower() == "true"
    
    uvicorn.run(
        "main_v2:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
