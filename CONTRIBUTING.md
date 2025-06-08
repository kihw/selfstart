# 🤝 Guide de Contribution - SelfStart

Merci de votre intérêt pour contribuer à SelfStart ! Ce guide vous aidera à démarrer et à comprendre comment contribuer efficacement au projet.

## 📋 Table des Matières

- [🚀 Démarrage Rapide](#-démarrage-rapide)
- [🎯 Types de Contributions](#-types-de-contributions)
- [🛠️ Configuration de l'Environnement](#️-configuration-de-lenvironnement)
- [📝 Standards de Code](#-standards-de-code)
- [🔄 Processus de Contribution](#-processus-de-contribution)
- [🧪 Tests](#-tests)
- [📚 Documentation](#-documentation)
- [🐛 Signaler des Bugs](#-signaler-des-bugs)
- [✨ Proposer des Fonctionnalités](#-proposer-des-fonctionnalités)
- [👥 Communauté](#-communauté)

## 🚀 Démarrage Rapide

1. **🍴 Fork** le repository
2. **📥 Clone** votre fork
3. **🔧 Configurez** l'environnement de développement
4. **🌿 Créez** une branche pour votre contribution
5. **💻 Développez** votre fonctionnalité ou correction
6. **🧪 Testez** vos changements
7. **📤 Soumettez** une Pull Request

```bash
# 1. Fork sur GitHub puis cloner
git clone https://github.com/VOTRE_USERNAME/selfstart.git
cd selfstart

# 2. Ajouter le remote upstream
git remote add upstream https://github.com/kihw/selfstart.git

# 3. Configuration initiale
make install

# 4. Créer une branche
git checkout -b feature/ma-super-fonctionnalite

# 5. Après vos changements
git add .
git commit -m "✨ Add amazing feature"
git push origin feature/ma-super-fonctionnalite

# 6. Créer une PR sur GitHub
```

## 🎯 Types de Contributions

Nous accueillons tous les types de contributions :

### 🐛 Corrections de Bugs
- Signaler des bugs via les [Issues](https://github.com/kihw/selfstart/issues)
- Corriger des bugs existants
- Améliorer la gestion d'erreurs

### ✨ Nouvelles Fonctionnalités
- Proposer de nouvelles fonctionnalités
- Implémenter des fonctionnalités demandées
- Améliorer l'expérience utilisateur

### 📚 Documentation
- Corriger des erreurs dans la documentation
- Ajouter des exemples d'utilisation
- Traduire la documentation
- Améliorer les commentaires de code

### 🎨 Interface Utilisateur
- Améliorer le design
- Corriger des problèmes d'accessibilité
- Optimiser les performances frontend
- Ajouter des animations

### 🔧 Infrastructure
- Optimiser les Dockerfiles
- Améliorer la configuration Caddy
- Optimiser les performances
- Améliorer la sécurité

### 🧪 Tests
- Ajouter des tests unitaires
- Créer des tests d'intégration
- Améliorer la couverture de code
- Automatiser les tests

## 🛠️ Configuration de l'Environnement

### 🔧 Prérequis

- **Docker** 20.10+ et **Docker Compose**
- **Git** pour le versioning
- **Node.js** 18+ (pour le développement frontend)
- **Python** 3.11+ (pour le développement backend)

### 📋 Installation

```bash
# 1. Cloner le repository
git clone https://github.com/kihw/selfstart.git
cd selfstart

# 2. Installation automatique
chmod +x start.sh
./start.sh

# Ou avec Make
make install
```

### 🔄 Développement

```bash
# Démarrer en mode développement
make dev

# Voir les logs en temps réel
make logs

# Redémarrer après modifications
make restart

# Tests
make test
```

### 📁 Structure de Développement

```
selfstart/
├── 🔧 backend-api/         # API FastAPI
│   ├── main.py            # Point d'entrée API
│   ├── docker_manager.py  # Gestion Docker
│   ├── requirements.txt   # Dépendances Python
│   └── tests/             # Tests backend
├── 🎨 frontend-loader/     # Interface React
│   ├── src/               # Code source React
│   ├── package.json       # Dépendances Node.js
│   └── tests/             # Tests frontend
├── 🌐 caddy/              # Configuration proxy
├── 📁 examples/           # Applications d'exemple
└── 🧪 tests/             # Tests d'intégration
```

## 📝 Standards de Code

### 🐍 Backend (Python)

```bash
# Style de code
black backend-api/
flake8 backend-api/ --max-line-length=88

# Tests
pytest backend-api/tests/

# Type checking (optionnel)
mypy backend-api/
```

**Conventions:**
- Utiliser **Black** pour le formatage
- **PEP 8** pour le style
- **Type hints** pour les nouvelles fonctions
- **Docstrings** pour les fonctions publiques

### ⚛️ Frontend (React/JavaScript)

```bash
# Style de code
npm run lint
npm run format

# Tests
npm test

# Build
npm run build
```

**Conventions:**
- **ESLint + Prettier** pour le formatage
- **Composants fonctionnels** avec hooks
- **Props destructuring**
- **Noms explicites** pour les variables/fonctions

### 🐳 Docker

**Bonnes pratiques:**
- Images multi-stage pour optimiser la taille
- `.dockerignore` approprié
- Variables d'environnement documentées
- Health checks inclus
- Utilisateur non-root quand possible

### 📝 Commits

Nous utilisons les **Conventional Commits** :

```bash
# Format
<type>(<scope>): <description>

# Exemples
feat(backend): add container auto-restart feature
fix(frontend): resolve loading animation glitch  
docs(readme): update installation instructions
style(frontend): improve button hover effects
refactor(api): simplify container management logic
test(backend): add unit tests for docker manager
ci(github): update workflow dependencies
```

**Types de commits:**
- `feat`: Nouvelle fonctionnalité
- `fix`: Correction de bug
- `docs`: Documentation
- `style`: Formatage/style (pas de changement logique)
- `refactor`: Refactoring sans changement fonctionnel
- `test`: Ajout/modification de tests
- `ci`: CI/CD
- `chore`: Maintenance

## 🔄 Processus de Contribution

### 1. 🍴 Préparation

```bash
# Fork et clone
git clone https://github.com/VOTRE_USERNAME/selfstart.git
cd selfstart

# Configurer upstream
git remote add upstream https://github.com/kihw/selfstart.git

# Synchroniser avec upstream
git fetch upstream
git checkout main
git merge upstream/main
```

### 2. 🌿 Développement

```bash
# Créer une branche
git checkout -b feature/ma-fonctionnalite

# Développer et tester
make dev
# ... développement ...
make test

# Commits fréquents
git add .
git commit -m "feat: add new feature"
```

### 3. 📤 Soumission

```bash
# Push vers votre fork
git push origin feature/ma-fonctionnalite

# Créer une PR sur GitHub
# Utiliser le template de PR
```

### 4. 🔍 Review

- **Patience** : Les reviews prennent du temps
- **Réactivité** : Répondez aux commentaires rapidement
- **Ouverture** : Acceptez les suggestions constructives
- **Tests** : Assurez-vous que les tests CI passent

### 5. 🎉 Merge

Une fois approuvée, votre PR sera mergée ! 🎉

## 🧪 Tests

### 🔧 Tests Backend

```bash
# Tests unitaires
cd backend-api
pytest tests/ -v

# Coverage
pytest tests/ --cov=. --cov-report=html

# Tests spécifiques
pytest tests/test_docker_manager.py
```

### ⚛️ Tests Frontend

```bash
# Tests React
cd frontend-loader
npm test

# Tests e2e (si configurés)
npm run test:e2e

# Coverage
npm test -- --coverage
```

### 🐳 Tests d'Intégration

```bash
# Tests complets avec Docker
make test

# Tests manuels
make start
curl http://localhost:8000/health
curl http://localhost:3000
```

### ✅ Checklist de Tests

Avant de soumettre une PR :

- [ ] **Tests unitaires** passent
- [ ] **Tests d'intégration** passent
- [ ] **Nouveaux tests** ajoutés pour les nouvelles fonctionnalités
- [ ] **Coverage** maintenu ou amélioré
- [ ] **Tests manuels** effectués

## 📚 Documentation

### 📖 Types de Documentation

1. **Code** : Commentaires et docstrings
2. **API** : Documentation FastAPI automatique
3. **Utilisateur** : README, guides, tutoriels
4. **Développeur** : Ce guide de contribution

### ✍️ Standards Documentation

- **Langage** : Français pour la documentation utilisateur
- **Format** : Markdown avec émojis
- **Structure** : Headers hiérarchiques
- **Exemples** : Code samples fonctionnels
- **Liens** : Références croisées

### 📝 Mise à Jour

Quand mettre à jour la documentation :

- [ ] Nouvelle fonctionnalité → Mettre à jour README
- [ ] Changement d'API → Mettre à jour docstrings
- [ ] Nouveau processus → Mettre à jour guides
- [ ] Correction de bug → Vérifier la documentation

## 🐛 Signaler des Bugs

### 📋 Avant de Signaler

1. **Vérifiez** les [issues existantes](https://github.com/kihw/selfstart/issues)
2. **Testez** avec la dernière version
3. **Reproduisez** le bug de manière cohérente
4. **Collectez** les informations nécessaires

### 🔍 Informations Requises

- **Environnement** : OS, Docker version, navigateur
- **Étapes** : Comment reproduire le bug
- **Logs** : Logs pertinents (masquez les infos sensibles)
- **Configuration** : Fichier .env (sans secrets)
- **Captures** : Screenshots si applicable

### 📝 Template de Bug

Utilisez le [template de bug report](.github/ISSUE_TEMPLATE/bug_report.md) pour garantir que toutes les informations nécessaires sont fournies.

## ✨ Proposer des Fonctionnalités

### 💡 Avant de Proposer

1. **Vérifiez** la [roadmap](CHANGELOG.md#roadmap)
2. **Cherchez** dans les [issues existantes](https://github.com/kihw/selfstart/issues)
3. **Discutez** dans les [Discussions](https://github.com/kihw/selfstart/discussions)
4. **Évaluez** l'alignement avec les objectifs du projet

### 📋 Processus de Proposition

1. **Ouvrir** une [feature request](.github/ISSUE_TEMPLATE/feature_request.md)
2. **Décrire** le problème à résoudre
3. **Proposer** une solution détaillée
4. **Discuter** avec la communauté
5. **Implémenter** (vous ou quelqu'un d'autre)

### 🎯 Critères d'Acceptation

- ✅ **Aligné** avec les objectifs du projet
- ✅ **Utile** pour la majorité des utilisateurs
- ✅ **Faisable** techniquement
- ✅ **Maintenable** à long terme
- ✅ **Documenté** et testé

## 👥 Communauté

### 💬 Canaux de Communication

- **Issues** : Bugs et fonctionnalités
- **Discussions** : Questions et idées
- **Pull Requests** : Code reviews
- **Email** : Contact direct (voir profil)

### 🤝 Code de Conduite

Nous attendons de tous les contributeurs qu'ils :

- **Respectent** tous les participants
- **Soient constructifs** dans leurs critiques
- **Aident** les nouveaux contributeurs
- **Restent concentrés** sur les objectifs du projet
- **Communiquent** de manière professionnelle

### 🏆 Reconnaissance

Tous les contributeurs sont reconnus :

- **README** : Section contributeurs
- **CHANGELOG** : Mentions dans les releases
- **GitHub** : Profil de contributeur
- **Communauté** : Remerciements publics

## 🚀 Ressources Utiles

### 📚 Documentation Technique

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Docker Documentation](https://docs.docker.com/)
- [Caddy Documentation](https://caddyserver.com/docs/)

### 🛠️ Outils Recommandés

- **IDE** : VS Code avec extensions
- **Git GUI** : GitHub Desktop, SourceTree
- **API Testing** : Postman, Insomnia
- **Docker GUI** : Docker Desktop, Portainer

### 📖 Guides Externes

- [How to Contribute to Open Source](https://opensource.guide/how-to-contribute/)
- [First Contributions](https://github.com/firstcontributions/first-contributions)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

## 🎉 Merci !

Votre contribution rend SelfStart meilleur pour tous ! 

**Questions ?** N'hésitez pas à :
- Ouvrir une [Discussion](https://github.com/kihw/selfstart/discussions)
- Créer une [Issue](https://github.com/kihw/selfstart/issues)
- Contacter les maintainers

**Happy coding!** 🚀

---

*Ce guide est vivant et évolue avec le projet. N'hésitez pas à proposer des améliorations !*
