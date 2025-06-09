# 🔧 Correctifs de Communication Réseau Docker

## 📋 Résumé des problèmes identifiés et corrigés

Cette branche corrige plusieurs problèmes de configuration réseau qui pouvaient empêcher la communication entre les containers Docker de SelfStart.

## 🔍 Problèmes identifiés

### 1. **Configuration réseau incohérente**
- Le fichier original `docker-compose.yml` utilisait `caddy_net` au lieu du réseau standardisé `selfstart-network`
- Manque de définition explicite du réseau avec un nom fixe
- Configuration réseau externe incorrecte

### 2. **Healthchecks manquants ou incorrects**
- Pas de healthchecks dans les Dockerfiles
- Timeouts trop courts pour les containers lents à démarrer
- Manque de `curl` dans les images pour les healthchecks

### 3. **Configuration Caddy problématique**
- Matchers utilisant `jq` qui n'est pas toujours disponible
- Configuration des headers manquante pour certains services
- Pas de gestion des erreurs appropriée

### 4. **Sécurité des containers**
- Containers s'exécutant en tant que root
- Pas d'utilisateurs dédiés dans les Dockerfiles

## ✅ Corrections apportées

### 1. **docker-compose.yml**
```yaml
# Avant
networks:
  caddy_net:
    external: true

# Après  
networks:
  selfstart-network:
    driver: bridge
    name: selfstart-network
```

**Améliorations :**
- Réseau unifié `selfstart-network` pour tous les services
- Définition explicite du driver et du nom
- Healthchecks ajoutés pour tous les services
- Timeouts augmentés pour les containers lents

### 2. **Dockerfiles backend et frontend**
```dockerfile
# Nouvelles fonctionnalités ajoutées :
RUN apt-get update && apt-get install -y curl  # Backend
RUN apk add --no-cache curl                    # Frontend

# Utilisateurs non-root
RUN useradd --create-home app && chown -R app:app /app
USER app

# Healthchecks intégrés
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

### 3. **Configuration Caddy**
```caddyfile
# Avant (problématique)
@running `curl -sf http://backend-api:8000/api/status?name=sonarr | jq -r '.status' | grep -q running`

# Après (compatible)
@running `curl -sf http://backend-api:8000/api/status?name=sonarr | grep -o '"status":"running"'`
```

**Améliorations :**
- Suppression de la dépendance à `jq`
- Headers HTTP complets pour tous les services
- Route API directe ajoutée pour le développement
- Gestion d'erreurs globale améliorée

### 4. **Sécurité renforcée**
```dockerfile
# Backend
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Frontend  
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
RUN chown -R nextjs:nodejs /app
USER nextjs
```

## 🛠️ Nouveaux outils de diagnostic

### 1. **Script de test réseau automatique**
```bash
# Utilisation
chmod +x network-test.sh
./network-test.sh

# Ou via Makefile
make network-test
```

**Fonctionnalités :**
- Vérification automatique de Docker et du réseau
- Tests de connectivité externe et interne
- Diagnostic des endpoints API
- Logs automatiques en cas d'erreur
- Résumé avec URLs d'accès et commandes utiles

### 2. **Commandes Makefile étendues**
```bash
make network-test      # Diagnostic complet
make network-create    # Créer le réseau
make check-health      # Vérifier la santé des services
make quick-start       # Démarrage rapide avec réseau
make full-start        # Démarrage complet (services + apps + dashboard)
make quick-test        # Test rapide après démarrage
```

### 3. **Documentation de troubleshooting**
- Guide complet `NETWORK_TROUBLESHOOTING.md`
- Diagnostic étape par étape
- Solutions aux problèmes courants
- Architecture réseau détaillée

## 🔬 Tests validés

### 1. **Communication interne**
```bash
✅ frontend-loader -> backend-api:8000/health
✅ caddy -> backend-api:8000/health  
✅ caddy -> frontend-loader:3000
✅ dashboard -> backend-api:8000/health
```

### 2. **Accès externe**
```bash
✅ localhost:8000 -> API backend
✅ localhost:3000 -> Frontend loader
✅ localhost:3001 -> Dashboard (si activé)
```

### 3. **Endpoints API**
```bash
✅ /health
✅ /api/containers
✅ /api/status?name=container
✅ /docs (documentation)
```

## 🚀 Instructions de déploiement

### 1. **Récupérer les corrections**
```bash
git checkout fix/docker-network-communication
git pull origin fix/docker-network-communication
```

### 2. **Nettoyer l'environnement existant**
```bash
# Arrêter et nettoyer
docker-compose down -v
docker network rm selfstart-network 2>/dev/null || true
docker system prune -f
```

### 3. **Déployer avec les corrections**
```bash
# Méthode 1: Démarrage rapide
make quick-start

# Méthode 2: Démarrage complet avec diagnostic
make full-start
make network-test

# Méthode 3: Manuel
make network-create
make build
make start
```

### 4. **Vérification**
```bash
# Test automatique complet
make network-test

# Tests manuels
curl http://localhost:8000/health
curl http://localhost:3000
docker exec selfstart-frontend curl http://backend-api:8000/health
```

## 📊 Résultats attendus

Après application des corrections :

✅ **Communication réseau stable** entre tous les services  
✅ **Healthchecks fonctionnels** avec détection des pannes  
✅ **Sécurité renforcée** avec utilisateurs non-root  
✅ **Configuration Caddy robuste** sans dépendances externes  
✅ **Outils de diagnostic complets** pour le troubleshooting  
✅ **Documentation claire** pour résoudre les problèmes  

## 🔧 Commandes de maintenance

### Redémarrage en cas de problème
```bash
# Redémarrage léger
make restart

# Redémarrage avec reconstruction  
make rebuild

# Redémarrage complet avec nettoyage
docker-compose down -v
make network-create
make start
```

### Diagnostic permanent
```bash
# Monitoring continu
make monitor

# Logs en temps réel
make logs

# État des services
make status
```

## 🚨 Points d'attention

1. **Première installation** : Toujours exécuter `make network-create` avant le premier démarrage
2. **Après mise à jour** : Relancer `make network-test` pour vérifier la communication
3. **En production** : Configurer des mots de passe sécurisés dans `.env`
4. **Monitoring** : Utiliser `make check-health` régulièrement

## 📋 Checklist de validation

- [ ] Le réseau `selfstart-network` existe
- [ ] Tous les containers sont sur le même réseau
- [ ] L'API backend répond sur `/health`
- [ ] Le frontend peut joindre l'API en interne
- [ ] Caddy route correctement vers les services
- [ ] Les healthchecks Docker fonctionnent
- [ ] Les logs ne montrent pas d'erreurs réseau

---

**🎯 Objectif atteint :** Communication réseau Docker fiable et debuggable pour SelfStart

**📅 Version :** fix/docker-network-communication  
**🔧 Statut :** Prêt pour merge vers main