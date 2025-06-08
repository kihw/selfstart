---
name: 🐛 Bug Report
about: Signaler un bug dans SelfStart
title: '[BUG] '
labels: ['bug', 'triage']
assignees: []
---

## 🐛 Description du Bug

Une description claire et concise du bug.

## 🔄 Étapes pour Reproduire

1. Aller à '...'
2. Cliquer sur '...'
3. Faire défiler jusqu'à '...'
4. Voir l'erreur

## ✅ Comportement Attendu

Une description claire et concise de ce que vous attendiez.

## ❌ Comportement Actuel

Une description claire et concise de ce qui se passe actuellement.

## 📱 Environnement

**Desktop (merci de compléter les informations suivantes):**
- OS: [ex: Ubuntu 20.04, Windows 10, macOS Big Sur]
- Navigateur: [ex: Chrome 91, Firefox 89, Safari 14]
- Version Docker: [ex: 20.10.7]
- Version Docker Compose: [ex: 1.29.2]

**Smartphone (si applicable):**
- Device: [ex: iPhone 12, Samsung Galaxy S21]
- OS: [ex: iOS 14.6, Android 11]
- Navigateur: [ex: Safari, Chrome Mobile]

**Configuration SelfStart:**
- Version SelfStart: [ex: v2.0.0, commit hash, etc.]
- Domaine utilisé: [ex: localhost, exemple.com]
- Applications déployées: [ex: Sonarr, Radarr, Jellyfin]

## 📋 Logs

**Logs Backend API:**
```
Collez ici les logs de docker-compose logs backend-api
```

**Logs Frontend:**
```
Collez ici les logs de docker-compose logs frontend-loader
```

**Logs Caddy:**
```
Collez ici les logs de docker-compose logs caddy
```

**Logs du Container Problématique (si applicable):**
```
Collez ici les logs du container qui pose problème
```

## 📸 Captures d'Écran

Si applicable, ajoutez des captures d'écran pour expliquer votre problème.

## 📝 Configuration

**Fichier .env (masquez les informations sensibles):**
```env
BASE_DOMAIN=...
API_PORT=...
# etc.
```

**Docker Compose utilisé:**
- [ ] docker-compose.yml seul
- [ ] docker-compose.yml + examples/docker-compose.apps.yml
- [ ] Configuration personnalisée

## 🔧 Tentatives de Résolution

Décrivez ce que vous avez déjà essayé pour résoudre le problème:
- [ ] Redémarrage des services (`make restart`)
- [ ] Vérification des logs (`make logs`)
- [ ] Nettoyage Docker (`make clean`)
- [ ] Mise à jour (`make update`)
- [ ] Autre: ___________

## 📚 Contexte Supplémentaire

Ajoutez toute autre information sur le problème ici.

## ✅ Checklist

- [ ] J'ai vérifié que ce bug n'a pas déjà été signalé
- [ ] J'ai fourni toutes les informations demandées
- [ ] J'ai masqué les informations sensibles (mots de passe, clés, etc.)
- [ ] J'ai testé avec la dernière version de SelfStart
