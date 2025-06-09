# Guide d'intégration du Dashboard SelfStart

## 🔧 Intégration dans le projet principal

### 1. Mise à jour du docker-compose.yml

Ajouter le service dashboard au fichier `docker-compose.yml` principal :

```yaml
services:
  # ... services existants (caddy, backend-api, frontend-loader) ...

  # Dashboard d'administration
  frontend-dashboard:
    build: ./frontend-dashboard
    container_name: selfstart-dashboard
    restart: unless-stopped
    ports:
      - "${DASHBOARD_PORT:-3001}:3000"
    environment:
      - VITE_API_URL=http://backend-api:8000
      - VITE_POLLING_INTERVAL=${POLLING_INTERVAL:-2000}
    networks:
      - selfstart-network
    depends_on:
      - backend-api
    profiles: ["dashboard"]
```

### 2. Mise à jour du Caddyfile

Ajouter dans `caddy/Caddyfile` :

```caddyfile
# Interface d'administration SelfStart
admin.{$BASE_DOMAIN} {
    reverse_proxy frontend-dashboard:3000 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
    
    # Authentification basique (optionnelle)
    @auth_enabled `test "${ENABLE_DASHBOARD_AUTH:-false}" = "true"`
    handle @auth_enabled {
        basicauth {
            {$ADMIN_USERNAME} {$ADMIN_PASSWORD_HASH}
        }
    }
    
    log {
        output file /var/log/caddy/admin.log
        level INFO
    }
}

# Accès local pour développement
localhost:3001 {
    reverse_proxy frontend-dashboard:3000
}
```

### 3. Variables d'environnement (.env.example)

Ajouter au fichier `.env.example` :

```env
# =============================================================================
# CONFIGURATION DASHBOARD
# =============================================================================

# Port du Dashboard d'administration
DASHBOARD_PORT=3001

# Authentification Dashboard
ENABLE_DASHBOARD_AUTH=false
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_password_here
# Hash du mot de passe (générer avec: caddy hash-password)
ADMIN_PASSWORD_HASH=$2a$14$Zkx19XLiW6VYouLHR5NmfOFU0z2GTNOWNvhHn.b6jCa7Jb.0Kfxh2
```

### 4. Mise à jour du Makefile

Ajouter les commandes dashboard :

```makefile
dashboard: ## Démarre le dashboard d'administration
	@echo "$(GREEN)🎛️  Démarrage du dashboard...$(NC)"
	@docker-compose --profile dashboard up -d
	@echo "$(GREEN)✅ Dashboard disponible sur http://localhost:3001$(NC)"

dashboard-build: ## Reconstruit le dashboard
	@echo "$(GREEN)🔨 Construction du dashboard...$(NC)"
	@docker-compose build frontend-dashboard
	@echo "$(GREEN)✅ Dashboard reconstruit$(NC)"

dashboard-logs: ## Affiche les logs du dashboard
	@docker-compose logs -f frontend-dashboard

dashboard-stop: ## Arrête le dashboard
	@docker-compose --profile dashboard down
```

### 5. Extensions API Backend requises

Créer `backend-api/dashboard_api.py` :

