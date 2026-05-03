.PHONY: build up down logs restart db opps metrics test shell stats clean

# Démarrage
build:
	docker compose build
docker compose up -d

up:
	docker compose up -d

down:
	docker compose down

# Logs
logs:
	docker compose logs -f ebay-bot

restart:
	docker compose restart ebay-bot

# Base
opps:
	docker compose exec postgres psql -U nassim -d ebay -c \
		"SELECT item_id,title,raw_price,total_price,category_name,created_at FROM listings ORDER BY created_at DESC LIMIT 20;"

db:
	docker compose exec postgres psql -U nassim -d ebay

# Métriques
metrics:
	curl -s http://localhost:9877/metrics

# Tests
shell:
	docker compose exec ebay-bot /bin/bash

test:
	docker compose exec ebay-bot python -m pytest bot/ -v 2>/dev/null || echo "No pytest available"

# Stats
stats:
	docker compose exec ebay-bot python -m shlex python -c \"from utils.cache import RedisCache; print(RedisCache().count_seen())\" 2>/dev/null || echo "Redis not available"

# Nettoyage
clean:
	docker compose down -v
