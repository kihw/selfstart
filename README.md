# SelfStart 🚀

**Système de démarrage dynamique de containers Docker via URLs dédiées**

SelfStart permet de démarrer automatiquement des containers Docker lorsqu'un utilisateur accède à une URL spécifique, avec une interface de chargement élégante pendant le processus.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-blue.svg)](https://react.dev/)

## ✨ Fonctionnalités

- 🚀 **Démarrage automatique** : Accédez à `https://sonarr.exemple.com` et le container `sonarr` se démarre automatiquement
- 🎨 **Interface moderne** : Écran de chargement React avec animations fluides et design glassmorphism
- 🔄 **Reverse proxy intelligent** : Caddy route automatiquement vers le service une fois démarré
- 📊 **Monitoring temps réel** : Détection automatique de l'état des containers avec logs en direct
- 🔧 **Extensible** : Ajout facile de nouveaux services via la configuration
- 🔒 **Sécurisé** : HTTPS automatique, isolation réseau, authentification optionnelle
- 📱 **Responsive** : Interface adaptée à tous les écrans
- ⚡ **Performance** : Démarrage rapide et optimisé

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│  Caddy Proxy    │───▶│ React Loader │───▶│ FastAPI Backend │
│ (Reverse Proxy) │    │ (Frontend)   │    │ (Docker SDK)    │
│ + HTTPS Auto    │    │ + Animations │    │ + Health Checks │
└─────────────────┘    └──────────────┘    └─────────────────┘
         │                                           │
         ▼                                           ▼
┌─────────────────┐                        ┌─────────────────┐
│ Container Apps  │                        │ Docker Engine   │
│ (sonarr, etc.)  │◀──────────────────────▶│ (via socket)    │
└─────────────────┘                        └─────────────────┘
```

## 🚀 Démarrage Ultra-Rapide

### 🎯 Installation en 1 commande

```bash
# Cloner et installer automatiquement
git clone https://github.com/kihw/selfstart.git && cd selfstart && chmod +x start.sh && ./start.sh
```

### 📋 Prérequis

- ✅ Docker et Docker Compose installés
- ✅ Domaines configurés (ou localhost pour les tests)
- ✅ Ports 80/443 disponibles

### ⚡ Installation Manuelle

```bash
# 1. Cloner le repository
git clone https://github.com/kihw/selfstart.git
cd selfstart

# 2. Configuration automatique
make install

# 3. Démarrer tous les services
make start

