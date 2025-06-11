from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio
import os
from docker_manager import DockerManager
from typing import Optional
import logging
from caddy_api import router as caddy_router

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation de l'application FastAPI
app = FastAPI(
    title="SelfStart API",
    description="API pour gérer le démarrage automatique de containers Docker",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialisation du gestionnaire Docker
docker_manager = DockerManager()

# Inclure le router Caddy
app.include_router(caddy_router)

# Modèles Pydantic
class ContainerResponse(BaseModel):
    status: str
    container_name: str
    uptime: Optional[int] = None
    port: Optional[int] = None
    message: Optional[str] = None

class ActionResponse(BaseModel):
    success: bool
    message: str
    container_name: str

@app.get("/health")
async def health_check():
    """Point de santé pour les health checks"""
    return {"status": "healthy", "service": "selfstart-api"}

@app.get("/")
async def root():
    """Point d'entrée racine de l'API"""
    return {
        "message": "SelfStart API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "status": "/api/status?name=container_name",
            "start": "/api/start?name=container_name",
            "stop": "/api/stop?name=container_name",
            "list": "/api/containers"
        }
    }

@app.get("/api/status", response_model=ContainerResponse)
async def get_container_status(
    name: str = Query(..., description="Nom du container à vérifier")
):
    """
    Vérifie l'état d'un container Docker
    
    Args:
        name: Nom du container à vérifier
        
    Returns:
        ContainerResponse: État du container avec détails
    """
    try:
        logger.info(f"Vérification de l'état du container: {name}")
        
        status_info = await docker_manager.get_container_status(name)
        
        return ContainerResponse(
            status=status_info["status"],
            container_name=name,
            uptime=status_info.get("uptime"),
            port=status_info.get("port"),
            message=status_info.get("message")
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du container {name}: {str(e)}")
        return ContainerResponse(
            status="error",
            container_name=name,
            message=f"Erreur: {str(e)}"
        )

@app.post("/api/start", response_model=ActionResponse)
async def start_container(
    background_tasks: BackgroundTasks,
    name: str = Query(..., description="Nom du container à démarrer")
):
    """
    Démarre un container Docker
    
    Args:
        name: Nom du container à démarrer
        background_tasks: Tâches en arrière-plan pour le démarrage
        
    Returns:
        ActionResponse: Résultat de l'opération de démarrage
    """
    try:
        logger.info(f"Démarrage du container: {name}")
        
        # Vérifier d'abord l'état actuel
        current_status = await docker_manager.get_container_status(name)
        
        if current_status["status"] == "running":
            return ActionResponse(
                success=True,
                message="Container déjà en cours d'exécution",
                container_name=name
            )
        
        if current_status["status"] == "not_found":
            raise HTTPException(
                status_code=404,
                detail=f"Container '{name}' introuvable"
            )
        
        # Démarrer le container en arrière-plan
        background_tasks.add_task(docker_manager.start_container, name)
        
        return ActionResponse(
            success=True,
            message="Démarrage du container en cours...",
            container_name=name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du container {name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du démarrage: {str(e)}"
        )

@app.post("/api/stop", response_model=ActionResponse)
async def stop_container(
    name: str = Query(..., description="Nom du container à arrêter")
):
    """
    Arrête un container Docker
    
    Args:
        name: Nom du container à arrêter
        
    Returns:
        ActionResponse: Résultat de l'opération d'arrêt
    """
    try:
        logger.info(f"Arrêt du container: {name}")
        
        result = await docker_manager.stop_container(name)
        
        return ActionResponse(
            success=result["success"],
            message=result["message"],
            container_name=name
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt du container {name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'arrêt: {str(e)}"
        )

@app.get("/api/containers")
async def list_containers():
    """
    Liste tous les containers disponibles
    
    Returns:
        dict: Liste des containers avec leur état
    """
    try:
        logger.info("Récupération de la liste des containers")
        
        containers = await docker_manager.list_all_containers()
        
        return {
            "containers": containers,
            "total": len(containers)
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des containers: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération: {str(e)}"
        )

@app.get("/api/logs/{container_name}")
async def get_container_logs(
    container_name: str,
    lines: int = Query(100, description="Nombre de lignes à récupérer")
):
    """
    Récupère les logs d'un container
    
    Args:
        container_name: Nom du container
        lines: Nombre de lignes de logs à récupérer
        
    Returns:
        dict: Logs du container
    """
    try:
        logger.info(f"Récupération des logs pour: {container_name}")
        
        logs = await docker_manager.get_container_logs(container_name, lines)
        
        return {
            "container_name": container_name,
            "logs": logs,
            "lines_requested": lines
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des logs {container_name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des logs: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)