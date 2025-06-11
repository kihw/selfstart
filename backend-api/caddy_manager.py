import asyncio
import json
import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import aiofiles
import aiohttp
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ProxyRule(str, Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    IP_HASH = "ip_hash"
    HEALTH_BASED = "health_based"

class MatcherType(str, Enum):
    HOST = "host"
    PATH = "path"
    HEADER = "header"
    QUERY = "query"
    METHOD = "method"

@dataclass
class CaddyMatcher:
    type: MatcherType
    value: str
    name: Optional[str] = None

@dataclass
class CaddyUpstream:
    address: str
    weight: int = 1
    max_requests: int = 0
    health_check_uri: str = "/health"
    health_check_interval: str = "30s"
    health_check_timeout: str = "5s"

@dataclass
class CaddyRoute:
    id: str
    domain: str
    matchers: List[CaddyMatcher]
    upstreams: List[CaddyUpstream]
    rule: ProxyRule = ProxyRule.ROUND_ROBIN
    tls_enabled: bool = True
    basic_auth: Optional[Dict[str, str]] = None
    rate_limit: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    middleware: List[str] = None
    enabled: bool = True
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.middleware is None:
            self.middleware = []

class CaddyConfigManager:
    """Gestionnaire de configuration Caddy avec interface admin"""
    
    def __init__(self, caddy_config_path: str = "/etc/caddy/Caddyfile", 
                 caddy_admin_url: str = "http://localhost:2019"):
        self.config_path = caddy_config_path
        self.admin_url = caddy_admin_url
        self.routes: Dict[str, CaddyRoute] = {}
        self.global_config = {
            "email": "admin@example.com",
            "admin_port": 2019,
            "http_port": 80,
            "https_port": 443,
            "log_level": "INFO"
        }
        
    async def load_routes(self) -> Dict[str, CaddyRoute]:
        """Charge les routes depuis la configuration actuelle"""
        try:
            # Charger depuis l'API admin de Caddy
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.admin_url}/config/") as response:
                    if response.status == 200:
                        config = await response.json()
                        self.routes = self._parse_caddy_config(config)
            
            return self.routes
        except Exception as e:
            logger.error(f"Erreur chargement routes Caddy: {e}")
            return {}

    def _parse_caddy_config(self, config: Dict) -> Dict[str, CaddyRoute]:
        """Parse la configuration Caddy en routes"""
        routes = {}
        
        try:
            apps = config.get("apps", {})
            http_app = apps.get("http", {})
            servers = http_app.get("servers", {})
            
            for server_name, server_config in servers.items():
                routes_config = server_config.get("routes", [])
                
                for route_config in routes_config:
                    route = self._parse_route(route_config)
                    if route:
                        routes[route.id] = route
        except Exception as e:
            logger.error(f"Erreur parsing config Caddy: {e}")
        
        return routes

    def _parse_route(self, route_config: Dict) -> Optional[CaddyRoute]:
        """Parse une route individuelle"""
        try:
            # Extraire les matchers
            matchers = []
            match_config = route_config.get("match", [])
            for matcher in match_config:
                if "host" in matcher:
                    matchers.append(CaddyMatcher(MatcherType.HOST, matcher["host"][0]))
                elif "path" in matcher:
                    matchers.append(CaddyMatcher(MatcherType.PATH, matcher["path"][0]))
            
            # Extraire les upstreams
            upstreams = []
            handle_config = route_config.get("handle", [])
            for handler in handle_config:
                if handler.get("handler") == "reverse_proxy":
                    upstreams_config = handler.get("upstreams", [])
                    for upstream in upstreams_config:
                        upstreams.append(CaddyUpstream(
                            address=upstream.get("dial", ""),
                            weight=upstream.get("weight", 1)
                        ))
            
            if not matchers or not upstreams:
                return None
            
            # Créer la route
            domain = matchers[0].value if matchers else "unknown"
            route_id = f"route_{hash(domain)}_{len(upstreams)}"
            
            return CaddyRoute(
                id=route_id,
                domain=domain,
                matchers=matchers,
                upstreams=upstreams
            )
            
        except Exception as e:
            logger.error(f"Erreur parsing route: {e}")
            return None

    async def create_route(self, route: CaddyRoute) -> bool:
        """Crée une nouvelle route"""
        try:
            self.routes[route.id] = route
            await self._apply_configuration()
            logger.info(f"Route {route.id} créée pour {route.domain}")
            return True
        except Exception as e:
            logger.error(f"Erreur création route {route.id}: {e}")
            return False

    async def update_route(self, route_id: str, route: CaddyRoute) -> bool:
        """Met à jour une route existante"""
        try:
            if route_id not in self.routes:
                return False
            
            route.updated_at = datetime.now()
            self.routes[route_id] = route
            await self._apply_configuration()
            logger.info(f"Route {route_id} mise à jour")
            return True
        except Exception as e:
            logger.error(f"Erreur mise à jour route {route_id}: {e}")
            return False

    async def delete_route(self, route_id: str) -> bool:
        """Supprime une route"""
        try:
            if route_id not in self.routes:
                return False
            
            del self.routes[route_id]
            await self._apply_configuration()
            logger.info(f"Route {route_id} supprimée")
            return True
        except Exception as e:
            logger.error(f"Erreur suppression route {route_id}: {e}")
            return False

    async def toggle_route(self, route_id: str) -> bool:
        """Active/désactive une route"""
        try:
            if route_id not in self.routes:
                return False
            
            route = self.routes[route_id]
            route.enabled = not route.enabled
            route.updated_at = datetime.now()
            
            await self._apply_configuration()
            logger.info(f"Route {route_id} {'activée' if route.enabled else 'désactivée'}")
            return True
        except Exception as e:
            logger.error(f"Erreur toggle route {route_id}: {e}")
            return False

    async def _apply_configuration(self) -> bool:
        """Applique la configuration à Caddy"""
        try:
            # Générer la configuration Caddy
            config = self._generate_caddy_config()
            
            # Appliquer via l'API admin
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.admin_url}/load",
                    json=config,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        logger.info("Configuration Caddy appliquée avec succès")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Erreur application config Caddy: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Erreur application configuration: {e}")
            return False

    def _generate_caddy_config(self) -> Dict:
        """Génère la configuration Caddy JSON"""
        config = {
            "admin": {
                "listen": f":{self.global_config['admin_port']}"
            },
            "apps": {
                "http": {
                    "servers": {
                        "selfstart": {
                            "listen": [f":{self.global_config['http_port']}", f":{self.global_config['https_port']}"],
                            "routes": []
                        }
                    }
                },
                "tls": {
                    "automation": {
                        "policies": [
                            {
                                "subjects": ["*.{$BASE_DOMAIN}"],
                                "issuers": [
                                    {
                                        "module": "acme",
                                        "email": self.global_config["email"]
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        }
        
        # Ajouter les routes actives
        for route in self.routes.values():
            if route.enabled:
                caddy_route = self._route_to_caddy_config(route)
                config["apps"]["http"]["servers"]["selfstart"]["routes"].append(caddy_route)
        
        return config

    def _route_to_caddy_config(self, route: CaddyRoute) -> Dict:
        """Convertit une route en configuration Caddy"""
        caddy_route = {
            "match": [],
            "handle": []
        }
        
        # Ajouter les matchers
        for matcher in route.matchers:
            if matcher.type == MatcherType.HOST:
                caddy_route["match"].append({"host": [matcher.value]})
            elif matcher.type == MatcherType.PATH:
                caddy_route["match"].append({"path": [matcher.value]})
        
        # Ajouter le reverse proxy
        reverse_proxy = {
            "handler": "reverse_proxy",
            "upstreams": []
        }
        
        for upstream in route.upstreams:
            upstream_config = {
                "dial": upstream.address
            }
            if upstream.weight != 1:
                upstream_config["weight"] = upstream.weight
            reverse_proxy["upstreams"].append(upstream_config)
        
        # Ajouter la politique de load balancing
        if route.rule != ProxyRule.ROUND_ROBIN:
            reverse_proxy["load_balancing"] = {
                "selection_policy": {
                    "policy": route.rule.value
                }
            }
        
        # Ajouter les health checks
        if route.upstreams:
            reverse_proxy["health_checks"] = {
                "active": {
                    "uri": route.upstreams[0].health_check_uri,
                    "interval": route.upstreams[0].health_check_interval,
                    "timeout": route.upstreams[0].health_check_timeout
                }
            }
        
        caddy_route["handle"].append(reverse_proxy)
        
        # Ajouter l'authentification basique si configurée
        if route.basic_auth:
            auth_handler = {
                "handler": "authentication",
                "providers": {
                    "http_basic": {
                        "accounts": route.basic_auth
                    }
                }
            }
            caddy_route["handle"].insert(0, auth_handler)
        
        return caddy_route

    async def get_caddy_status(self) -> Dict[str, Any]:
        """Récupère le statut de Caddy"""
        try:
            async with aiohttp.ClientSession() as session:
                # Statut général
                async with session.get(f"{self.admin_url}/") as response:
                    if response.status != 200:
                        return {"status": "error", "message": "Caddy admin API non accessible"}
                
                # Métriques
                metrics = {}
                try:
                    async with session.get(f"{self.admin_url}/metrics") as response:
                        if response.status == 200:
                            metrics_text = await response.text()
                            metrics = self._parse_prometheus_metrics(metrics_text)
                except:
                    pass
                
                return {
                    "status": "running",
                    "routes_count": len([r for r in self.routes.values() if r.enabled]),
                    "total_routes": len(self.routes),
                    "metrics": metrics,
                    "admin_url": self.admin_url
                }
        except Exception as e:
            logger.error(f"Erreur statut Caddy: {e}")
            return {"status": "error", "message": str(e)}

    def _parse_prometheus_metrics(self, metrics_text: str) -> Dict[str, Any]:
        """Parse les métriques Prometheus de Caddy"""
        metrics = {}
        try:
            lines = metrics_text.split('\n')
            for line in lines:
                if line.startswith('caddy_http_requests_total'):
                    # Parser les métriques de base
                    pass
        except:
            pass
        return metrics

    async def backup_configuration(self) -> str:
        """Sauvegarde la configuration actuelle"""
        try:
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "global_config": self.global_config,
                "routes": {route_id: asdict(route) for route_id, route in self.routes.items()}
            }
            
            backup_filename = f"caddy_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_path = f"/app/data/backups/{backup_filename}"
            
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            async with aiofiles.open(backup_path, 'w') as f:
                await f.write(json.dumps(backup_data, indent=2, default=str))
            
            logger.info(f"Configuration sauvegardée: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Erreur sauvegarde configuration: {e}")
            raise

    async def restore_configuration(self, backup_path: str) -> bool:
        """Restaure une configuration depuis une sauvegarde"""
        try:
            async with aiofiles.open(backup_path, 'r') as f:
                backup_data = json.loads(await f.read())
            
            # Restaurer la configuration globale
            self.global_config = backup_data.get("global_config", self.global_config)
            
            # Restaurer les routes
            routes_data = backup_data.get("routes", {})
            self.routes = {}
            
            for route_id, route_data in routes_data.items():
                # Convertir les dates
                if "created_at" in route_data:
                    route_data["created_at"] = datetime.fromisoformat(route_data["created_at"])
                if "updated_at" in route_data:
                    route_data["updated_at"] = datetime.fromisoformat(route_data["updated_at"])
                
                # Reconstruire les objets
                matchers = [CaddyMatcher(**m) for m in route_data.get("matchers", [])]
                upstreams = [CaddyUpstream(**u) for u in route_data.get("upstreams", [])]
                
                route_data["matchers"] = matchers
                route_data["upstreams"] = upstreams
                
                self.routes[route_id] = CaddyRoute(**route_data)
            
            # Appliquer la configuration
            await self._apply_configuration()
            
            logger.info(f"Configuration restaurée depuis {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Erreur restauration configuration: {e}")
            return False

    async def validate_configuration(self) -> Dict[str, Any]:
        """Valide la configuration actuelle"""
        errors = []
        warnings = []
        
        # Vérifier les routes
        for route_id, route in self.routes.items():
            # Vérifier les domaines
            if not route.domain or route.domain == "unknown":
                errors.append(f"Route {route_id}: domaine invalide")
            
            # Vérifier les upstreams
            if not route.upstreams:
                errors.append(f"Route {route_id}: aucun upstream configuré")
            
            for upstream in route.upstreams:
                if not upstream.address:
                    errors.append(f"Route {route_id}: adresse upstream vide")
        
        # Vérifier les conflits de domaines
        domains = {}
        for route_id, route in self.routes.items():
            if route.enabled and route.domain in domains:
                warnings.append(f"Conflit de domaine: {route.domain} utilisé par {domains[route.domain]} et {route_id}")
            domains[route.domain] = route_id
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "routes_count": len(self.routes),
            "enabled_routes": len([r for r in self.routes.values() if r.enabled])
        }

    async def test_route(self, route_id: str) -> Dict[str, Any]:
        """Teste une route spécifique"""
        if route_id not in self.routes:
            return {"success": False, "error": "Route introuvable"}
        
        route = self.routes[route_id]
        results = []
        
        for upstream in route.upstreams:
            try:
                async with aiohttp.ClientSession() as session:
                    test_url = f"http://{upstream.address}{upstream.health_check_uri}"
                    async with session.get(test_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        results.append({
                            "upstream": upstream.address,
                            "status": response.status,
                            "success": 200 <= response.status < 400,
                            "response_time": "< 5s"
                        })
            except Exception as e:
                results.append({
                    "upstream": upstream.address,
                    "status": 0,
                    "success": False,
                    "error": str(e)
                })
        
        success_count = sum(1 for r in results if r["success"])
        
        return {
            "route_id": route_id,
            "domain": route.domain,
            "total_upstreams": len(results),
            "healthy_upstreams": success_count,
            "success": success_count > 0,
            "results": results
        }