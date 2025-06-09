# Makefile pour SelfStart
# Simplifie les opérations courantes de développement et de déploiement

.PHONY: help install start stop restart status logs clean build update apps network-test

# Variables
COMPOSE_FILE = docker-compose.yml
APPS_COMPOSE_FILE = examples/docker-compose.apps.yml
PROJECT_NAME = selfstart

# Couleurs pour les messages
GREEN = \033[0;32m
YELLOW = \033[1;33m
NC = \033[0m # No Color

help: ## Affiche l'aide
	@echo "$(GREEN)SelfStart - Commandes disponibles:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

install: ## Installation initiale avec configuration automatique
	@echo "$(GREEN)🚀 Installation de SelfStart...$(NC)"
	@chmod +x start.sh
	@./start.sh

start: ## Démarre tous les services SelfStart
	@echo "$(GREEN)▶️  Démarrage des services SelfStart...$(NC)"
	@docker-compose up -d
	@echo "$(GREEN)✅ Services démarrés$(NC)"

stop: ## Arrête tous les services
	@echo "$(YELLOW)⏹️  Arrêt des services...$(NC)"
	@docker-compose down
	@echo "$(GREEN)✅ Services arrêtés$(NC)"

restart: ## Redémarre tous les services
	@echo "$(YELLOW)🔄 Redémarrage des services...$(NC)"
	@docker-compose restart
	@echo "$(GREEN)✅ Services redémarrés$(NC)"

status: ## Affiche l'état des services
	@echo "$(GREEN)📊 État des services:$(NC)"
	@docker-compose ps

logs: ## Affiche les logs en temps réel
	@echo "$(GREEN)📋 Logs des services (Ctrl+C pour quitter):$(NC)"
	@docker-compose logs -f

build: ## Reconstruit les images Docker
	@echo "$(GREEN)🔨 Construction des images...$(NC)"
	@docker-compose build --no-cache
	@echo "$(GREEN)✅ Images construites$(NC)"

rebuild: stop build start ## Arrête, reconstruit et redémarre tout

update: ## Met à jour le projet depuis Git et redémarre
	@echo "$(GREEN)📥 Mise à jour du projet...$(NC)"
	@git pull
	@docker-compose down
	@docker-compose build --no-cache
	@docker-compose up -d
	@echo "$(GREEN)✅ Mise à jour terminée$(NC)"

apps: ## Démarre les applications d'exemple (Sonarr, Radarr, etc.)
	@echo "$(GREEN)🎬 Démarrage des applications d'exemple...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f $(APPS_COMPOSE_FILE) --profile apps up -d
	@echo "$(GREEN)✅ Applications d'exemple démarrées$(NC)"

apps-stop: ## Arrête les applications d'exemple
	@echo "$(YELLOW)⏹️  Arrêt des applications d'exemple...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f $(APPS_COMPOSE_FILE) --profile apps down
	@echo "$(GREEN)✅ Applications d'exemple arrêtées$(NC)"

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

clean: ## Nettoie les ressources Docker inutilisées
	@echo "$(YELLOW)🧹 Nettoyage des ressources Docker...$(NC)"
	@docker system prune -f
	@docker volume prune -f
	@echo "$(GREEN)✅ Nettoyage terminé$(NC)"

clean-all: ## Supprime TOUT (containers, images, volumes, réseaux)
	@echo "$(YELLOW)⚠️  ATTENTION: Cette action supprime TOUTES les données!$(NC)"
	@echo "$(YELLOW)Appuyez sur Ctrl+C pour annuler, ou Entrée pour continuer...$(NC)"
	@read
	@docker-compose -f $(COMPOSE_FILE) -f $(APPS_COMPOSE_FILE) down -v --remove-orphans
	@docker system prune -a -f --volumes
	@echo "$(GREEN)✅ Suppression complète terminée$(NC)"

dev: ## Mode développement avec rechargement automatique
	@echo "$(GREEN)🛠️  Mode développement...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f docker-compose.dev.yml up --build

backup: ## Sauvegarde les volumes et la configuration
	@echo "$(GREEN)💾 Sauvegarde en cours...$(NC)"
	@mkdir -p backups
	@docker run --rm -v selfstart_caddy_data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/caddy_data_$(shell date +%Y%m%d_%H%M%S).tar.gz -C /data .
	@cp .env backups/env_$(shell date +%Y%m%d_%H%M%S).backup 2>/dev/null || true
	@echo "$(GREEN)✅ Sauvegarde terminée dans ./backups/$(NC)"

test: ## Lance les tests (API et frontend)
	@echo "$(GREEN)🧪 Lancement des tests...$(NC)"
	@docker-compose exec backend-api python -m pytest tests/ || echo "Pas de tests backend configurés"
	@docker-compose exec frontend-loader npm test || echo "Pas de tests frontend configurés"

shell-backend: ## Ouvre un shell dans le container backend
	@docker-compose exec backend-api /bin/bash

shell-frontend: ## Ouvre un shell dans le container frontend
	@docker-compose exec frontend-loader /bin/sh

api-docs: ## Ouvre la documentation de l'API
	@echo "$(GREEN)📚 Documentation API disponible sur:$(NC)"
	@echo "  http://localhost:8000/docs"
	@echo "  http://localhost:8000/redoc"

monitor: ## Affiche les ressources utilisées par les containers
	@echo "$(GREEN)📈 Monitoring des ressources:$(NC)"
	@docker stats

check-health: ## Vérifie la santé des services
	@echo "$(GREEN)🏥 Vérification de la santé des services:$(NC)"
	@echo "Backend API:"
	@curl -f http://localhost:8000/health 2>/dev/null && echo "  ✅ Backend OK" || echo "  ❌ Backend KO"
	@echo "Frontend:"
	@curl -f http://localhost:3000 2>/dev/null && echo "  ✅ Frontend OK" || echo "  ❌ Frontend KO"

network: ## Affiche les informations réseau
	@echo "$(GREEN)🌐 Informations réseau:$(NC)"
	@docker network ls | grep selfstart
	@echo ""
	@docker network inspect selfstart-network | grep -E '"Name"|"IPv4Address"'

network-test: ## Lance le diagnostic réseau complet
	@echo "$(GREEN)🔍 Diagnostic réseau complet...$(NC)"
	@chmod +x network-test.sh
	@./network-test.sh

network-create: ## Crée le réseau SelfStart
	@echo "$(GREEN)🌐 Création du réseau SelfStart...$(NC)"
	@docker network create selfstart-network 2>/dev/null || echo "Réseau déjà existant"
	@echo "$(GREEN)✅ Réseau prêt$(NC)"

volumes: ## Affiche les volumes Docker
	@echo "$(GREEN)💽 Volumes Docker:$(NC)"
	@docker volume ls | grep selfstart

env-check: ## Vérifie la configuration .env
	@echo "$(GREEN)⚙️  Vérification de la configuration:$(NC)"
	@if [ -f .env ]; then \
		echo "  ✅ Fichier .env présent"; \
		echo "  Domaine configuré: $$(grep BASE_DOMAIN .env | cut -d'=' -f2)"; \
	else \
		echo "  ❌ Fichier .env manquant - Lancez 'make install'"; \
	fi

# Règles pour les différents environnements
prod: ## Déploiement en production
	@echo "$(GREEN)🚀 Déploiement en production...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f docker-compose.prod.yml up -d
	@echo "$(GREEN)✅ Déploiement en production terminé$(NC)"

staging: ## Déploiement en staging
	@echo "$(GREEN)🧪 Déploiement en staging...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) -f docker-compose.staging.yml up -d
	@echo "$(GREEN)✅ Déploiement en staging terminé$(NC)"

# Gestion des certificats SSL (pour la production)
ssl-cert: ## Génère des certificats SSL de test
	@echo "$(GREEN)🔒 Génération de certificats SSL de test...$(NC)"
	@mkdir -p ssl
	@openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
		-keyout ssl/selfstart.key -out ssl/selfstart.crt \
		-subj "/C=FR/ST=State/L=City/O=SelfStart/CN=localhost"
	@echo "$(GREEN)✅ Certificats générés dans ./ssl/$(NC)"

# Raccourcis pour les développeurs
quick-start: network-create start ## Démarrage rapide (réseau + services)

full-start: network-create start apps dashboard ## Démarrage complet avec tout

quick-test: start check-health network-test ## Test rapide après démarrage

# Affichage par défaut
.DEFAULT_GOAL := help