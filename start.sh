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

# Vérifier Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose n'est pas installé. Veuillez installer Docker Compose d'abord."
    exit 1
fi

# Vérifier que Docker fonctionne
if ! docker ps &> /dev/null; then
    print_error "Docker n'est pas démarré ou vous n'avez pas les permissions nécessaires."
    print_info "Essayez: sudo systemctl start docker"
    print_info "Ou ajoutez votre utilisateur au groupe docker: sudo usermod -aG docker \$USER"
    exit 1
fi

print_message "✓ Docker et Docker Compose sont disponibles"

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
mkdir -p downloads media/tv media/movies media/music config
print_message "✓ Répertoires créés"

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
docker-compose down 2>/dev/null || true

# Construire et démarrer les services
print_info "Construction et démarrage des services SelfStart..."
docker-compose up -d --build

# Attendre que les services soient prêts
print_info "Attente du démarrage des services..."
sleep 10

# Vérifier l'état des services
print_info "Vérification de l'état des services..."

if docker-compose ps | grep -q "Up"; then
    print_message "✓ Services SelfStart démarrés avec succès!"
else
    print_error "Certains services ont échoué. Vérifiez les logs avec: docker-compose logs"
    exit 1
fi

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
    echo "  Frontend: http://localhost:3000"
else
    echo "  Interface d'administration: https://admin.$domain"
    echo "  API Backend: http://$domain:8000"
    echo "  Exemples d'applications:"
    echo "    - Sonarr: https://sonarr.$domain"
    echo "    - Radarr: https://radarr.$domain"
    echo "    - Jellyfin: https://jellyfin.$domain"
fi

echo
print_info "Commandes utiles:"
echo "  Voir les logs:           docker-compose logs -f"
echo "  Arrêter les services:    docker-compose down"
echo "  Redémarrer:              docker-compose restart"
echo "  Mettre à jour:           git pull && docker-compose up -d --build"

echo
print_info "Pour démarrer des applications d'exemple:"
echo "  docker-compose -f docker-compose.yml -f examples/docker-compose.apps.yml --profile apps up -d"

echo
print_warning "Notes importantes:"
echo "  1. Pour la production, modifiez les mots de passe dans .env"
echo "  2. Configurez vos DNS pour pointer vers ce serveur"
echo "  3. Assurez-vous que les ports 80 et 443 sont ouverts"

echo
print_message "Installation terminée! Consultez le README.md pour plus d'informations."
