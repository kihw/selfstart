# Exemples d'applications SelfStart

Ce répertoire contient des exemples de configurations pour différentes applications populaires que vous pouvez utiliser avec SelfStart.

## 🚀 Utilisation

### Démarrage des applications d'exemple

1. **Copier la configuration des applications :**
   ```bash
   # Fusionner avec votre docker-compose.yml principal
   docker-compose -f docker-compose.yml -f examples/docker-compose.apps.yml up -d
   
   # Ou utiliser uniquement les exemples
   docker-compose -f examples/docker-compose.apps.yml --profile apps up -d
   ```

2. **Configurer Caddy pour les nouveaux services :**
   Ajoutez les entrées correspondantes dans votre `caddy/Caddyfile` :
   
   ```caddyfile
   bazarr.{$BASE_DOMAIN} {
       @running `curl -sf http://backend-api:8000/api/status?name=bazarr | jq -r '.status' | grep -q running`
       
       handle @running {
           reverse_proxy bazarr:6767
       }
       
       handle {
           reverse_proxy frontend-loader:3000 {
               header_up X-Container-Name bazarr
               header_up X-Container-Port 6767
           }
       }
   }
   ```

3. **Tester l'accès :**
   - `https://sonarr.votre-domaine.com`
   - `https://radarr.votre-domaine.com`
   - `https://jellyfin.votre-domaine.com`
   - etc.

## 📋 Applications disponibles

### 🎬 Média

| Service | Port | Description | URL d'exemple |
|---------|------|-------------|---------------|
| **Sonarr** | 8989 | Gestionnaire de séries TV | `sonarr.exemple.com` |
| **Radarr** | 7878 | Gestionnaire de films | `radarr.exemple.com` |
| **Bazarr** | 6767 | Gestionnaire de sous-titres | `bazarr.exemple.com` |
| **Jellyfin** | 8096 | Serveur multimédia open-source | `jellyfin.exemple.com` |
| **Plex** | 32400 | Serveur multimédia | `plex.exemple.com` |

### 🔍 Indexeurs

| Service | Port | Description | URL d'exemple |
|---------|------|-------------|---------------|
| **Prowlarr** | 9696 | Gestionnaire d'indexeurs | `prowlarr.exemple.com` |

### ☁️ Cloud & Productivité

| Service | Port | Description | URL d'exemple |
|---------|------|-------------|---------------|
| **Nextcloud** | 8080 | Cloud personnel | `nextcloud.exemple.com` |

### 🐳 Administration

| Service | Port | Description | URL d'exemple |
|---------|------|-------------|---------------|
| **Portainer** | 9000 | Interface de gestion Docker | `portainer.exemple.com` |

## ⚙️ Configuration personnalisée

### Variables d'environnement

Personnalisez les chemins dans votre `.env` :

```env
# Chemins de stockage
DOWNLOADS_PATH=/path/to/downloads
TV_PATH=/path/to/tv
MOVIES_PATH=/path/to/movies

# Configuration utilisateur
PUID=1000
PGID=1000
TZ=Europe/Paris
```

### Ajout d'une nouvelle application

1. **Ajouter le service dans docker-compose.yml :**
   ```yaml
   mon-app:
     image: mon-app:latest
     container_name: mon-app
     restart: unless-stopped
     ports:
       - "8080:8080"
     environment:
       - PUID=${PUID:-1000}
       - PGID=${PGID:-1000}
     volumes:
       - mon-app_config:/config
     networks:
       - selfstart-network
     profiles: ["apps"]
     labels:
       - "selfstart.enable=true"
       - "selfstart.port=8080"
       - "selfstart.name=mon-app"
   ```

2. **Configurer Caddy :**
   ```caddyfile
   mon-app.{$BASE_DOMAIN} {
       @running `curl -sf http://backend-api:8000/api/status?name=mon-app | jq -r '.status' | grep -q running`
       
       handle @running {
           reverse_proxy mon-app:8080
       }
       
       handle {
           reverse_proxy frontend-loader:3000 {
               header_up X-Container-Name mon-app
               header_up X-Container-Port 8080
           }
       }
   }
   ```

3. **Ajouter le volume (si nécessaire) :**
   ```yaml
   volumes:
     mon-app_config:
   ```

## 🔒 Sécurité

### Authentification

Certaines applications nécessitent une configuration d'authentification :

- **Nextcloud** : Utilisateur par défaut `admin` / mot de passe `changeme` (à changer !)
- **Portainer** : Configuration au premier accès
- **Plex** : Configuration via l'interface web

### Réseaux

Tous les services utilisent le réseau `selfstart-network` pour une isolation appropriée.

### Volumes

Les données sont stockées dans des volumes Docker nommés pour la persistance et la sécurité.

## 🐛 Dépannage

### Problèmes courants

1. **Container ne démarre pas :**
   ```bash
   docker-compose logs nom-du-service
   ```

2. **Port déjà utilisé :**
   ```bash
   # Vérifier les ports utilisés
   netstat -tlnp | grep :8080
   
   # Modifier le port dans docker-compose.yml
   ports:
     - "8081:8080"  # Port externe différent
   ```

3. **Problèmes de permissions :**
   ```bash
   # Vérifier et ajuster PUID/PGID
   id $USER
   
   # Dans .env
   PUID=1000
   PGID=1000
   ```

### Logs et monitoring

```bash
# Suivre les logs en temps réel
docker-compose logs -f nom-du-service

# Vérifier l'état via l'API
curl http://localhost:8000/api/status?name=sonarr

# Lister tous les containers
curl http://localhost:8000/api/containers
```

## 📚 Ressources

- [Documentation Sonarr](https://wiki.servarr.com/sonarr)
- [Documentation Radarr](https://wiki.servarr.com/radarr)
- [Documentation Jellyfin](https://jellyfin.org/docs/)
- [Documentation Nextcloud](https://docs.nextcloud.com/)
- [Documentation Portainer](https://docs.portainer.io/)

---

**💡 Conseil :** Commencez avec quelques services simples comme Jellyfin ou Nextcloud avant d'ajouter la stack complète *arr (Sonarr, Radarr, etc.).