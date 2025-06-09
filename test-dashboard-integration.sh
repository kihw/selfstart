#!/bin/bash

# Script de test d'intégration Dashboard <-> Backend
echo "🧪 Test d'intégration SelfStart Dashboard..."

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

# 1. Vérifier que Docker fonctionne
if ! docker ps >/dev/null 2>&1; then
    print_error "Docker n'est pas accessible"
    exit 1
fi
print_success "Docker accessible"

# 2. Vérifier l'existence du réseau
if ! docker network ls | grep -q "selfstart-network"; then
    print_warning "Réseau selfstart-network n'existe pas, création..."
    docker network create selfstart-network
fi
print_success "Réseau selfstart-network OK"

# 3. Démarrer le backend si pas déjà lancé
if ! docker ps | grep -q "selfstart-backend"; then
    print_warning "Backend non démarré, démarrage..."
    docker-compose up -d backend-api
    sleep 5
fi

# 4. Tester l'API backend
echo "🔌 Test de l'API backend..."
if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    print_success "API backend accessible sur localhost:8000"
else
    print_error "API backend non accessible"
    exit 1
fi

# 5. Construire le dashboard
echo "🏗️ Construction du dashboard..."
docker-compose build frontend-dashboard

# 6. Démarrer le dashboard
echo "🚀 Démarrage du dashboard..."
docker-compose --profile dashboard up -d

# 7. Attendre le démarrage
echo "⏳ Attente du démarrage (30s)..."
sleep 30

# 8. Vérifier que le dashboard est accessible
if curl -f http://localhost:3001 >/dev/null 2>&1; then
    print_success "Dashboard accessible sur localhost:3001"
else
    print_error "Dashboard non accessible"
    docker-compose logs frontend-dashboard
    exit 1
fi

# 9. Test de communication interne
echo "🔗 Test de communication interne..."
# Tester depuis le container dashboard vers l'API
docker-compose exec frontend-dashboard curl -f http://backend-api:8000/health 2>/dev/null
if [ $? -eq 0 ]; then
    print_success "Communication interne dashboard -> backend OK"
else
    print_error "Échec communication interne"
    echo "📋 Logs dashboard:"
    docker-compose logs --tail=20 frontend-dashboard
    echo "📋 Logs backend:"
    docker-compose logs --tail=20 backend-api
fi

# 10. Test API depuis le dashboard
echo "📡 Test des endpoints API..."
endpoints=("/health" "/api/containers" "/")
for endpoint in "${endpoints[@]}"; do
    if curl -f "http://localhost:8000$endpoint" >/dev/null 2>&1; then
        print_success "Endpoint $endpoint OK"
    else
        print_warning "Endpoint $endpoint non accessible"
    fi
done

echo ""
echo "🎯 Résumé du test:"
echo "  - Backend: http://localhost:8000"
echo "  - Dashboard: http://localhost:3001"
echo "  - API Docs: http://localhost:8000/docs"
echo ""
echo "🔧 Commandes utiles:"
echo "  docker-compose logs frontend-dashboard"
echo "  docker-compose logs backend-api"
echo "  docker-compose ps"
