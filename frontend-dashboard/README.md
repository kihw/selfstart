# 📊 SelfStart Dashboard

Interface d'administration complète pour SelfStart avec monitoring temps réel, gestion des containers, automation et webhooks.

## ✨ Fonctionnalités

### 🏠 **Vue d'ensemble**
- **Métriques système** temps réel (CPU, mémoire, réseau)
- **Status des containers** avec actions rapides
- **Événements récents** avec horodatage
- **Cartes de métriques** interactives avec tendances

### 🐳 **Gestion des Containers**
- **Table complète** avec recherche et filtres
- **Actions en lot** : start, stop, restart
- **Modal détaillé** pour chaque container
- **Métriques individuelles** en temps réel

### 📈 **Monitoring Système**
- **Graphiques temps réel** pour les ressources
- **Trafic réseau** entrant/sortant
- **Logs système** intégrés
- **Barres de progression** animées

### ⚡ **Automation**
- **Règles d'auto-shutdown** configurables
- **Conditions multiples** : inactivité, ressources, planning
- **Gestion par container** ou globale

### 🔔 **Webhooks**
- **Support multi-providers** : Discord, Slack, Teams
- **Configuration par événement**
- **Test des webhooks** intégré

### ⚙️ **Paramètres**
- **Configuration système** centralisée
- **Sécurité** et authentification
- **Actions système** : backup, restart

## 🚀 Installation

### 1. Structure du projet

```
selfstart/
├── frontend-dashboard/          # Dashboard React
│   ├── src/
│   │   ├── components/         # Composants modulaires
│   │   ├── hooks/             # Hooks personnalisés
│   │   └── Dashboard.jsx      # Composant principal
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml         # Configuration principale
└── caddy/Caddyfile           # Configuration proxy
```

### 2. Ajouter au docker-compose.yml

```yaml
services:
  # ... services existants ...

  # Dashboard d'administration
  frontend-dashboard:
    build: ./frontend-dashboard
    container_name: selfstart-dashboard
    restart: unless-stopped
    ports:
      - "3001:3000"
    environment:
      - VITE_API_URL=http://backend-api:8000
      - VITE_POLLING_INTERVAL=${POLLING_INTERVAL:-2000}
    networks:
      - selfstart-network
    depends_on:
      - backend-api
```

### 3. Configuration Caddy

Ajouter dans `caddy/Caddyfile` :

```caddyfile
# Interface d'administration
admin.{$BASE_DOMAIN} {
    reverse_proxy frontend-dashboard:3000
    
    # Authentification basique (optionnelle)
    basicauth {
        admin $2a$14$Zkx19XLiW6VYouLHR5NmfOFU0z2GTNOWNvhHn.b6jCa7Jb.0Kfxh2
    }
}
```

### 4. Démarrage

```bash
# Construire et démarrer
docker-compose up -d --build

# Ou avec le Makefile
make build && make start
```

## 🔗 Accès

- **Local** : http://localhost:3001
- **Production** : https://admin.votre-domaine.com

## 🎨 Interface

### Design System
- **Framework** : React 18 + Vite
- **Styling** : TailwindCSS
- **Icônes** : Lucide React
- **Couleurs** : Palette moderne avec support dark/light
- **Animations** : Transitions fluides CSS

### Composants Modulaires
```
src/components/
├── Navigation.jsx         # Navigation principale
├── Overview.jsx          # Vue d'ensemble
├── Containers.jsx        # Gestion containers
├── Monitoring.jsx        # Monitoring système
├── Automation.jsx        # Règles automation
├── Webhooks.jsx          # Configuration webhooks
├── SettingsTab.jsx       # Paramètres
├── ContainerModal.jsx    # Modal détails
└── UIComponents.jsx      # Composants réutilisables
```

## 🔌 API Integration

### Endpoints requis

Le dashboard s'attend à ces endpoints de l'API backend :

