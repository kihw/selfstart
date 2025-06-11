from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import asyncio
import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

# Imports des nouveaux modules
from container_orchestrator import ContainerOrchestrator, ContainerConfig, StartupStrategy, ContainerState
from proxy_manager import ProxyManager, ProxyTarget, Backend, ProxyRule, BackendStatus
from docker_manager import DockerManager

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Modèles Pydantic
class ContainerCreateRequest(BaseModel):
    name: str
    image: str
    ports: Dict[int, int]
    environment: Dict[str, str] = {}
    volumes: Dict[str, str] = {}
    labels: Dict[str, str] = {}
    dependencies: List[str] = []
    startup_strategy: StartupStrategy = StartupStrategy.IMMEDIATE
    health_check: Optional[Dict[str, Any]] = None
    startup_timeout: int = 120

class ProxyTargetRequest(BaseModel):
    name: str
    backends: List[Dict[str, Any]]
    rule: ProxyRule = ProxyRule.ROUND_ROBIN
    health_check_path: str = "/health"
    health_check_interval: int = 30

class BackendRequest(BaseModel):
    host: str
    port: int
    weight: int = 1
    max_connections: int = 100

# Initialisation de l'application FastAPI Enhanced
app = FastAPI(
    title="SelfStart Enhanced API",
    description="API avancée avec orchestration intelligente et proxy load-balancé",
    version="1.5.0",
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

# Variables globales pour les gestionnaires
docker_manager = None
container_orchestrator = None
proxy_manager = None

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    global docker_manager, container_orchestrator, proxy_manager
    
    logger.info("🚀 Démarrage de SelfStart Enhanced API...")
    
    try:
        # Redis pour la coordination
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        # Initialisation des gestionnaires
        docker_manager = DockerManager()
        
        container_orchestrator = ContainerOrchestrator(redis_url)
        await container_orchestrator.start()
        
        proxy_manager = ProxyManager(redis_url)
        await proxy_manager.start()
        
        # Configuration des targets de proxy par défaut
        await _setup_default_proxy_targets()
        
        logger.info("✅ SelfStart Enhanced API initialisé avec succès")
        
    except Exception as e:
        logger.error(f"❌ Erreur initialisation: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage à l'arrêt"""
    logger.info("🛑 Arrêt de SelfStart Enhanced API...")
    
    try:
        if container_orchestrator:
            await container_orchestrator.stop()
        if proxy_manager:
            await proxy_manager.stop()
        
        logger.info("✅ SelfStart Enhanced API arrêté proprement")
    except Exception as e:
        logger.error(f"❌ Erreur arrêt: {e}")

async def _setup_default_proxy_targets():
    """Configure les targets de proxy par défaut"""
    # Target pour l'API backend
    api_target = ProxyTarget(
        name="api",
        backends=[Backend(host="localhost", port=8000)],
        rule=ProxyRule.HEALTH_BASED,
        health_check_path="/health"
    )
    await proxy_manager.register_target(api_target)
    
    # Target pour le frontend
    frontend_target = ProxyTarget(
        name="frontend",
        backends=[Backend(host="localhost", port=3000)],
        rule=ProxyRule.ROUND_ROBIN,
        health_check_path="/"
    )
    await proxy_manager.register_target(frontend_target)

# ===============================
# ENDPOINTS API ENHANCED
# ===============================

@app.get("/health")
async def health_check():
    """Point de santé avancé"""
    orchestrator_metrics = container_orchestrator.get_metrics() if container_orchestrator else {}
    proxy_metrics = proxy_manager.get_metrics() if proxy_manager else {}
    
    return {
        "status": "healthy",
        "service": "selfstart-enhanced-api",
        "version": "1.5.0",
        "timestamp": datetime.now().isoformat(),
        "orchestrator": orchestrator_metrics,
        "proxy": proxy_metrics
    }

@app.get("/")
async def root():
    """Point d'entrée racine de l'API Enhanced"""
    return {
        "message": "SelfStart Enhanced API",
        "version": "1.5.0",
        "features": [
            "intelligent_orchestration",
            "load_balanced_proxy",
            "health_monitoring",
            "dependency_management",
            "circuit_breakers",
            "auto_scaling_ready"
        ],
        "docs": "/docs"
    }

# ===============================
# CONTAINER ORCHESTRATION
# ===============================

@app.post("/api/v2/containers")
async def create_container(request: ContainerCreateRequest):
    """Crée et configure un nouveau container"""
    try:
        config = ContainerConfig(
            name=request.name,
            image=request.image,
            ports=request.ports,
            environment=request.environment,
            volumes=request.volumes,
            labels=request.labels,
            dependencies=request.dependencies,
            startup_strategy=request.startup_strategy,
            health_check=request.health_check,
            startup_timeout=request.startup_timeout
        )
        
        await container_orchestrator.register_container(config)
        
        return {
            "success": True,
            "message": f"Container {request.name} configuré",
            "container_name": request.name
        }
        
    except Exception as e:
        logger.error(f"Erreur création container {request.name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/containers")
async def list_containers():
    """Liste tous les containers avec leur statut détaillé"""
    try:
        containers = await container_orchestrator.get_all_containers()
        
        result = []
        for name, status in containers.items():
            result.append({
                "name": name,
                "state": status.state.value,
                "container_id": status.container_id,
                "started_at": status.started_at.isoformat() if status.started_at else None,
                "health_status": status.health_status,
                "last_health_check": status.last_health_check.isoformat() if status.last_health_check else None,
                "error_message": status.error_message,
                "restart_count": status.restart_count
            })
        
        return {
            "containers": result,
            "total": len(result),
            "metrics": container_orchestrator.get_metrics()
        }
        
    except Exception as e:
        logger.error(f"Erreur liste containers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/containers/{name}/status")
async def get_container_status(name: str):
    """Récupère le statut détaillé d'un container"""
    try:
        status = await container_orchestrator.get_container_status(name)
        
        if not status:
            raise HTTPException(status_code=404, detail=f"Container {name} non trouvé")
        
        return {
            "name": name,
            "state": status.state.value,
            "container_id": status.container_id,
            "started_at": status.started_at.isoformat() if status.started_at else None,
            "health_status": status.health_status,
            "last_health_check": status.last_health_check.isoformat() if status.last_health_check else None,
            "error_message": status.error_message,
            "restart_count": status.restart_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur statut container {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v2/containers/{name}/start")
async def start_container_enhanced(name: str, force: bool = Query(False)):
    """Démarre un container avec gestion des dépendances"""
    try:
        success = await container_orchestrator.start_container(name, force)
        
        if success:
            return {
                "success": True,
                "message": f"Container {name} en cours de démarrage",
                "container_name": name
            }
        else:
            raise HTTPException(status_code=500, detail=f"Échec démarrage {name}")
            
    except Exception as e:
        logger.error(f"Erreur démarrage container {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v2/containers/{name}/stop")
async def stop_container_enhanced(name: str, force: bool = Query(False)):
    """Arrête un container"""
    try:
        success = await container_orchestrator.stop_container(name, force)
        
        if success:
            return {
                "success": True,
                "message": f"Container {name} arrêté",
                "container_name": name
            }
        else:
            raise HTTPException(status_code=500, detail=f"Échec arrêt {name}")
            
    except Exception as e:
        logger.error(f"Erreur arrêt container {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v2/containers/{name}/restart")
async def restart_container_enhanced(name: str):
    """Redémarre un container"""
    try:
        success = await container_orchestrator.restart_container(name)
        
        if success:
            return {
                "success": True,
                "message": f"Container {name} redémarré",
                "container_name": name
            }
        else:
            raise HTTPException(status_code=500, detail=f"Échec redémarrage {name}")
            
    except Exception as e:
        logger.error(f"Erreur redémarrage container {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/containers/{name}/logs")
async def get_container_logs_enhanced(name: str, lines: int = Query(100)):
    """Récupère les logs d'un container"""
    try:
        logs = await container_orchestrator.get_container_logs(name, lines)
        
        return {
            "container_name": name,
            "logs": logs,
            "lines_requested": lines
        }
        
    except Exception as e:
        logger.error(f"Erreur logs container {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===============================
# PROXY MANAGEMENT
# ===============================

@app.post("/api/v2/proxy/targets")
async def create_proxy_target(request: ProxyTargetRequest):
    """Crée un nouveau target de proxy"""
    try:
        backends = []
        for backend_data in request.backends:
            backend = Backend(
                host=backend_data["host"],
                port=backend_data["port"],
                weight=backend_data.get("weight", 1),
                max_connections=backend_data.get("max_connections", 100)
            )
            backends.append(backend)
        
        target = ProxyTarget(
            name=request.name,
            backends=backends,
            rule=request.rule,
            health_check_path=request.health_check_path,
            health_check_interval=request.health_check_interval
        )
        
        await proxy_manager.register_target(target)
        
        return {
            "success": True,
            "message": f"Target {request.name} créé",
            "target_name": request.name
        }
        
    except Exception as e:
        logger.error(f"Erreur création target {request.name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/proxy/targets")
async def list_proxy_targets():
    """Liste tous les targets de proxy"""
    try:
        targets = []
        for target_name in proxy_manager.targets.keys():
            status = proxy_manager.get_target_status(target_name)
            if status:
                targets.append(status)
        
        return {
            "targets": targets,
            "total": len(targets),
            "metrics": proxy_manager.get_metrics()
        }
        
    except Exception as e:
        logger.error(f"Erreur liste targets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/proxy/targets/{target_name}")
async def get_proxy_target_status(target_name: str):
    """Récupère le statut d'un target de proxy"""
    try:
        status = proxy_manager.get_target_status(target_name)
        
        if not status:
            raise HTTPException(status_code=404, detail=f"Target {target_name} non trouvé")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur statut target {target_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v2/proxy/targets/{target_name}/backends")
async def add_backend_to_target(target_name: str, request: BackendRequest):
    """Ajoute un backend à un target"""
    try:
        backend = Backend(
            host=request.host,
            port=request.port,
            weight=request.weight,
            max_connections=request.max_connections
        )
        
        await proxy_manager.add_backend(target_name, backend)
        
        return {
            "success": True,
            "message": f"Backend {backend.url} ajouté au target {target_name}"
        }
        
    except Exception as e:
        logger.error(f"Erreur ajout backend: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v2/proxy/targets/{target_name}/backends")
async def remove_backend_from_target(target_name: str, backend_url: str = Query(...)):
    """Retire un backend d'un target"""
    try:
        await proxy_manager.remove_backend(target_name, backend_url)
        
        return {
            "success": True,
            "message": f"Backend {backend_url} retiré du target {target_name}"
        }
        
    except Exception as e:
        logger.error(f"Erreur suppression backend: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v2/proxy/targets/{target_name}/backends/maintenance")
async def set_backend_maintenance(target_name: str, backend_url: str = Query(...), 
                                maintenance: bool = Query(...)):
    """Met un backend en maintenance"""
    try:
        await proxy_manager.set_backend_maintenance(target_name, backend_url, maintenance)
        
        return {
            "success": True,
            "message": f"Backend {backend_url} {'en' if maintenance else 'hors'} maintenance"
        }
        
    except Exception as e:
        logger.error(f"Erreur maintenance backend: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===============================
# PROXY REQUESTS
# ===============================

@app.api_route("/proxy/{target_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(request: Request, target_name: str, path: str):
    """Proxifie une requête vers un target"""
    try:
        # Extraire les informations de la requête
        method = request.method
        headers = dict(request.headers)
        body = await request.body()
        client_ip = request.client.host
        
        # Supprimer les headers problématiques
        headers.pop('host', None)
        headers.pop('content-length', None)
        
        # Proxifier la requête
        status_code, response_headers, response_body = await proxy_manager.proxy_request(
            target_name=target_name,
            path=f"/{path}",
            method=method,
            headers=headers,
            body=body,
            client_ip=client_ip
        )
        
        return StreamingResponse(
            iter([response_body]),
            status_code=status_code,
            headers=response_headers
        )
        
    except Exception as e:
        logger.error(f"Erreur proxy vers {target_name}: {e}")
        raise HTTPException(status_code=502, detail="Proxy error")

# ===============================
# MÉTRIQUES ET MONITORING
# ===============================

@app.get("/api/v2/metrics")
async def get_enhanced_metrics():
    """Récupère toutes les métriques du système"""
    try:
        orchestrator_metrics = container_orchestrator.get_metrics() if container_orchestrator else {}
        proxy_metrics = proxy_manager.get_metrics() if proxy_manager else {}
        
        return {
            "timestamp": datetime.now().isoformat(),
            "orchestrator": orchestrator_metrics,
            "proxy": proxy_metrics,
            "system": {
                "api_version": "1.5.0",
                "uptime": "calculated_uptime"  # À implémenter
            }
        }
        
    except Exception as e:
        logger.error(f"Erreur métriques: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===============================
# COMPATIBILITÉ API v1
# ===============================

@app.get("/api/status")
async def get_container_status_v1(name: str = Query(...)):
    """Compatibilité v1 - Vérifie l'état d'un container"""
    try:
        status = await container_orchestrator.get_container_status(name)
        
        if not status:
            return {
                "status": "not_found",
                "container_name": name,
                "message": f"Container {name} introuvable"
            }
        
        # Mapper les nouveaux états vers les anciens
        status_map = {
            ContainerState.RUNNING: "running",
            ContainerState.STOPPED: "stopped",
            ContainerState.STARTING: "starting",
            ContainerState.ERROR: "error",
            ContainerState.UNHEALTHY: "unhealthy"
        }
        
        return {
            "status": status_map.get(status.state, "unknown"),
            "container_name": name,
            "uptime": int((datetime.now() - status.started_at).total_seconds()) if status.started_at else 0,
            "message": f"Container {name} est {status.state.value}"
        }
        
    except Exception as e:
        logger.error(f"Erreur statut v1 {name}: {e}")
        return {
            "status": "error",
            "container_name": name,
            "message": f"Erreur: {str(e)}"
        }

@app.post("/api/start")
async def start_container_v1(name: str = Query(...)):
    """Compatibilité v1 - Démarre un container"""
    try:
        success = await container_orchestrator.start_container(name)
        
        return {
            "success": success,
            "message": "Container en cours de démarrage" if success else "Échec du démarrage",
            "container_name": name
        }
        
    except Exception as e:
        logger.error(f"Erreur démarrage v1 {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop")
async def stop_container_v1(name: str = Query(...)):
    """Compatibilité v1 - Arrête un container"""
    try:
        success = await container_orchestrator.stop_container(name)
        
        return {
            "success": success,
            "message": "Container arrêté" if success else "Échec de l'arrêt",
            "container_name": name
        }
        
    except Exception as e:
        logger.error(f"Erreur arrêt v1 {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    uvicorn.run(
        "main_enhanced:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )