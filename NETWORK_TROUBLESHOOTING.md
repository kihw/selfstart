# 🔧 Guide de diagnostic réseau SelfStart

Ce document vous aide à diagnostiquer et résoudre les problèmes de communication réseau entre les containers Docker de SelfStart.

## 🌐 Architecture réseau

SelfStart utilise un réseau Docker bridge nommé `selfstart-network` pour permettre la communication entre tous les services :

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│  Caddy Proxy    │───▶│ React Loader │───▶│ FastAPI Backend │
│ (Reverse Proxy) │    │ (Frontend)   │    │ (Docker SDK)    │
│ Port 80/443     │    │ Port 3000    │    │ Port 8000       │
└─────────────────┘    └──────────────┘    └─────────────────┘
         │                                           │
         ▼                      selfstart-network    ▼
┌─────────────────┐              ┌─────────────────┐ │
│ Container Apps  │◀─────────────┤  Dashboard      │ │
│ (sonarr, etc.)  │              │  Port 3001      │ │
└─────────────────┘              └─────────────────┘ │
                                                     │
                                 ┌─────────────────┐ │
                                 │ Docker Engine   │◀┘
                                 │ (via socket)    │
                                 └─────────────────┘
```

## 🔍 Diagnostic automatique

### Test rapide
```bash
# Test complet automatique
make network-test

# Ou directement
chmod +x network-test.sh && ./network-test.sh
```

### Tests manuels

#### 1. Vérifier le réseau Docker
```bash
# Lister les réseaux
docker network ls | grep selfstart

# Inspecter le réseau
docker network inspect selfstart-network

# Créer le réseau si manquant
make network-create
```

#### 2. Vérifier les containers
```bash
# État des containers
make status
# ou
docker-compose ps

# Santé des services
make check-health
```

#### 3. Tests de connectivité
```bash
# Accès externe
curl -f http://localhost:8000/health    # API
curl -f http://localhost:3000           # Frontend
curl -f http://localhost:3001           # Dashboard

# Communication interne
docker exec selfstart-frontend curl -f http://backend-api:8000/health
docker exec selfstart-caddy curl -f http://frontend-loader:3000
```

## 🔧 Résolution des problèmes courants

### ❌ Erreur: "network selfstart-network not found"

**Solution :**
```bash
# Créer le réseau
make network-create
# ou
docker network create selfstart-network

# Redémarrer les services
make restart
```

### ❌ Communication interne échoue

**Causes possibles :**
1. Containers sur des réseaux différents
2. Noms de containers incorrects
3. Ports internes mal configurés

**Solution :**
```bash
# Vérifier que tous les containers sont sur selfstart-network
docker network inspect selfstart-network

# Redémarrer avec recréation
docker-compose down
docker-compose up -d --force-recreate
```

### ❌ API non accessible depuis l'extérieur

**Vérifications :**
```bash
# Port binding
docker-compose ps
netstat -tlnp | grep :8000

# Logs de l'API
docker-compose logs backend-api
```

**Solution :**
```bash
# Redémarrer le backend
docker-compose restart backend-api

# Ou rebuild complet
make rebuild
```

### ❌ Frontend ne peut pas joindre l'API

**Vérifications :**
```bash
# Variable d'environnement
docker-compose exec frontend-loader env | grep VITE_API_URL

# Test depuis le container
docker exec selfstart-frontend curl http://backend-api:8000/health
```

**Solution :**
```bash
# Corriger dans docker-compose.yml
environment:
  - VITE_API_URL=http://backend-api:8000  # Nom interne correct

# Redémarrer
make restart
```

### ❌ Caddy ne route pas vers les bons services

**Vérifications :**
```bash
# Configuration Caddy
docker-compose exec caddy cat /etc/caddy/Caddyfile

# Logs Caddy
docker-compose logs caddy
```

**Solution :**
```bash
# Vérifier la configuration dans caddy/Caddyfile
# Redémarrer Caddy
docker-compose restart caddy
```

## 🛡️ Bonnes pratiques réseau

### Configuration recommandée

#### docker-compose.yml
```yaml
networks:
  selfstart-network:
    driver: bridge
    name: selfstart-network

services:
  backend-api:
    networks:
      - selfstart-network
    # ...
  
  frontend-loader:
    networks:
      - selfstart-network
    environment:
      - VITE_API_URL=http://backend-api:8000  # Nom du service
    # ...
```

#### Variables d'environnement
```bash
# .env
BASE_DOMAIN=localhost  # ou votre domaine
API_PORT=8000
FRONTEND_PORT=3000
DASHBOARD_PORT=3001
```

### Ports et services

| Service | Port externe | Port interne | Nom réseau |
|---------|-------------|-------------|------------|
| Backend API | 8000 | 8000 | `backend-api` |
| Frontend | 3000 | 3000 | `frontend-loader` |
| Dashboard | 3001 | 3000 | `frontend-dashboard` |
| Caddy | 80/443 | 80/443 | `caddy` |

## 📋 Commandes de diagnostic

### Commandes Makefile
```bash
make network-test      # Diagnostic complet
make network-create    # Créer le réseau
make check-health      # Vérifier la santé
make status           # État des services
make logs             # Logs en temps réel
make monitor          # Ressources système
```

### Commandes Docker directes
```bash
# Réseau
docker network ls
docker network inspect selfstart-network

# Containers
docker-compose ps
docker-compose logs service-name

# Communication
docker exec container-name curl http://target:port/path
```

## 🔄 Redémarrage en cas de problème

### Redémarrage léger
```bash
make restart
```

### Redémarrage avec reconstruction
```bash
make rebuild
```

### Redémarrage complet avec nettoyage
```bash
docker-compose down -v
docker network rm selfstart-network 2>/dev/null || true
make network-create
make start
```

## 🆘 Obtenir de l'aide

Si les problèmes persistent :

1. **Exécuter le diagnostic complet** : `make network-test`
2. **Collecter les logs** : `make logs > selfstart-logs.txt`
3. **Vérifier la configuration** : `make env-check`
4. **Créer une issue GitHub** avec :
   - Sortie de `make network-test`
   - Logs des services
   - Configuration système (OS, Docker version)

## 📚 Liens utiles

- [Documentation Docker Networks](https://docs.docker.com/network/)
- [Docker Compose Networking](https://docs.docker.com/compose/networking/)
- [Troubleshooting Docker](https://docs.docker.com/engine/troubleshooting/)

---

**💡 Conseil :** Gardez ce guide à portée de main et utilisez `make network-test` comme premier réflexe en cas de problème réseau !