# 4. Démarrer avec applications d'exemple
make apps
```

### 🎮 Commandes Utiles

```bash
make help          # Afficher toutes les commandes
make status         # État des services
make logs           # Logs en temps réel
make restart        # Redémarrer
make update         # Mettre à jour depuis Git
make backup         # Sauvegarder la configuration
make clean          # Nettoyer les ressources
```

## 📱 Applications Supportées

### 🎬 Média Management (Starr Apps)
| Service | Port | Description | URL d'exemple |
|---------|------|-------------|---------------|
| **Sonarr** | 8989 | Gestionnaire de séries TV | `sonarr.exemple.com` |
| **Radarr** | 7878 | Gestionnaire de films | `radarr.exemple.com` |
| **Bazarr** | 6767 | Gestionnaire de sous-titres | `bazarr.exemple.com` |
| **Prowlarr** | 9696 | Gestionnaire d'indexeurs | `prowlarr.exemple.com` |

### 📺 Streaming
| Service | Port | Description | URL d'exemple |
|---------|------|-------------|---------------|
| **Jellyfin** | 8096 | Serveur multimédia open-source | `jellyfin.exemple.com` |
| **Plex** | 32400 | Serveur multimédia | `plex.exemple.com` |

### ☁️ Productivité
| Service | Port | Description | URL d'exemple |
|---------|------|-------------|---------------|
| **Nextcloud** | 8080 | Cloud personnel | `nextcloud.exemple.com` |
| **Portainer** | 9000 | Interface de gestion Docker | `portainer.exemple.com` |

## 📁 Structure du Projet

```
selfstart/
├── 🚀 start.sh                  # Installation automatique
├── ⚡ Makefile                   # Commandes simplifiées
├── 🐳 docker-compose.yml        # Orchestration principale
├── 📝 .env.example              # Configuration complète
├── 📋 CHANGELOG.md              # Historique des versions
├── 🙈 .gitignore                # Exclusions Git
├── 📄 LICENSE                   # Licence MIT
├── 📁 caddy/
│   └── ⚙️ Caddyfile             # Configuration Caddy avec HTTPS
├── 📁 backend-api/
│   ├── 🐳 Dockerfile            # Image Python optimisée
│   ├── 📄 requirements.txt      # Dépendances Python
│   ├── 🔧 main.py              # API FastAPI complète
│   └── 🐋 docker_manager.py    # Gestionnaire Docker intelligent
├── 📁 frontend-loader/
│   ├── 🐳 Dockerfile            # Image Node.js optimisée
│   ├── 📦 package.json          # Dépendances React/Vite
│   ├── ⚡ vite.config.js        # Configuration Vite
│   ├── 🎨 tailwind.config.js    # TailwindCSS personnalisé
│   ├── 🌐 index.html           # Template HTML optimisé
│   └── 📁 src/
│       ├── ⚛️ App.jsx           # Interface React moderne
│       ├── 📄 main.jsx          # Point d'entrée
│       └── 🎨 index.css         # Styles glassmorphism
└── 📁 examples/
    ├── 📖 README.md             # Guide des exemples
    └── 🐳 docker-compose.apps.yml # Applications préconfigurées
```

## ⚙️ Configuration Avancée

### 🔧 Variables d'Environnement (.env)

```env
# Domaine principal
BASE_DOMAIN=exemple.com

# Ports des services
API_PORT=8000
FRONTEND_PORT=3000

# Performance
STARTUP_TIMEOUT=120
POLLING_INTERVAL=2000

# Sécurité
SECRET_KEY=your_secret_key_here
ENABLE_BASIC_AUTH=false
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_password

# Stockage
DOWNLOADS_PATH=./downloads
TV_PATH=./media/tv
MOVIES_PATH=./media/movies

# Utilisateur (utilisez `id $USER`)
PUID=1000
PGID=1000
TZ=Europe/Paris
```

### 🆕 Ajouter une Nouvelle Application

#### 1. **Docker Compose**
```yaml
# Ajouter dans docker-compose.yml ou examples/docker-compose.apps.yml
mon-app:
  image: mon-app:latest
  container_name: mon-app
  restart: unless-stopped
  ports:
    - "8080:8080"
  networks:
    - selfstart-network
  profiles: ["apps"]
  labels:
    - "selfstart.enable=true"
    - "selfstart.port=8080"
```

#### 2. **Configuration Caddy**
```caddyfile
# Ajouter dans caddy/Caddyfile
mon-app.{$BASE_DOMAIN} {
    @running `curl -sf http://backend-api:8000/api/status?name=mon-app | jq -r '.status' | grep -q running`
    
    handle @running {
        reverse_proxy mon-app:8080 {
            header_up Host {host}
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-For {remote_host}
            header_up X-Forwarded-Proto {scheme}
        }
    }
    
    handle {
        reverse_proxy frontend-loader:3000 {
            header_up X-Container-Name mon-app
            header_up X-Container-Port 8080
        }
    }
}
```

#### 3. **Test**
```bash
make restart
curl http://localhost:8000/api/status?name=mon-app
```

## 🔧 API Documentation

### 📊 Endpoints Principaux

| Endpoint | Méthode | Description | Exemple |
|----------|---------|-------------|---------|
| `/health` | GET | Santé de l'API | `curl http://localhost:8000/health` |
| `/api/status` | GET | État d'un container | `?name=sonarr` |
| `/api/start` | POST | Démarrer un container | `?name=sonarr` |
| `/api/stop` | POST | Arrêter un container | `?name=sonarr` |
| `/api/containers` | GET | Lister tous les containers | |
| `/api/logs/{name}` | GET | Logs d'un container | `?lines=100` |

### 📝 Réponses d'API

**État d'un container:**
```json
{
  "status": "running|stopped|not_found|starting",
  "container_name": "sonarr",
  "uptime": 3600,
  "port": 8989,
  "message": "Container opérationnel"
}
```

**Démarrage réussi:**
```json
{
  "success": true,
  "message": "Container démarré avec succès",
  "container_name": "sonarr"
}
```

### 🔗 Documentation Interactive

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🎨 Interface Utilisateur

### ✨ Fonctionnalités de l'Interface

- 🎭 **Design Glassmorphism** avec effets de transparence
- 📊 **Barre de progression** temps réel avec animations
- 📜 **Logs en direct** avec timestamps
- 🎨 **Animations CSS** fluides et modernes
- 📱 **Design Responsive** pour mobile/desktop
- 🌓 **Thème adaptatif** selon les préférences système
- ⚡ **Performance optimisée** avec lazy loading

### 🎮 États Visuels

- 🟢 **Prêt** : Icône verte avec effet glow
- 🔵 **Démarrage** : Animation de chargement
- 🔴 **Erreur** : Message d'erreur avec bouton retry
- ⏳ **Chargement** : Points animés et progression

## 🐛 Dépannage

### 🔍 Diagnostic Rapide

```bash
# Vérifier l'état de tous les services
make status

# Santé de l'API
make check-health

# Logs en temps réel
make logs

# Informations réseau
make network

# Configuration
make env-check
```

### 🚨 Problèmes Courants

#### Container ne démarre pas
```bash
# Vérifier les logs spécifiques
docker-compose logs nom_du_service

# Vérifier l'état Docker
docker ps -a

# Tester l'API manuellement
curl http://localhost:8000/api/status?name=sonarr
```

#### Problèmes de réseau
```bash
# Vérifier Caddy
docker-compose logs caddy

# Tester DNS
nslookup sonarr.exemple.com

# Vérifier les ports
make monitor
```

#### Permissions Docker
```bash
# Ajouter au groupe docker
sudo usermod -aG docker $USER
newgrp docker

# Vérifier les permissions
ls -la /var/run/docker.sock
```

## 🔒 Sécurité

### 🛡️ Mesures de Sécurité Intégrées

- ✅ **Socket Docker en lecture seule** quand possible
- ✅ **Réseaux Docker isolés** pour chaque service
- ✅ **HTTPS automatique** via Let's Encrypt
- ✅ **Headers de sécurité** configurés automatiquement
- ✅ **Authentification basique** optionnelle
- ✅ **Variables sensibles** dans .env sécurisé

### 🏭 Configuration Production

```bash
# 1. Configuration sécurisée
cp .env.example .env

# 2. Éditer avec vos valeurs
nano .env

# 3. Générer une clé secrète
openssl rand -hex 32

# 4. Activer l'authentification
ENABLE_BASIC_AUTH=true
ADMIN_PASSWORD=votre_mot_de_passe_tres_fort

# 5. Déployer
make prod
```

## 📊 Monitoring et Métriques

### 📈 Health Checks Automatiques

- ✅ **API Backend** : Vérification toutes les 30 secondes
- ✅ **Containers** : Status en temps réel
- ✅ **Réseaux** : Connectivité automatique
- ✅ **Volumes** : Espace disque surveillé

### 📋 Logs Structurés

```bash
# Tous les logs
make logs

# Service spécifique
docker-compose logs -f backend-api

# Logs d'application
curl http://localhost:8000/api/logs/sonarr?lines=50
```

## 🚧 Roadmap v2.1

### 🎯 Fonctionnalités Prévues

