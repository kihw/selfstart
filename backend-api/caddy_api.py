from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from caddy_manager import CaddyConfigManager, CaddyRoute, CaddyMatcher, CaddyUpstream, MatcherType, ProxyRule

router = APIRouter(prefix="/api/caddy", tags=["caddy"])

# Instance globale du gestionnaire Caddy
caddy_manager = CaddyConfigManager()

# Modèles Pydantic pour l'API
class CaddyMatcherRequest(BaseModel):
    type: MatcherType
    value: str
    name: Optional[str] = None

class CaddyUpstreamRequest(BaseModel):
    address: str
    weight: int = 1
    max_requests: int = 0
    health_check_uri: str = "/health"
    health_check_interval: str = "30s"
    health_check_timeout: str = "5s"

class CaddyRouteRequest(BaseModel):
    domain: str
    matchers: List[CaddyMatcherRequest]
    upstreams: List[CaddyUpstreamRequest]
    rule: ProxyRule = ProxyRule.ROUND_ROBIN
    tls_enabled: bool = True
    basic_auth: Optional[Dict[str, str]] = None
    rate_limit: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    middleware: List[str] = []
    enabled: bool = True

class CaddyGlobalConfigRequest(BaseModel):
    email: str
    admin_port: int = 2019
    http_port: int = 80
    https_port: int = 443
    log_level: str = "INFO"

@router.get("/status")
async def get_caddy_status():
    """Récupère le statut de Caddy"""
    return await caddy_manager.get_caddy_status()

@router.get("/routes")
async def get_routes():
    """Récupère toutes les routes configurées"""
    routes = await caddy_manager.load_routes()
    
    return {
        "routes": [
            {
                "id": route_id,
                "domain": route.domain,
                "upstreams_count": len(route.upstreams),
                "enabled": route.enabled,
                "rule": route.rule.value,
                "tls_enabled": route.tls_enabled,
                "created_at": route.created_at.isoformat(),
                "updated_at": route.updated_at.isoformat()
            }
            for route_id, route in routes.items()
        ],
        "total": len(routes),
        "enabled": len([r for r in routes.values() if r.enabled])
    }

@router.get("/routes/{route_id}")
async def get_route(route_id: str):
    """Récupère une route spécifique"""
    routes = await caddy_manager.load_routes()
    
    if route_id not in routes:
        raise HTTPException(status_code=404, detail="Route introuvable")
    
    route = routes[route_id]
    
    return {
        "id": route_id,
        "domain": route.domain,
        "matchers": [
            {
                "type": m.type.value,
                "value": m.value,
                "name": m.name
            }
            for m in route.matchers
        ],
        "upstreams": [
            {
                "address": u.address,
                "weight": u.weight,
                "max_requests": u.max_requests,
                "health_check_uri": u.health_check_uri,
                "health_check_interval": u.health_check_interval,
                "health_check_timeout": u.health_check_timeout
            }
            for u in route.upstreams
        ],
        "rule": route.rule.value,
        "tls_enabled": route.tls_enabled,
        "basic_auth": route.basic_auth,
        "rate_limit": route.rate_limit,
        "headers": route.headers,
        "middleware": route.middleware,
        "enabled": route.enabled,
        "created_at": route.created_at.isoformat(),
        "updated_at": route.updated_at.isoformat()
    }

@router.post("/routes")
async def create_route(route_request: CaddyRouteRequest):
    """Crée une nouvelle route"""
    # Convertir les modèles Pydantic en objets internes
    matchers = [
        CaddyMatcher(
            type=m.type,
            value=m.value,
            name=m.name
        )
        for m in route_request.matchers
    ]
    
    upstreams = [
        CaddyUpstream(
            address=u.address,
            weight=u.weight,
            max_requests=u.max_requests,
            health_check_uri=u.health_check_uri,
            health_check_interval=u.health_check_interval,
            health_check_timeout=u.health_check_timeout
        )
        for u in route_request.upstreams
    ]
    
    # Générer un ID unique
    route_id = f"route_{hash(route_request.domain)}_{len(upstreams)}_{int(datetime.now().timestamp())}"
    
    route = CaddyRoute(
        id=route_id,
        domain=route_request.domain,
        matchers=matchers,
        upstreams=upstreams,
        rule=route_request.rule,
        tls_enabled=route_request.tls_enabled,
        basic_auth=route_request.basic_auth,
        rate_limit=route_request.rate_limit,
        headers=route_request.headers,
        middleware=route_request.middleware,
        enabled=route_request.enabled
    )
    
    success = await caddy_manager.create_route(route)
    
    if success:
        return {
            "success": True,
            "route_id": route_id,
            "message": f"Route créée pour {route_request.domain}"
        }
    else:
        raise HTTPException(status_code=500, detail="Erreur lors de la création de la route")