```javascript
// Endpoints existants
GET  /health                    // Santé API
GET  /api/status?name={name}    // Status container
POST /api/start?name={name}     // Démarrer container
POST /api/stop?name={name}      // Arrêter container
GET  /api/containers            // Liste containers
GET  /api/logs/{name}           // Logs container

// Nouveaux endpoints à ajouter
GET  /api/system/metrics        // Métriques système
GET  /api/automation/rules      // Règles automation
POST /api/automation/rules      // Créer règle
GET  /api/webhooks              // Configuration webhooks
POST /api/webhooks              // Créer webhook
GET  /api/settings              // Paramètres système
```

### Exemple d'extension API

```python
# backend-api/main.py

@app.get("/api/system/metrics")
async def get_system_metrics():
    return {
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "network_in": get_network_bytes_in(),
        "network_out": get_network_bytes_out()
    }

@app.get("/api/automation/rules")
async def get_automation_rules():
    # Utiliser le AutoShutdownManager
    return await shutdown_manager.get_rules()
```

## 🔄 Données Temps Réel

### Polling Intelligent
- **Métriques système** : Mise à jour toutes les 3 secondes
- **Status containers** : Polling configurable (défaut: 2s)
- **Événements** : Push via WebSocket (futur)

### Simulation de données
Le dashboard inclut un hook `useSimulatedData` pour démonstration :

```javascript
// Remplacer par des vraies API calls
const { data } = useSimulatedData();

// Par des appels API réels
const { data } = useApiData(API_BASE_URL);
```

## 🛡️ Sécurité

### Authentification
- **Authentification basique** Caddy intégrée
- **Variables d'environnement** sécurisées
- **Headers de sécurité** automatiques

### Configuration production
```env
# .env
ENABLE_BASIC_AUTH=true
ADMIN_USERNAME=admin
ADMIN_PASSWORD=votre_mot_de_passe_fort
```

## 📱 Responsive Design

- **Mobile-first** : Interface adaptée mobile
- **Tablette** : Optimisé pour tablettes
- **Desktop** : Interface complète
- **Accessibilité** : Standards WCAG

## 🎯 Extensibilité

### Ajouter un nouvel onglet

1. **Créer le composant** :
```javascript
// src/components/MonNouvelOnglet.jsx
const MonNouvelOnglet = () => (
  <div>Contenu de mon onglet</div>
);
export default MonNouvelOnglet;
```

2. **Ajouter à la navigation** :
```javascript
// src/components/Navigation.jsx
const tabs = [
  // ... onglets existants
  { id: 'mon-onglet', label: 'Mon Onglet', icon: MonIcon }
];
```

3. **Intégrer au Dashboard** :
```javascript
// src/Dashboard.jsx
import MonNouvelOnglet from './components/MonNouvelOnglet';

const renderActiveTab = () => {
  switch (activeTab) {
    // ... cas existants
    case 'mon-onglet':
      return <MonNouvelOnglet />;
  }
};
```

## 🚧 Roadmap

### v2.1 (Prochaine version)
- [ ] **WebSocket** pour mises à jour temps réel
- [ ] **Graphiques avancés** avec Recharts
- [ ] **Thème sombre** complet
- [ ] **Notifications** toast en temps réel
- [ ] **Export** des données et configurations

### v2.2 (Futur)
- [ ] **Multi-utilisateurs** avec rôles
- [ ] **API GraphQL** pour optimiser les requêtes
- [ ] **PWA** pour installation mobile
- [ ] **Plugins** système extensible

## 📝 Développement

### Prérequis
- Node.js 18+
- Docker & Docker Compose
- Accès à l'API SelfStart

### Scripts disponibles
```bash
npm run dev      # Développement
npm run build    # Production build
npm run preview  # Preview du build
npm run lint     # Linting
```

### Structure recommandée
```
src/
├── components/     # Composants UI
├── hooks/         # Logique métier
├── utils/         # Fonctions utilitaires
├── api/          # Clients API
└── styles/       # Styles globaux
```

## 🤝 Contribution

1. **Fork** le repository
2. **Créer** une branche feature
3. **Développer** dans `frontend-dashboard/`
4. **Tester** localement
5. **Soumettre** une PR

---

**Développé avec ❤️ pour la communauté SelfStart**

*Dashboard v2.0 - Interface d'administration moderne* 🚀
