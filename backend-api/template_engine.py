import os
import json
import yaml
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path
import jinja2
from jinja2 import Environment, FileSystemLoader, Template, TemplateError
import aiofiles

logger = logging.getLogger(__name__)

@dataclass
class TemplateContext:
    """Contexte pour le rendu des templates"""
    # Variables système
    timestamp: datetime
    hostname: str
    base_domain: str
    api_port: int
    frontend_port: int
    
    # Variables d'environnement
    env_vars: Dict[str, str]
    
    # Services découverts
    services: List[Dict[str, Any]]
    
    # Métriques système
    system_metrics: Dict[str, Any]
    
    # Variables personnalisées
    custom_vars: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le contexte en dictionnaire pour Jinja2"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "hostname": self.hostname,
            "base_domain": self.base_domain,
            "api_port": self.api_port,
            "frontend_port": self.frontend_port,
            "env": self.env_vars,
            "services": self.services,
            "metrics": self.system_metrics,
            "custom": self.custom_vars,
            # Fonctions utilitaires
            "now": datetime.now,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool
        }

class TemplateEngine:
    """Moteur de templates pour SelfStart avec support Jinja2"""
    
    def __init__(self, templates_dir: str = "templates", enable_autoescape: bool = True):
        self.templates_dir = templates_dir
        self.enable_autoescape = enable_autoescape
        
        # Configuration Jinja2
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=enable_autoescape,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
        
        # Ajouter des filtres personnalisés
        self._add_custom_filters()
        
        # Ajouter des fonctions globales
        self._add_global_functions()
        
        # Cache des templates
        self.template_cache = {}
        self.cache_enabled = True
        
        # Créer le répertoire si nécessaire
        os.makedirs(templates_dir, exist_ok=True)

    def _add_custom_filters(self):
        """Ajoute des filtres personnalisés à Jinja2"""
        
        @self.env.filter
        def to_yaml(value):
            """Convertit une valeur en YAML"""
            return yaml.dump(value, default_flow_style=False)
        
        @self.env.filter
        def to_json(value, indent=2):
            """Convertit une valeur en JSON"""
            return json.dumps(value, indent=indent)
        
        @self.env.filter
        def service_by_name(services, name):
            """Filtre les services par nom"""
            return [s for s in services if s.get('name') == name]
        
        @self.env.filter
        def service_by_type(services, service_type):
            """Filtre les services par type"""
            return [s for s in services if s.get('type') == service_type]
        
        @self.env.filter
        def running_services(services):
            """Filtre uniquement les services en cours d'exécution"""
            return [s for s in services if s.get('status') == 'running']
        
        @self.env.filter
        def format_bytes(bytes_value):
            """Formate les bytes en unités lisibles"""
            if bytes_value < 1024:
                return f"{bytes_value} B"
            elif bytes_value < 1024 * 1024:
                return f"{bytes_value / 1024:.1f} KB"
            elif bytes_value < 1024 * 1024 * 1024:
                return f"{bytes_value / (1024 * 1024):.1f} MB"
            else:
                return f"{bytes_value / (1024 * 1024 * 1024):.1f} GB"
        
        @self.env.filter
        def format_duration(seconds):
            """Formate une durée en secondes"""
            if seconds < 60:
                return f"{seconds}s"
            elif seconds < 3600:
                return f"{seconds // 60}m {seconds % 60}s"
            else:
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                return f"{hours}h {minutes}m"
        
        @self.env.filter
        def env_default(value, default=""):
            """Récupère une variable d'environnement avec valeur par défaut"""
            return os.getenv(value, default)

    def _add_global_functions(self):
        """Ajoute des fonctions globales à Jinja2"""
        
        def generate_port(base_port, service_name):
            """Génère un port basé sur le hash du nom de service"""
            import hashlib
            hash_obj = hashlib.md5(service_name.encode())
            hash_int = int(hash_obj.hexdigest()[:4], 16)
            return base_port + (hash_int % 1000)
        
        def format_caddy_matcher(service_name, base_domain):
            """Génère un matcher Caddy pour un service"""
            return f"{service_name}.{base_domain}"
        
        def service_url(service_name, base_domain, protocol="https"):
            """Génère l'URL complète d'un service"""
            return f"{protocol}://{service_name}.{base_domain}"
        
        def load_secret(secret_name):
            """Charge un secret depuis les variables d'environnement"""
            return os.getenv(f"SECRET_{secret_name.upper()}", "")
        
        # Ajouter au contexte global
        self.env.globals.update({
            'generate_port': generate_port,
            'format_caddy_matcher': format_caddy_matcher,
            'service_url': service_url,
            'load_secret': load_secret
        })

    async def render_template(self, template_name: str, context: TemplateContext, 
                            output_file: Optional[str] = None) -> str:
        """Rend un template avec le contexte donné"""
        try:
            # Récupérer le template
            template = await self._get_template(template_name)
            
            # Préparer le contexte
            template_context = context.to_dict()
            
            # Rendre le template
            rendered = template.render(template_context)
            
            # Sauvegarder si un fichier de sortie est spécifié
            if output_file:
                await self._save_rendered_content(output_file, rendered)
            
            return rendered
            
        except TemplateError as e:
            logger.error(f"Erreur template {template_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Erreur rendu template {template_name}: {e}")
            raise

    async def _get_template(self, template_name: str) -> Template:
        """Récupère un template (avec cache)"""
        if self.cache_enabled and template_name in self.template_cache:
            template_info = self.template_cache[template_name]
            template_path = os.path.join(self.templates_dir, template_name)
            
            # Vérifier si le fichier a été modifié
            if os.path.exists(template_path):
                mtime = os.path.getmtime(template_path)
                if mtime == template_info['mtime']:
                    return template_info['template']
        
        # Charger le template
        template = self.env.get_template(template_name)
        
        # Mettre en cache
        if self.cache_enabled:
            template_path = os.path.join(self.templates_dir, template_name)
            mtime = os.path.getmtime(template_path) if os.path.exists(template_path) else 0
            self.template_cache[template_name] = {
                'template': template,
                'mtime': mtime
            }
        
        return template

    async def _save_rendered_content(self, output_file: str, content: str):
        """Sauvegarde le contenu rendu dans un fichier"""
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        async with aiofiles.open(output_file, 'w') as f:
            await f.write(content)

    async def render_from_string(self, template_string: str, context: TemplateContext) -> str:
        """Rend un template depuis une chaîne de caractères"""
        try:
            template = self.env.from_string(template_string)
            template_context = context.to_dict()
            return template.render(template_context)
        except TemplateError as e:
            logger.error(f"Erreur template string: {e}")
            raise

    async def validate_template(self, template_name: str) -> Dict[str, Any]:
        """Valide un template et retourne les erreurs/warnings"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "variables": [],
            "filters": [],
            "functions": []
        }
        
        try:
            template_path = os.path.join(self.templates_dir, template_name)
            
            if not os.path.exists(template_path):
                validation_result["valid"] = False
                validation_result["errors"].append(f"Template {template_name} introuvable")
                return validation_result
            
            # Charger et parser le template
            template = self.env.get_template(template_name)
            
            # Analyser l'AST pour extraire les variables utilisées
            ast = self.env.parse(template.source)
            variables = set()
            
            for node in ast.find_all(jinja2.nodes.Name):
                if isinstance(node.ctx, jinja2.nodes.Load):
                    variables.add(node.name)
            
            validation_result["variables"] = list(variables)
            
            # Test de rendu avec un contexte minimal
            try:
                test_context = TemplateContext(
                    timestamp=datetime.now(),
                    hostname="test",
                    base_domain="test.com",
                    api_port=8000,
                    frontend_port=3000,
                    env_vars={},
                    services=[],
                    system_metrics={},
                    custom_vars={}
                )
                
                template.render(test_context.to_dict())
                
            except Exception as e:
                validation_result["warnings"].append(f"Erreur potentielle: {str(e)}")
            
        except TemplateError as e:
            validation_result["valid"] = False
            validation_result["errors"].append(str(e))
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Erreur inattendue: {str(e)}")
        
        return validation_result

    async def list_templates(self) -> List[Dict[str, Any]]:
        """Liste tous les templates disponibles"""
        templates = []
        
        try:
            for root, dirs, files in os.walk(self.templates_dir):
                for file in files:
                    if file.endswith(('.j2', '.jinja', '.jinja2', '.template')):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, self.templates_dir)
                        
                        stat = os.stat(full_path)
                        
                        templates.append({
                            "name": rel_path,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "path": full_path
                        })
        except Exception as e:
            logger.error(f"Erreur listing templates: {e}")
        
        return templates

    async def create_template(self, template_name: str, content: str) -> bool:
        """Crée un nouveau template"""
        try:
            template_path = os.path.join(self.templates_dir, template_name)
            os.makedirs(os.path.dirname(template_path), exist_ok=True)
            
            async with aiofiles.open(template_path, 'w') as f:
                await f.write(content)
            
            # Invalider le cache
            if template_name in self.template_cache:
                del self.template_cache[template_name]
            
            logger.info(f"Template {template_name} créé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur création template {template_name}: {e}")
            return False

    async def update_template(self, template_name: str, content: str) -> bool:
        """Met à jour un template existant"""
        return await self.create_template(template_name, content)

    async def delete_template(self, template_name: str) -> bool:
        """Supprime un template"""
        try:
            template_path = os.path.join(self.templates_dir, template_name)
            
            if os.path.exists(template_path):
                os.remove(template_path)
                
                # Invalider le cache
                if template_name in self.template_cache:
                    del self.template_cache[template_name]
                
                logger.info(f"Template {template_name} supprimé")
                return True
            else:
                logger.warning(f"Template {template_name} introuvable")
                return False
                
        except Exception as e:
            logger.error(f"Erreur suppression template {template_name}: {e}")
            return False

    def clear_cache(self):
        """Vide le cache des templates"""
        self.template_cache.clear()
        logger.info("Cache des templates vidé")

class ConfigurationRenderer:
    """Gestionnaire pour le rendu automatique des configurations"""
    
    def __init__(self, template_engine: TemplateEngine, service_discovery=None):
        self.template_engine = template_engine
        self.service_discovery = service_discovery
        
        # Configuration du rendu automatique
        self.auto_render_enabled = True
        self.auto_render_templates = [
            "caddy/Caddyfile.j2",
            "docker-compose.override.yml.j2",
            "nginx/nginx.conf.j2"
        ]
        
        # Outputs par défaut
        self.template_outputs = {
            "caddy/Caddyfile.j2": "caddy/Caddyfile",
            "docker-compose.override.yml.j2": "docker-compose.override.yml",
            "nginx/nginx.conf.j2": "nginx/nginx.conf"
        }

    async def render_all_configurations(self) -> Dict[str, bool]:
        """Rend toutes les configurations automatiquement"""
        results = {}
        
        # Créer le contexte
        context = await self._create_context()
        
        for template_name in self.auto_render_templates:
            try:
                output_file = self.template_outputs.get(template_name)
                
                rendered = await self.template_engine.render_template(
                    template_name, 
                    context,
                    output_file
                )
                
                results[template_name] = True
                logger.info(f"Configuration {template_name} rendue avec succès")
                
            except Exception as e:
                logger.error(f"Erreur rendu {template_name}: {e}")
                results[template_name] = False
        
        return results

    async def _create_context(self) -> TemplateContext:
        """Crée le contexte pour le rendu des templates"""
        import socket
        import psutil
        
        # Variables système
        hostname = socket.gethostname()
        base_domain = os.getenv("BASE_DOMAIN", "localhost")
        api_port = int(os.getenv("API_PORT", "8000"))
        frontend_port = int(os.getenv("FRONTEND_PORT", "3000"))
        
        # Variables d'environnement
        env_vars = dict(os.environ)
        
        # Services découverts
        services = []
        if self.service_discovery:
            try:
                discovered_services = await self.service_discovery.get_all_services()
                services = [
                    {
                        "name": s.name,
                        "type": s.service_type.value,
                        "status": s.status.value,
                        "image": s.image,
                        "endpoints": [
                            {
                                "protocol": ep.protocol,
                                "host": ep.host,
                                "port": ep.port,
                                "path": ep.path,
                                "url": ep.url
                            }
                            for ep in s.endpoints
                        ],
                        "labels": s.labels,
                        "dependencies": s.dependencies,
                        "auto_scale_enabled": s.auto_scale_enabled
                    }
                    for s in discovered_services
                ]
            except Exception as e:
                logger.error(f"Erreur récupération services: {e}")
        
        # Métriques système
        try:
            system_metrics = {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
                "uptime": datetime.now().timestamp() - psutil.boot_time()
            }
        except Exception as e:
            logger.error(f"Erreur métriques système: {e}")
            system_metrics = {}
        
        # Variables personnalisées (à charger depuis un fichier de config)
        custom_vars = {}
        try:
            custom_config_path = "config/custom_vars.yml"
            if os.path.exists(custom_config_path):
                with open(custom_config_path, 'r') as f:
                    custom_vars = yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Erreur chargement variables personnalisées: {e}")
        
        return TemplateContext(
            timestamp=datetime.now(),
            hostname=hostname,
            base_domain=base_domain,
            api_port=api_port,
            frontend_port=frontend_port,
            env_vars=env_vars,
            services=services,
            system_metrics=system_metrics,
            custom_vars=custom_vars
        )

    async def render_single_config(self, template_name: str, 
                                 output_file: Optional[str] = None) -> str:
        """Rend une configuration spécifique"""
        context = await self._create_context()
        
        if output_file is None:
            output_file = self.template_outputs.get(template_name)
        
        return await self.template_engine.render_template(
            template_name, 
            context, 
            output_file
        )

    def add_auto_render_template(self, template_name: str, output_file: str):
        """Ajoute un template au rendu automatique"""
        if template_name not in self.auto_render_templates:
            self.auto_render_templates.append(template_name)
        self.template_outputs[template_name] = output_file

    def remove_auto_render_template(self, template_name: str):
        """Retire un template du rendu automatique"""
        if template_name in self.auto_render_templates:
            self.auto_render_templates.remove(template_name)
        if template_name in self.template_outputs:
            del self.template_outputs[template_name]

# Templates par défaut fournis avec SelfStart

CADDY_TEMPLATE = """# Configuration Caddy générée automatiquement par SelfStart
# Générée le {{ timestamp }}

