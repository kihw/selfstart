#!/bin/bash

# Script de démarrage rapide pour SelfStart
# Ce script configure et démarre automatiquement SelfStart

set -e

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher des messages colorés
print_message() {
    echo -e "${GREEN}[SelfStart]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[SelfStart]${NC} $1"
}

print_error() {
    echo -e "${RED}[SelfStart]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[SelfStart]${NC} $1"
}

# Fonction pour détecter la commande Docker Compose disponible
detect_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    elif docker compose version &> /dev/null 2>&1; then
        echo "docker compose"
    else
        return 1
    fi
}

# Banner
echo -e "${BLUE}"
echo "  ____       _  __   ____  _             _   "
echo " / ___|  ___| |/ _| / ___|| |_ __ _ _ __| |_ "
echo " \___ \ / _ \ | |_  \___ \| __/ _\` | '__| __|"
echo "  ___) |  __/ |  _|  ___) | || (_| | |  | |_ "
echo " |____/ \___|_|_|   |____/ \__\__,_|_|   \__|"
echo -e "${NC}"
echo "Système de démarrage automatique de containers Docker"
echo "======================================================="
echo

# Vérification des prérequis
print_info "Vérification des prérequis..."

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker n'est pas installé. Veuillez installer Docker d'abord."
    exit 1
fi

# Vérifier Docker Compose et détecter la commande
if ! DOCKER_COMPOSE_CMD=$(detect_docker_compose); then
    print_error "Docker Compose n'est pas installé ou n'est pas accessible."
    print_info "Pour installer Docker Compose:"
    print_info "  - Ubuntu/Debian: sudo apt-get install docker-compose-plugin"
    print_info "  - RHEL/CentOS: sudo yum install docker-compose-plugin"
    print_info "  - Ou suivez la documentation officielle Docker"
    exit 1
fi

print_message "✓ Docker et Docker Compose sont disponibles (utilisation de: $DOCKER_COMPOSE_CMD)"

# Vérifier que Docker fonctionne
if ! docker ps &> /dev/null; then
    print_error "Docker n'est pas démarré ou vous n'avez pas les permissions nécessaires."
    print_info "Essayez: sudo systemctl start docker"
    print_info "Ou ajoutez votre utilisateur au groupe docker: sudo usermod -aG docker \$USER"
    exit 1
fi

print_message "✓ Docker fonctionne correctement"

# Configuration du fichier .env
if [ ! -f .env ]; then
    print_info "Création du fichier de configuration .env..."
    
    # Demander le domaine
    echo -n "Entrez votre domaine (ou localhost pour les tests): "
    read -r domain
    domain=${domain:-localhost}
    
    # Créer le fichier .env
    cp .env.example .env
    sed -i "s/BASE_DOMAIN=exemple.com/BASE_DOMAIN=$domain/" .env
    
    # Générer une clé secrète
    if command -v openssl &> /dev/null; then
        secret_key=$(openssl rand -hex 32)
        sed -i "s/SECRET_KEY=votre_cle_secrete_ici/SECRET_KEY=$secret_key/" .env
    fi
    
    print_message "✓ Fichier .env créé avec le domaine: $domain"
else
    print_message "✓ Fichier .env existant détecté"
fi

# Créer les répertoires nécessaires
print_info "Création des répertoires de données..."
mkdir -p downloads media/tv media/movies media/music config data
# Permissions plus restrictives pour data
mkdir -p data
chmod -R 755 data
print_message "✓ Répertoires créés"

# Créer le répertoire pour les logs Caddy
print_info "Création du répertoire pour les logs Caddy..."
mkdir -p ./logs/caddy
print_message "✓ Répertoire de logs créé"

# Créer le répertoire caddy et le Caddyfile si nécessaire
print_info "Configuration de Caddy..."
mkdir -p ./caddy
if [ ! -f ./caddy/Caddyfile ]; then
    # Créer un Caddyfile de base
    cat > ./caddy/Caddyfile << 'EOF'
# Configuration Caddy pour SelfStart
# Reverse proxy intelligent avec démarrage automatique de containers

# Configuration globale
{
    # Configuration automatique HTTPS
    email admin@{$BASE_DOMAIN}
    
    # Optimisations de performance
    servers {
        protocols h1 h2 h3
    }
}

# Route principale - Exemple avec Sonarr
sonarr.{$BASE_DOMAIN} {
    # Matcher pour vérifier si le container est en cours d'exécution
    @running `curl -sf http://backend-api:8000/api/status?name=sonarr | grep -o '"status":"running"'`
    
    # Si le container est en cours d'exécution, rediriger vers lui
    handle @running {
        reverse_proxy sonarr:8989 {
            # Headers pour préserver l'IP client
            header_up Host {host}
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-For {remote_host}
            header_up X-Forwarded-Proto {scheme}
            
            # Timeout augmenté pour les applications lentes
            timeout 30s
        }
    }
    
    # Sinon, afficher l'interface de chargement
    handle {
        reverse_proxy frontend-loader:3000 {
            header_up X-Container-Name sonarr
            header_up X-Container-Port 8989
            header_up Host {host}
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-For {remote_host}
            header_up X-Forwarded-Proto {scheme}
        }
    }
    
    # Logs pour debugging
    log {
        output file /var/log/caddy/sonarr.log
        level INFO
    }
}

