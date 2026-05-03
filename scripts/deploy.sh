#!/usr/bin/env bash
# Script de deploiement du bot eBay Opportunities

set -euo pipefail

bold() { printf '\033[1m%s\033[0m\n' "$1"; }
info()  { printf '\033[32m[INFO]\033[0m %s\n' "$1"; }
error() { printf '\033[31m[ERROR]\033[0m %s\n' "$1" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

	cd "$PROJECT_DIR"

if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    cp .env.example .env
    info ".env cree a partir de .env.example"
  else
    error ".env manquant et aucun .env.example Remix"
  fi
fi

info "Verification de Docker..." >&2
if ! command -v docker &> /dev/null; then
  error "Docker non installe"
fi
docker compose version &> /dev/null || error "docker compose non disponible"

info "Build des images..." >&2
docker compose build --no-cache

info "Creation du reseau monitoring_net s'il n'existe pas..." >&2
docker network inspect monitoring_network &> /dev/null || \
  docker network create monitoring_network

info "Démarrage des services..." >&2
docker compose up -d

info "Verification de PostgreSQL..." >&2
docker compose exec -T postgres pg_isready -U nassim -d ebay \
  || error "PostgreSQL ne demarre pas"

info "Verification de Redis..." >&2
docker compose exec -T redis redis-cli ping | grep -q PONG \
  || error "Redis ne repond pas"

info "Test de l'endpoint Prometheus..." >&2
sleep 10
curl -f -s http://localhost:9877/metrics &> /dev/null \
  || error "Exporteur Prometheus injoignable"

bold "=== Déploiement terminé ==="
echo ""
echo "Services lancés:"
docker compose ps
info "Logs  : docker compose logs -f ebay-bot"
info "Base  : make db"
info "Opport: make opps"
info "Toutes les commandes: make"