# Configuration globale
{
    admin off
    email admin@{{ base_domain }}
    
    servers {
        protocols h1 h2 h3
    }
}

{% for service in services | running_services %}
# Service: {{ service.name }}
{{ service.name }}.{{ base_domain }} {
    @running `curl -sf http://{{ env.get('BACKEND_HOST', 'backend-api') }}:{{ api_port }}/api/status?name={{ service.name }} | grep -o '"status":"running"'`
    
    handle @running {
        {% for endpoint in service.endpoints %}
        reverse_proxy {{ endpoint.host }}:{{ endpoint.port }} {
            header_up Host {host}
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-For {remote_host}
            header_up X-Forwarded-Proto {scheme}
            timeout 30s
        }
        {% endfor %}
    }
    
    handle {
        reverse_proxy {{ env.get('FRONTEND_HOST', 'frontend-loader') }}:{{ frontend_port }} {
            header_up X-Container-Name {{ service.name }}
            {% if service.endpoints %}
            header_up X-Container-Port {{ service.endpoints[0].port }}
            {% endif %}
        }
    }
    
    log {
        output file /var/log/caddy/{{ service.name }}.log
        level INFO
    }
}

{% endfor %}

# Interface d'administration (si configurée)
{% if env.get('ENABLE_ADMIN_INTERFACE', 'false') == 'true' %}
admin.{{ base_domain }} {
    reverse_proxy frontend-dashboard:3001
    
    {% if env.get('ENABLE_BASIC_AUTH', 'false') == 'true' %}
    basicauth {
        {{ env.get('ADMIN_USERNAME', 'admin') }} {{ env.get('ADMIN_PASSWORD_HASH', '') }}
    }
    {% endif %}
}
{% endif %}

