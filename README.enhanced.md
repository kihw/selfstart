# SelfStart Enhanced 🚀⚡

**Système avancé de démarrage dynamique avec orchestration intelligente et load balancing**

SelfStart Enhanced apporte une architecture de niveau production avec orchestration de containers, load balancing intelligent, et monitoring avancé.

## ✨ Nouvelles Fonctionnalités Enhanced

### 🎭 Orchestration Intelligente
- **Gestion des dépendances** : Démarrage automatique des services requis
- **Health monitoring** : Surveillance continue de la santé des containers
- **Restart policies** : Redémarrage intelligent en cas de panne
- **Resource management** : Gestion des limites et quotas

### ⚖️ Load Balancing Avancé
- **Multiple algorithms** : Round-robin, least-connections, weighted, IP-hash
- **Health checks** : Vérification automatique des backends
- **Circuit breakers** : Protection contre les cascades de pannes
- **Sticky sessions** : Support des sessions persistantes

### 📊 Monitoring & Observabilité
- **Métriques Prometheus** : Export natif des métriques
- **Dashboards Grafana** : Visualisation temps réel
- **Distributed tracing** : Suivi des requêtes cross-services
- **Alerting** : Notifications automatiques

### 🔄 High Availability
- **Multi-instance** : Déploiement de plusieurs instances
- **Failover automatique** : Basculement transparent
- **Zero-downtime deployments** : Mises à jour sans interruption
- **Backup & restore** : Sauvegarde automatique

## 🏗️ Architecture Enhanced

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   HAProxy LB    │───▶│  Caddy Enhanced  │───▶│  Container Apps     │
│ (Load Balancer) │    │ (Smart Proxy)    │    │ (Auto-orchestrated) │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│ Backend API x2  │◀───│ Frontend x2      │◀───│ Container           │
│ (Clustered)     │    │ (Load Balanced)  │    │ Orchestrator        │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│ Redis Cluster   │    │ Prometheus       │    │ Proxy Manager       │
│ (Coordination)  │    │ (Metrics)        │    │ (Load Balancing)    │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
```

## 🚀 Démarrage Enhanced

### ⚡ Installation Ultra-Rapide

```bash
# Clone et installation Enhanced
git clone https://github.com/kihw/selfstart.git
cd selfstart
make install-enhanced
```

### 🎯 Modes de Déploiement

```bash
# Mode standard Enhanced
make start-enhanced

# Mode High Availability
make start-ha

# Mode complet (HA + Monitoring + Dashboard + Apps)
make start-full

# Mode développement
make dev-enhanced
```

## 📊 Nouvelles API v2

### 🎭 Container Orchestration

```bash
# Créer un container avec dépendances
curl -X POST http://localhost:8000/api/v2/containers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "webapp",
    "image": "nginx:latest",
    "ports": {"80": 8080},
    "dependencies": ["database", "cache"],
    "startup_strategy": "dependency_based",
    "health_check": {
      "type": "http",
      "url": "http://localhost:8080/health",
      "timeout": 5
    }
  }'

# Démarrer avec orchestration
curl -X POST http://localhost:8000/api/v2/containers/webapp/start

# Statut détaillé
curl http://localhost:8000/api/v2/containers/webapp/status
```

### ⚖️ Proxy Management

```bash
# Créer un target de load balancing
curl -X POST http://localhost:8000/api/v2/proxy/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "webapp",
    "backends": [
      {"host": "webapp1", "port": 8080, "weight": 2},
      {"host": "webapp2", "port": 8080, "weight": 1}
    ],
    "rule": "weighted",
    "health_check_path": "/health"
  }'

# Ajouter un backend
curl -X POST http://localhost:8000/api/v2/proxy/targets/webapp/backends \
  -H "Content-Type: application/json" \
  -d '{"host": "webapp3", "port": 8080, "weight": 1}'

# Mettre en maintenance
curl -X POST "http://localhost:8000/api/v2/proxy/targets/webapp/backends/maintenance?backend_url=http://webapp1:8080&maintenance=true"
```

### 📊 Métriques Avancées

```bash
# Métriques complètes
curl http://localhost:8000/api/v2/metrics

# Métriques Prometheus
curl http://localhost:8000/metrics

# Statut orchestrateur
curl http://localhost:8000/api/v2/containers | jq '.metrics'

# Statut proxy
curl http://localhost:8000/api/v2/proxy/targets | jq '.metrics'
```

## 🛠️ Commandes Enhanced

### 🎭 Orchestration

```bash
# Créer un container
make create-container NAME=myapp IMAGE=nginx:latest

# Démarrer/arrêter
make start-container NAME=myapp
make stop-container NAME=myapp

# Logs et statut
make container-logs NAME=myapp
make orchestrator-status
```

### ⚖️ Load Balancing

```bash
# Gérer les targets
make create-proxy-target NAME=myapp HOST=localhost PORT=8080
make add-backend TARGET=myapp HOST=localhost PORT=8081
make remove-backend TARGET=myapp URL=http://localhost:8081

# Maintenance
make backend-maintenance TARGET=myapp URL=http://localhost:8081 MODE=true

# Tests
make test-load-balancing
```

### 📊 Monitoring

```bash
# Démarrer le monitoring
make start-monitoring

# Métriques
make metrics
make prometheus-metrics

# Health checks
make health-check-all