# Dashboard d'administration
admin.{$BASE_DOMAIN} {
    reverse_proxy frontend-dashboard:3000 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
    
    # Authentification basique (optionnelle)
    @auth_enabled {
        env ENABLE_BASIC_AUTH true
    }
    
    handle @auth_enabled {
        basicauth {
            {$ADMIN_USERNAME} {$ADMIN_PASSWORD_HASH}
        }
    }
    
    log {
        output file /var/log/caddy/admin.log
        level INFO
    }
}

# Configuration pour le développement local (localhost)
localhost:8080 {
    # API backend accessible directement
    handle /api/* {
        reverse_proxy backend-api:8000
    }
    
    # Interface frontend
    handle {
        reverse_proxy frontend-loader:3000
    }
}

# API directe (pour développement)
api.{$BASE_DOMAIN} {
    reverse_proxy backend-api:8000 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
    
    log {
        output file /var/log/caddy/api.log
        level INFO
    }
}

# Gestion des erreurs globales
handle_errors {
    @404 expression `{http.error.status_code} == 404`
    handle @404 {
        respond "Service non disponible - Vérifiez la configuration SelfStart" 404
    }
    
    @500 expression `{http.error.status_code} >= 500`
    handle @500 {
        respond "Erreur serveur - Contactez l'administrateur" 500
    }
}
EOF
    print_message "✓ Caddyfile créé"
else
    print_message "✓ Caddyfile existant détecté"
fi

# Créer le réseau Docker
print_info "Création du réseau Docker..."
if ! docker network ls | grep -q selfstart-network; then
    docker network create selfstart-network
    print_message "✓ Réseau selfstart-network créé"
else
    print_message "✓ Réseau selfstart-network existe déjà"
fi

# Arrêter les services existants
print_info "Arrêt des services existants..."
$DOCKER_COMPOSE_CMD down 2>/dev/null || true

# Construire et démarrer les services
print_info "Construction et démarrage des services SelfStart..."
$DOCKER_COMPOSE_CMD up -d --build

# Attendre que les services soient prêts
print_info "Attente du démarrage des services..."
sleep 10

# Vérifier l'état des services
print_info "Vérification de l'état des services..."

if $DOCKER_COMPOSE_CMD ps | grep -q "Up"; then
    print_message "✓ Services SelfStart démarrés avec succès!"
else
    print_error "Certains services ont échoué. Vérifiez les logs avec: $DOCKER_COMPOSE_CMD logs"
    exit 1
fi

# Rendre le script de test réseau exécutable
print_info "Configuration du script de diagnostic réseau..."
chmod +x network-test.sh
print_message "✓ Script network-test.sh prêt"

# Afficher les informations de connexion
echo
print_message "🎉 SelfStart est maintenant opérationnel!"
echo
print_info "URLs d'accès:"

# Lire le domaine depuis .env
domain=$(grep "BASE_DOMAIN=" .env | cut -d'=' -f2)

if [ "$domain" = "localhost" ]; then
    echo "  Interface d'administration: http://localhost:8080"
    echo "  API Backend: http://localhost:8000"
    echo "  Frontend: http://localhost:3001"
    echo "  Dashboard: http://localhost:3002 (démarrer avec: make dashboard)"
else
    echo "  Interface d'administration: https://admin.$domain"
    echo "  API Backend: https://api.$domain"
    echo "  Exemples d'applications:"
    echo "    - Sonarr: https://sonarr.$domain"
    echo "    - Radarr: https://radarr.$domain"
    echo "    - Jellyfin: https://jellyfin.$domain"
fi

echo
print_info "Commandes utiles:"
echo "  Voir les logs:           $DOCKER_COMPOSE_CMD logs -f"
echo "  Arrêter les services:    $DOCKER_COMPOSE_CMD down"
echo "  Redémarrer:              $DOCKER_COMPOSE_CMD restart"
echo "  Mettre à jour:           git pull && $DOCKER_COMPOSE_CMD up -d --build"
echo "  Tester le réseau:        ./network-test.sh"

echo
print_info "Pour démarrer des applications d'exemple:"
echo "  $DOCKER_COMPOSE_CMD -f docker-compose.yml -f examples/docker-compose.apps.yml --profile apps up -d"

echo
print_info "Pour démarrer le dashboard d'administration:"
echo "  $DOCKER_COMPOSE_CMD --profile dashboard up -d"

echo
print_warning "Notes importantes:"
echo "  1. Pour la production, modifiez les mots de passe dans .env"
echo "  2. Configurez vos DNS pour pointer vers ce serveur"
echo "  3. Assurez-vous que les ports 80 et 443 sont ouverts"

echo
print_message "Installation terminée! Consultez le README.md pour plus d'informations."