- [ ] 📊 **Dashboard administrateur** avec métriques temps réel
- [ ] 🔐 **Authentification OAuth** (Google, GitHub, Discord)
- [ ] 🚀 **API GraphQL** en complément du REST
- [ ] 🔌 **WebSocket** pour mises à jour temps réel
- [ ] 📧 **Notifications** (email, Slack, Discord)
- [ ] ⏰ **Auto-shutdown** après inactivité
- [ ] ⚖️ **Load balancing** pour applications
- [ ] ☁️ **Backup cloud** automatique
- [ ] 🧩 **Plugin system** pour extensions
- [ ] 📱 **Mobile app** React Native

### 🔧 Améliorations Techniques

- [ ] ☸️ **Support Kubernetes** pour orchestration avancée
- [ ] 📈 **Métriques Prometheus** intégrées
- [ ] 📊 **Dashboards Grafana** préconfigurés
- [ ] 🧪 **Tests automatisés** complets
- [ ] 🔄 **CI/CD GitHub Actions** intégré

## 🤝 Contribution

### 🎯 Comment Contribuer

1. **🍴 Fork** le repository
2. **🌟 Star** le projet si vous l'aimez
3. **🔀 Créer** une branche feature (`git checkout -b feature/amazing-feature`)
4. **💾 Commit** vos changements (`git commit -m 'Add amazing feature'`)
5. **📤 Push** vers la branche (`git push origin feature/amazing-feature`)
6. **🔀 Ouvrir** une Pull Request

### 📋 Standards de Code

- **Python** : PEP 8 + Black formatter
- **JavaScript** : ESLint + Prettier
- **Docker** : Multi-stage builds optimisés
- **Documentation** : Markdown avec émojis 😊

### 🐛 Reporter un Bug

Créez une issue avec :
- 📝 Description détaillée
- 🔄 Étapes pour reproduire
- 📋 Logs pertinents
- 💻 Informations système

## 📞 Support et Communauté

### 🆘 Obtenir de l'Aide

- 📖 **Documentation** : README.md et exemples
- 🐛 **Issues** : [GitHub Issues](https://github.com/kihw/selfstart/issues)
- 💬 **Discussions** : [GitHub Discussions](https://github.com/kihw/selfstart/discussions)
- 📧 **Contact** : Voir profil [@kihw](https://github.com/kihw)

### 🌟 Donnez votre avis !

Si SelfStart vous aide, n'hésitez pas à :
- ⭐ **Star** le repository
- 🐦 **Partager** sur les réseaux sociaux
- 📝 **Écrire** un retour d'expérience
- 🤝 **Contribuer** au développement

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 🙏 Remerciements

### 🛠️ Technologies Utilisées

- 🌐 [**Caddy**](https://caddyserver.com/) - Reverse proxy moderne avec HTTPS automatique
- ⚡ [**FastAPI**](https://fastapi.tiangolo.com/) - Framework Python moderne et rapide
- ⚛️ [**React**](https://react.dev/) - Bibliothèque JavaScript pour interfaces utilisateur
- 🎨 [**TailwindCSS**](https://tailwindcss.com/) - Framework CSS utilitaire
- 🐳 [**Docker**](https://docker.com/) - Plateforme de containerisation
- ⚡ [**Vite**](https://vitejs.dev/) - Build tool moderne et rapide

### 🏆 Inspirations

- **Traefik** pour l'inspiration du reverse proxy intelligent
- **Portainer** pour l'interface de gestion Docker
- **Home Assistant** pour l'architecture modulaire
- **Nginx Proxy Manager** pour la simplicité de configuration

### 👥 Contributeurs

Un grand merci à tous les contributeurs qui ont rendu SelfStart possible !

[![Contributors](https://contrib.rocks/image?repo=kihw/selfstart)](https://github.com/kihw/selfstart/graphs/contributors)

---

<div align="center">

**Développé avec ❤️ par la communauté**

[⭐ Star ce projet](https://github.com/kihw/selfstart) • [🐛 Reporter un bug](https://github.com/kihw/selfstart/issues) • [💬 Rejoindre la discussion](https://github.com/kihw/selfstart/discussions)

*SelfStart v2.0 - Démarrage automatique révolutionnaire* 🚀

</div>