# Configuration locale pour développement
{% if base_domain == 'localhost' %}
localhost:{{ api_port }} {
    reverse_proxy backend-api:8000
}

localhost:{{ frontend_port }} {
    reverse_proxy frontend-loader:3000
}
{% endif %}
"""

DOCKER_COMPOSE_OVERRIDE_TEMPLATE = """# Docker Compose override généré automatiquement
# Généré le {{ timestamp }}

version: '3.8'

services:
{% for service in services %}
  # Service découvert: {{ service.name }}
  {{ service.name }}:
    labels:
      - "selfstart.discovered=true"
      - "selfstart.type={{ service.type }}"
      - "selfstart.status={{ service.status }}"
      {% if service.auto_scale_enabled %}
      - "selfstart.auto_scale=true"
      {% endif %}
    networks:
      - selfstart-network
    {% if service.status == 'running' %}
    restart: unless-stopped
    {% endif %}

{% endfor %}

networks:
  selfstart-network:
    external: true

# Variables d'environnement injectées
x-environment-defaults: &default-env
  TZ: {{ env.get('TZ', 'UTC') }}
  PUID: {{ env.get('PUID', '1000') }}
  PGID: {{ env.get('PGID', '1000') }}
"""

async def initialize_default_templates(template_engine: TemplateEngine):
    """Initialise les templates par défaut"""
    default_templates = {
        "caddy/Caddyfile.j2": CADDY_TEMPLATE,
        "docker-compose.override.yml.j2": DOCKER_COMPOSE_OVERRIDE_TEMPLATE
    }
    
    for template_name, content in default_templates.items():
        try:
            template_path = os.path.join(template_engine.templates_dir, template_name)
            if not os.path.exists(template_path):
                await template_engine.create_template(template_name, content)
                logger.info(f"Template par défaut créé: {template_name}")
        except Exception as e:
            logger.error(f"Erreur création template par défaut {template_name}: {e}")