# Benchmark
make benchmark
```

## 🔧 Configuration Enhanced

### 🎭 Container Orchestration

```yaml
# Configuration d'un container avec orchestration
webapp:
  name: "webapp"
  image: "nginx:latest"
  ports:
    80: 8080
  dependencies:
    - "database"
    - "cache"
  startup_strategy: "dependency_based"
  health_check:
    type: "http"
    url: "http://localhost:8080/health"
    timeout: 5
    interval: 30
  resource_limits:
    memory: "512m"
    cpu: "0.5"
  restart_policy: "unless-stopped"
  startup_timeout: 120
```

### ⚖️ Proxy Configuration

```yaml
# Configuration d'un target de load balancing
webapp_target:
  name: "webapp"
  rule: "least_connections"
  backends:
    - host: "webapp1"
      port: 8080
      weight: 2
      max_connections: 100
    - host: "webapp2"
      port: 8080
      weight: 1
      max_connections: 50
  health_check_path: "/health"
  health_check_interval: 30
  circuit_breaker_threshold: 5
  sticky_sessions: true
```

### 📊 Monitoring Configuration

```yaml
# Prometheus scrape config
scrape_configs:
  - job_name: 'selfstart-enhanced'
    static_configs:
      - targets: ['backend-api-enhanced:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

## 🔄 High Availability

### 🎯 Multi-Instance Deployment

```bash
# Démarrer en mode HA
make start-ha

# Vérifier les instances
docker-compose -f docker-compose.enhanced.yml ps

# Load balancer stats
make haproxy-stats
```

### 🔄 Failover Testing

```bash
# Simuler une panne
docker-compose -f docker-compose.enhanced.yml stop backend-api-enhanced

# Vérifier le failover
curl http://localhost:8000/health

# Redémarrer l'instance
docker-compose -f docker-compose.enhanced.yml start backend-api-enhanced
```

## 📊 Dashboards & Monitoring

### 📈 Grafana Dashboards

- **SelfStart Overview** : Vue d'ensemble du système
- **Container Metrics** : Métriques des containers
- **Proxy Performance** : Performance du load balancing
- **System Health** : Santé globale du système

Accès : http://localhost:3002 (admin/admin)

### 🎯 Prometheus Metrics

- `selfstart_containers_total` : Nombre total de containers
- `selfstart_proxy_requests_total` : Requêtes proxy
- `selfstart_proxy_response_time` : Temps de réponse
- `selfstart_backend_health` : Santé des backends

Accès : http://localhost:9090

## 🧪 Tests & Validation

### 🔬 Tests de Performance

```bash
# Benchmark complet
make benchmark

# Test de charge spécifique
ab -n 10000 -c 100 http://localhost:8000/health

# Test du load balancing
make test-load-balancing
```

### 🧪 Tests de Résilience

```bash
# Test de failover
docker-compose -f docker-compose.enhanced.yml stop backend-api-enhanced
curl http://localhost:8000/health  # Doit fonctionner via l'instance 2

# Test de circuit breaker
# Arrêter tous les backends d'un target
# Vérifier que le circuit breaker s'ouvre
```

## 🔒 Sécurité Enhanced

### 🛡️ Nouvelles Mesures

- **Rate limiting** : Protection contre les attaques DDoS
- **Circuit breakers** : Protection des backends
- **Health checks** : Détection automatique des compromissions
- **Audit logging** : Traçabilité complète des actions

### 🔐 Configuration Sécurisée

```bash
# Activer l'authentification
ENABLE_BASIC_AUTH=true
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=$(caddy hash-password --plaintext "votre_mot_de_passe")

# Rate limiting
ENABLE_RATE_LIMITING=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

## 🚧 Roadmap Enhanced v2.0

### 🎯 Fonctionnalités Prévues

- [ ] 🤖 **Auto-scaling** : Scaling automatique basé sur la charge
- [ ] 🌍 **Multi-region** : Déploiement géographiquement distribué
- [ ] 🔐 **Service mesh** : Istio/Linkerd integration
- [ ] 📱 **Mobile app** : Application mobile de monitoring
- [ ] 🧠 **AI/ML** : Prédiction de charge et optimisation automatique

### 🔧 Améliorations Techniques

- [ ] ☸️ **Kubernetes** : Support natif Kubernetes
- [ ] 🔄 **GitOps** : Déploiement via Git
- [ ] 🧪 **Chaos engineering** : Tests de résilience automatisés
- [ ] 📊 **Advanced metrics** : Métriques business et SLI/SLO

## 📞 Support Enhanced

### 🆘 Obtenir de l'Aide

- 📖 **Documentation Enhanced** : README.enhanced.md
- 🐛 **Issues** : [GitHub Issues](https://github.com/kihw/selfstart/issues)
- 💬 **Discussions** : [GitHub Discussions](https://github.com/kihw/selfstart/discussions)
- 📧 **Support Enterprise** : contact@selfstart.dev

### 🎯 Monitoring & Alerting

```bash
# Vérifier la santé globale
make health-check-all

# Métriques en temps réel
watch -n 5 'curl -s http://localhost:8000/api/v2/metrics | jq ".orchestrator"'

# Logs centralisés
make logs-enhanced
```

---

<div align="center">

**Développé avec ❤️ pour la production**

[⭐ Star ce projet](https://github.com/kihw/selfstart) • [🐛 Reporter un bug](https://github.com/kihw/selfstart/issues) • [💬 Rejoindre la discussion](https://github.com/kihw/selfstart/discussions)

*SelfStart Enhanced v1.5 - Production-Ready Container Orchestration* 🚀⚡

</div>