@router.put("/routes/{route_id}")
async def update_route(route_id: str, route_request: CaddyRouteRequest):
    """Met à jour une route existante"""
    # Convertir les modèles Pydantic en objets internes
    matchers = [
        CaddyMatcher(
            type=m.type,
            value=m.value,
            name=m.name
        )
        for m in route_request.matchers
    ]
    
    upstreams = [
        CaddyUpstream(
            address=u.address,
            weight=u.weight,
            max_requests=u.max_requests,
            health_check_uri=u.health_check_uri,
            health_check_interval=u.health_check_interval,
            health_check_timeout=u.health_check_timeout
        )
        for u in route_request.upstreams
    ]
    
    route = CaddyRoute(
        id=route_id,
        domain=route_request.domain,
        matchers=matchers,
        upstreams=upstreams,
        rule=route_request.rule,
        tls_enabled=route_request.tls_enabled,
        basic_auth=route_request.basic_auth,
        rate_limit=route_request.rate_limit,
        headers=route_request.headers,
        middleware=route_request.middleware,
        enabled=route_request.enabled
    )
    
    success = await caddy_manager.update_route(route_id, route)
    
    if success:
        return {
            "success": True,
            "message": f"Route {route_id} mise à jour"
        }
    else:
        raise HTTPException(status_code=404, detail="Route introuvable ou erreur de mise à jour")

@router.delete("/routes/{route_id}")
async def delete_route(route_id: str):
    """Supprime une route"""
    success = await caddy_manager.delete_route(route_id)
    
    if success:
        return {
            "success": True,
            "message": f"Route {route_id} supprimée"
        }
    else:
        raise HTTPException(status_code=404, detail="Route introuvable")

@router.post("/routes/{route_id}/toggle")
async def toggle_route(route_id: str):
    """Active/désactive une route"""
    success = await caddy_manager.toggle_route(route_id)
    
    if success:
        routes = await caddy_manager.load_routes()
        route = routes.get(route_id)
        status = "activée" if route and route.enabled else "désactivée"
        
        return {
            "success": True,
            "enabled": route.enabled if route else False,
            "message": f"Route {route_id} {status}"
        }
    else:
        raise HTTPException(status_code=404, detail="Route introuvable")

@router.post("/routes/{route_id}/test")
async def test_route(route_id: str):
    """Teste une route spécifique"""
    result = await caddy_manager.test_route(route_id)
    return result

@router.get("/validate")
async def validate_configuration():
    """Valide la configuration actuelle"""
    return await caddy_manager.validate_configuration()

@router.post("/backup")
async def backup_configuration():
    """Sauvegarde la configuration actuelle"""
    try:
        backup_path = await caddy_manager.backup_configuration()
        return {
            "success": True,
            "backup_path": backup_path,
            "message": "Configuration sauvegardée"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur sauvegarde: {str(e)}")

@router.post("/restore")
async def restore_configuration(backup_path: str):
    """Restaure une configuration depuis une sauvegarde"""
    success = await caddy_manager.restore_configuration(backup_path)
    
    if success:
        return {
            "success": True,
            "message": "Configuration restaurée avec succès"
        }
    else:
        raise HTTPException(status_code=500, detail="Erreur lors de la restauration")

@router.get("/global-config")
async def get_global_config():
    """Récupère la configuration globale"""
    return caddy_manager.global_config

@router.put("/global-config")
async def update_global_config(config: CaddyGlobalConfigRequest):
    """Met à jour la configuration globale"""
    caddy_manager.global_config = {
        "email": config.email,
        "admin_port": config.admin_port,
        "http_port": config.http_port,
        "https_port": config.https_port,
        "log_level": config.log_level
    }
    
    # Appliquer la nouvelle configuration
    success = await caddy_manager._apply_configuration()
    
    if success:
        return {
            "success": True,
            "message": "Configuration globale mise à jour"
        }
    else:
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour")

@router.post("/reload")
async def reload_configuration():
    """Recharge la configuration Caddy"""
    success = await caddy_manager._apply_configuration()
    
    if success:
        return {
            "success": True,
            "message": "Configuration rechargée"
        }
    else:
        raise HTTPException(status_code=500, detail="Erreur lors du rechargement")