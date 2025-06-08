# SelfStart 🚀

**Système de démarrage dynamique de containers Docker via URLs dédiées**

SelfStart permet de démarrer automatiquement des containers Docker lorsqu'un utilisateur accède à une URL spécifique, avec une interface de chargement élégante pendant le processus.

## 🎯 Fonctionnalités

- **Démarrage automatique** : Accédez à `https://sonarr.exemple.com` et le container `sonarr` se démarre automatiquement
- **Interface de chargement** : Écran de chargement React avec animations pendant le démarrage
- **Reverse proxy intelligent** : Caddy route automatiquement vers le service une fois démarré
- **Gestion d'état** : Détection automatique de l'état des containers (running/stopped)
- **Extensible** : Ajout facile de nouveaux services via la configuration

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│  Caddy Proxy    │───▶│ React Loader │───▶│ FastAPI Backend │
│ (Reverse Proxy) │    │ (Frontend)   │    │ (Docker SDK)    │
└─────────────────┘    └──────────────┘    └─────────────────┘
         │                                           │
         ▼                                           ▼
┌─────────────────┐                        ┌─────────────────┐
│ Container Apps  │                        │ Docker Engine   │
│ (sonarr, etc.)  │                        │ (via socket)    │
└─────────────────┘                        └─────────────────┘
```

## 🚀 Démarrage rapide

### Prérequis

- Docker et Docker Compose installés
- Domaines configurés (ou utiliser localhost pour les tests)

### Installation

1. **Cloner le repository**
   ```bash
   git clone https://github.com/kihw/selfstart.git
   cd selfstart
   ```

2. **Configuration**
   ```bash
   # Copier le fichier d'exemple
   cp .env.example .env
   
   # Éditer les domaines dans le Caddyfile
   nano caddy/Caddyfile
   ```

3. **Démarrer les services**
   ```bash
   docker-compose up -d
   ```

4. **Tester**
   - Accédez à votre domaine configuré (ex: `https://sonarr.exemple.com`)
   - Le container se démarre automatiquement avec l'interface de chargement
   - Une fois prêt, vous êtes redirigé vers l'application

## 📁 Structure du projet

```
selfstart/
├── 📄 README.md
├── 📄 docker-compose.yml          # Orchestration principale
├── 📄 .env.example               # Variables d'environnement
├── 📁 caddy/
│   └── 📄 Caddyfile              # Configuration reverse proxy
├── 📁 backend-api/
│   ├── 📄 Dockerfile
│   ├── 📄 requirements.txt
│   ├── 📄 main.py               # API FastAPI
│   └── 📄 docker_manager.py     # Gestion containers
├── 📁 frontend-loader/
│   ├── 📄 Dockerfile
│   ├── 📄 package.json
│   ├── 📄 vite.config.js
│   ├── 📄 tailwind.config.js
│   ├── 📁 src/
│   │   ├── 📄 App.jsx           # Interface principale
│   │   ├── 📄 main.jsx
│   │   └── 📄 index.css
│   └── 📄 index.html
└── 📁 examples/
    └── 📄 docker-compose.apps.yml # Exemples d'applications
```

## ⚙️ Configuration

### Variables d'environnement (.env)

```env
# Domaine principal
BASE_DOMAIN=exemple.com

# Configuration API
API_PORT=8000
FRONTEND_PORT=3000

# Timeout pour le démarrage des containers (secondes)
STARTUP_TIMEOUT=120

# Intervalle de polling (millisecondes)
POLLING_INTERVAL=2000
```

### Ajout de nouveaux services

1. **Configurer Caddy** (`caddy/Caddyfile`)
   ```caddyfile
   myapp.{$BASE_DOMAIN} {
       @running `curl -f http://backend-api:8000/api/status?name=myapp`
       handle @running {
           reverse_proxy myapp:8080
       }
       handle {
           reverse_proxy frontend-loader:3000
       }
   }
   ```

2. **Ajouter le container** dans votre `docker-compose.yml`
   ```yaml
   myapp:
     image: myapp:latest
     container_name: myapp
     ports:
       - "8080:8080"
     profiles: ["apps"]
   ```

## 🔧 API Endpoints

### `GET /api/status?name={container_name}`
Vérifie l'état d'un container

**Réponse :**
```json
{
  "status": "running|stopped|not_found",
  "container_name": "sonarr",
  "uptime": 3600
}
```

### `POST /api/start?name={container_name}`
Démarre un container

**Réponse :**
```json
{
  "success": true,
  "message": "Container started successfully",
  "container_name": "sonarr"
}
```

### `POST /api/stop?name={container_name}`
Arrête un container

**Réponse :**
```json
{
  "success": true,
  "message": "Container stopped successfully",
  "container_name": "sonarr"
}
```

## 🎨 Interface utilisateur

L'interface React propose :

- **Écran de chargement animé** pendant le démarrage
- **Indicateurs de progression** en temps réel
- **Messages d'erreur** en cas de problème
- **Design responsive** avec TailwindCSS
- **Thème sombre/clair** automatique

## 🐛 Dépannage

### Container ne démarre pas

```bash
# Vérifier les logs
docker-compose logs backend-api

# Vérifier l'état du container
docker ps -a | grep nom_container

# Tester l'API manuellement
curl http://localhost:8000/api/status?name=sonarr
```

### Problèmes de reverse proxy

```bash
# Vérifier la configuration Caddy
docker-compose logs caddy

# Tester la résolution DNS
nslookup sonarr.exemple.com

# Vérifier les ports
netstat -tlnp | grep :80
netstat -tlnp | grep :443
```

### Permissions Docker

```bash
# Vérifier les permissions du socket Docker
ls -la /var/run/docker.sock

# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER
```

## 🔒 Sécurité

- Le socket Docker est monté en lecture seule quand possible
- Authentification basique intégrée (optionnelle)
- HTTPS automatique via Caddy et Let's Encrypt
- Isolation des containers via Docker networks

## 🚧 Roadmap

- [ ] **Authentification** : Intégration OAuth/LDAP
- [ ] **Dashboard** : Interface d'administration web
- [ ] **Monitoring** : Métriques et alertes
- [ ] **Auto-shutdown** : Arrêt automatique après inactivité
- [ ] **Load balancing** : Gestion de plusieurs instances
- [ ] **WebSocket** : Mises à jour en temps réel

## 🤝 Contribution

1. Forkez le projet
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/amazing-feature`)
3. Committez vos changements (`git commit -m 'Add amazing feature'`)
4. Pushez vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrez une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🙏 Remerciements

- [Caddy](https://caddyserver.com/) pour le reverse proxy
- [FastAPI](https://fastapi.tiangolo.com/) pour l'API backend
- [React](https://react.dev/) pour l'interface utilisateur
- [TailwindCSS](https://tailwindcss.com/) pour le design
- [Docker](https://docker.com/) pour la containerisation

---

**Fait avec ❤️ par la communauté**