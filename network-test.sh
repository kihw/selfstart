#!/bin/bash

# Script de test et diagnostic réseau pour SelfStart
echo "🔍 Diagnostic réseau SelfStart..."

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

# 1. Vérifier Docker
echo -e "\n${BLUE}🐳 Vérification Docker${NC}"
if ! docker ps >/dev/null 2>&1; then
    print_error "Docker non accessible"
    exit 1
fi
print_success "Docker accessible"

# 2. Vérifier le réseau
echo -e "\n${BLUE}🌐 Vérification du réseau${NC}"
if ! docker network ls | grep -q "selfstart-network"; then
    print_warning "Réseau selfstart-network manquant, création..."
    docker network create selfstart-network
    if [ $? -eq 0 ]; then
        print_success "Réseau selfstart-network créé"
    else
        print_error "Échec création du réseau"
        exit 1
    fi
else
    print_success "Réseau selfstart-network existe"
fi

# 3. Vérifier les containers
echo -e "\n${BLUE}📦 État des containers${NC}"
containers=("selfstart-caddy" "selfstart-backend" "selfstart-frontend")
running_containers=0

for container in "${containers[@]}"; do
    if docker ps | grep -q "$container"; then
        print_success "Container $container en cours d'exécution"
        ((running_containers++))
    else
        print_warning "Container $container arrêté"
    fi
done

# 4. Démarrer les services si nécessaire
if [ $running_containers -lt 3 ]; then
    echo -e "\n${BLUE}🚀 Démarrage des services${NC}"
    docker-compose up -d
    sleep 15
fi

# 5. Tests de connectivité
echo -e "\n${BLUE}🔗 Tests de connectivité${NC}"

# Test API externe
if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    print_success "API accessible depuis l'extérieur (localhost:8000)"
else
    print_error "API non accessible depuis l'extérieur"
fi

# Test Frontend externe
if curl -f http://localhost:3000 >/dev/null 2>&1; then
    print_success "Frontend accessible depuis l'extérieur (localhost:3000)"
else
    print_error "Frontend non accessible depuis l'extérieur"
fi

# 6. Tests de communication interne
echo -e "\n${BLUE}🔄 Tests de communication interne${NC}"

# Test depuis frontend vers backend
if docker exec selfstart-frontend curl -f http://backend-api:8000/health >/dev/null 2>&1; then
    print_success "Communication frontend -> backend OK"
else
    print_error "Échec communication frontend -> backend"
fi

# Test depuis caddy vers backend
if docker exec selfstart-caddy curl -f http://backend-api:8000/health >/dev/null 2>&1; then
    print_success "Communication caddy -> backend OK"
else
    print_error "Échec communication caddy -> backend"
fi

# Test depuis caddy vers frontend
if docker exec selfstart-caddy curl -f http://frontend-loader:3000 >/dev/null 2>&1; then
    print_success "Communication caddy -> frontend OK"
else
    print_error "Échec communication caddy -> frontend"
fi

# 7. Test endpoints API
echo -e "\n${BLUE}📡 Tests endpoints API${NC}"
endpoints=("/health" "/api/containers" "/" "/docs")

for endpoint in "${endpoints[@]}"; do
    if curl -f "http://localhost:8000$endpoint" >/dev/null 2>&1; then
        print_success "Endpoint $endpoint accessible"
    else
        print_warning "Endpoint $endpoint non accessible"
    fi
done

# 8. Informations réseau détaillées
echo -e "\n${BLUE}🔍 Détails du réseau${NC}"
docker network inspect selfstart-network --format '{{range .Containers}}{{.Name}}: {{.IPv4Address}}{{"\n"}}{{end}}' 2>/dev/null || print_warning "Impossible d'inspecter le réseau"

# 9. Logs récents en cas d'erreur
if [ $running_containers -lt 3 ] || ! curl -f http://localhost:8000/health >/dev/null 2>&1; then
    echo -e "\n${BLUE}📋 Logs récents${NC}"
    print_info "Logs backend (20 dernières lignes):"
    docker-compose logs --tail=20 backend-api
    
    print_info "Logs frontend (20 dernières lignes):"
    docker-compose logs --tail=20 frontend-loader
    
    print_info "Logs caddy (20 dernières lignes):"
    docker-compose logs --tail=20 caddy
fi

# 10. Test dashboard si disponible
echo -e "\n${BLUE}📊 Test Dashboard${NC}"
if docker ps | grep -q "selfstart-dashboard"; then
    if curl -f http://localhost:3001 >/dev/null 2>&1; then
        print_success "Dashboard accessible (localhost:3001)"
        
        # Test communication dashboard -> backend
        if docker exec selfstart-dashboard curl -f http://backend-api:8000/health >/dev/null 2>&1; then
            print_success "Communication dashboard -> backend OK"
        else
            print_error "Échec communication dashboard -> backend"
        fi
    else
        print_error "Dashboard non accessible"
    fi
else
    print_info "Dashboard non démarré (profil optionnel)"
fi

# 11. Résumé et recommandations
echo -e "\n${BLUE}📋 Résumé${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# URLs d'accès
domain=$(grep "BASE_DOMAIN=" .env 2>/dev/null | cut -d'=' -f2 || echo "localhost")
echo -e "${BLUE}🌐 URLs d'accès:${NC}"
if [ "$domain" = "localhost" ]; then
    echo "  Backend API:     http://localhost:8000"
    echo "  Frontend:        http://localhost:3000"
    echo "  Dashboard:       http://localhost:3001 (si activé)"
    echo "  Documentation:   http://localhost:8000/docs"
else
    echo "  Admin Interface: https://admin.$domain"
    echo "  API Direct:      https://api.$domain"
    echo "  Applications:    https://[app].$domain"
fi

# Commandes utiles
echo -e "\n${BLUE}🛠️ Commandes utiles:${NC}"
echo "  make start           # Démarrer tous les services"
echo "  make logs            # Voir les logs"
echo "  make status          # État des services"
echo "  make restart         # Redémarrer"
echo "  make apps            # Démarrer avec exemples"

# Troubleshooting
echo -e "\n${BLUE}🔧 En cas de problème:${NC}"
echo "  1. Vérifier les logs: docker-compose logs"
echo "  2. Redémarrer:        docker-compose restart"
echo "  3. Nettoyer:          docker-compose down && docker-compose up -d"
echo "  4. Rebuild:           docker-compose build --no-cache"

echo -e "\n${GREEN}✅ Diagnostic terminé!${NC}"