```python
from fastapi import APIRouter, HTTPException
import psutil
import docker
from datetime import datetime
from typing import List, Dict, Any

router = APIRouter(prefix="/api", tags=["dashboard"])

@router.get("/system/metrics")
async def get_system_metrics():
    """Récupère les métriques système temps réel"""
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Mémoire
        memory = psutil.virtual_memory()
        
        # Disque
        disk = psutil.disk_usage('/')
        
        # Réseau
        network = psutil.net_io_counters()
        
        return {
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "memory_total": memory.total // (1024**3),  # GB
            "memory_used": memory.used // (1024**3),    # GB
            "disk_usage": (disk.used / disk.total) * 100,
            "disk_total": disk.total // (1024**3),      # GB
            "disk_free": disk.free // (1024**3),        # GB
            "network_bytes_sent": network.bytes_sent,
            "network_bytes_recv": network.bytes_recv,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur métriques: {str(e)}")

@router.get("/containers/detailed")
async def get_containers_detailed():
    """Récupère des informations détaillées sur tous les containers"""
    try:
        client = docker.from_env()
        containers = []
        
        for container in client.containers.list(all=True):
            # Stats du container si running
            stats = {}
            if container.status == "running":
                try:
                    stats_stream = container.stats(stream=False)
                    # Calcul CPU %
                    cpu_delta = stats_stream["cpu_stats"]["cpu_usage"]["total_usage"] - \
                               stats_stream["precpu_stats"]["cpu_usage"]["total_usage"]
                    system_delta = stats_stream["cpu_stats"]["system_cpu_usage"] - \
                                  stats_stream["precpu_stats"]["system_cpu_usage"]
                    cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0
                    
                    # Mémoire
                    memory_usage = stats_stream["memory_stats"]["usage"]
                    memory_limit = stats_stream["memory_stats"]["limit"]
                    memory_percent = (memory_usage / memory_limit) * 100 if memory_limit > 0 else 0
                    
                    stats = {
                        "cpu_percent": round(cpu_percent, 2),
                        "memory_usage_mb": round(memory_usage / (1024*1024), 2),
                        "memory_limit_mb": round(memory_limit / (1024*1024), 2),
                        "memory_percent": round(memory_percent, 2)
                    }
                except:
                    stats = {"cpu_percent": 0, "memory_usage_mb": 0, "memory_percent": 0}
            
            # Ports
            ports = []
            if container.ports:
                for container_port, host_configs in container.ports.items():
                    if host_configs:
                        ports.append({
                            "container_port": container_port,
                            "host_port": host_configs[0]["HostPort"]
                        })
            
            containers.append({
                "id": container.id[:12],
                "name": container.name,
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "created": container.attrs["Created"],
                "ports": ports,
                "labels": container.labels,
                "stats": stats
            })
        
        return {"containers": containers, "total": len(containers)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur containers: {str(e)}")

@router.get("/system/info")
async def get_system_info():
    """Informations système générales"""
    try:
        uname = psutil.uname()
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        
        return {
            "hostname": uname.node,
            "system": uname.system,
            "release": uname.release,
            "machine": uname.machine,
            "processor": uname.processor,
            "boot_time": boot_time.isoformat(),
            "cpu_count": psutil.cpu_count(),
            "cpu_count_logical": psutil.cpu_count(logical=True)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur info système: {str(e)}")
```

Et l'ajouter dans `main.py` :

```python
from dashboard_api import router as dashboard_router

app.include_router(dashboard_router)
```

### 6. Script de déploiement automatique

Créer `deploy-dashboard.sh` :

```bash
#!/bin/bash

echo "🚀 Déploiement du Dashboard SelfStart..."

# Vérifier que Docker fonctionne
if ! docker ps >/dev/null 2>&1; then
    echo "❌ Docker n'est pas accessible"
    exit 1
fi

# Construire le dashboard
echo "📦 Construction du dashboard..."
docker-compose build frontend-dashboard

# Démarrer avec le profil dashboard
echo "🎛️ Démarrage du dashboard..."
docker-compose --profile dashboard up -d

# Attendre que le service soit prêt
echo "⏳ Attente du démarrage..."
sleep 10

# Vérifier l'état
if docker-compose ps frontend-dashboard | grep -q "Up"; then
    echo "✅ Dashboard démarré avec succès!"
    echo ""
    echo "🌐 Accès:"
    
    # Récupérer le domaine depuis .env
    if [ -f .env ]; then
        DOMAIN=$(grep "BASE_DOMAIN=" .env | cut -d'=' -f2)
        if [ "$DOMAIN" != "localhost" ] && [ "$DOMAIN" != "" ]; then
            echo "  🔗 Interface admin: https://admin.$DOMAIN"
        fi
    fi
    
    echo "  🔗 Accès local: http://localhost:3001"
    echo "  📊 API: http://localhost:8000/docs"
else
    echo "❌ Échec du démarrage du dashboard"
    echo "📋 Logs:"
    docker-compose logs frontend-dashboard
    exit 1
fi
```

## 🎯 **Instructions de déploiement :**

### Méthode 1: Avec le profil dashboard

```bash
# Démarrer SelfStart avec dashboard
docker-compose --profile dashboard up -d

# Ou avec make
make dashboard
```

### Méthode 2: Script automatique

```bash
# Rendre exécutable et lancer
chmod +x deploy-dashboard.sh
./deploy-dashboard.sh
```

### Méthode 3: Intégration complète

```bash
# Modifier docker-compose.yml pour inclure le dashboard par défaut
# Puis redémarrer
make restart
```

## 🔐 **Configuration sécurisée :**

```bash
# 1. Générer un hash de mot de passe
docker run --rm caddy:2-alpine caddy hash-password --plaintext "votre_mot_de_passe"

# 2. Ajouter dans .env
echo "ENABLE_DASHBOARD_AUTH=true" >> .env
echo "ADMIN_PASSWORD_HASH=\$2a\$14\$..." >> .env

# 3. Redémarrer Caddy
docker-compose restart caddy
```

---

**Le dashboard SelfStart est maintenant prêt à être intégré ! 🎉**

✅ **Code modulaire et maintenable**  
✅ **Interface moderne et responsive**  
✅ **Intégration complète documentée**  
✅ **Sécurité et authentification**  
✅ **Monitoring temps réel**  
✅ **Prêt pour la production**
