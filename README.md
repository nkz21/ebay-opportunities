# ebay-opportunities

Bot de détection d'opportunités sur eBay.fr - Scan automatique des catégories **Télévision** et **Appareil photo** (neuf/ouvert non utilisé), scoring basé sur le prix moyen du marché, alertes Telegram et Discord.

## Stack technique

- **Python 3.12** - Bot principal
- **PostgreSQL** - Base de données des annonces
- **Redis** - Cache et déduplication des URLs
- **Docker & Docker Compose** - Orchestration des services
- **Prometheus** - Métriques applicatives (port 9877)
- **Grafana** - Dashboard de monitoring
- **Portainer** - Gestion des conteneurs
- **Tailscale** - Accès distant sécurisé

## Architecture du bot

```
bot/
├── main.py              # Scheduler principal + boucle de scan
├── metrics_server.py    # Serveur métriques Prometheus (port 9877)
├── scrapers/
│   ├── __init__.py
│   └── ebay_scraper.py  # Scraper eBay.fr (User-Agent rotation, retry)
├── analyzers/
│   ├── __init__.py
│   └── opportunity.py   # Calcul du score d'opportunité
├── notifiers/
│   ├── __init__.py
│   ├── telegram.py      # Notifications Telegram
│   └── discord.py       # Notifications Discord
└── utils/
    ├── __init__.py
    ├── settings.py      # Configuration (Pydantic)
    ├── database.py      # Connexion PostgreSQL & ORM
    └── cache.py         # Wrapper Redis pour déduplication

docker/
└── init.sql             # Schéma PostgreSQL (5 tables + vue + indexes)
```

## Fonctionnement du bot

1. **Scan** : Recherche eBay.fr par mots-clés (TV, Caméscope) avec filtres état neuf/ouvert
2. **Déduplication** : Vérification des URLs déjà traitées via Redis
3. **Stockage** : Persistance des annonces en PostgreSQL
4. **Analyse** : Calcul du prix moyen sur 30 jours + score d'opportunité
5. **Alerte** : Notification Telegram/Discord si score > seuil
6. **Métriques** : Export Prometheus scrapé par ta stack monitoring existante

## Configuration

Copier le fichier d'environnement :

```bash
cp .env.example .env
nano .env
```

### Variables d'environnement

| Variable | Description | Exemple |
|---|---|---|
| `POSTGRES_URL` | URL de connexion PostgreSQL | `postgresql://user:pass@postgres:5432/ebay` |
| `REDIS_URL` | URL Redis | `redis://redis:6379/0` |
| `TELEGRAM_BOT_TOKEN` | Token du bot Telegram | `6123456789:AAE...` |
| `TELEGRAM_CHAT_ID` | ID du chat Telegram | `-1001234567890` |
| `DISCORD_WEBHOOK_URL` | Webhook Discord | `https://discord.com/api/webhooks/...` |
| `SCAN_INTERVAL` | Intervalle entre les scans (secondes) | `300` |
| `PROXY_URL` | Proxy optionnel (HTTP/SOCKS) | (optionnel) |

## Déploiement

### 1. Cloner le repo

```bash
git clone https://github.com/nkz21/ebay-opportunities.git
cd ebay-opportunities
```

### 2. Démarrer avec Docker Compose

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### 3. Vérifier les logs

```bash
docker compose logs -f ebay-bot
```

### 4. Accéder à la base de données

```bash
make db
```

## Services et ports

| Service | Port | URL |
|---|---|---|
| ebay-bot (app) | - | Conteneur uniquement |
| ebay-exporter (Prometheus) | 9877 | `http://<host>:9877/metrics` |
| PostgreSQL | 5432 | `localhost:5432` |
| Redis | 6379 | `localhost:6379` |
| Adminer (UI DB) | 8095 | `http://<host>:8095` |

## Intégration Prometheus (stack monitoring)

Ajouter dans `/srv/tools/monitoring/config/prometheus/prometheus.yml` :

```yaml
  - job_name: 'ebay-bot'
    static_configs:
      - targets: ['ebay-exporter:9877']
```

Puis redémarrer Prometheus : `cd /srv/tools/monitoring && docker compose restart prometheus`

## Commandes Makefile

```bash
make build       # Build + démarrage des services
make logs        # Logs du bot en direct
make restart     # Redémarrer le bot seul
make db          # Console PostgreSQL
make opps        # Voir les opportunités détectées
make metrics     # Voir les métriques brutes
make test        # Lancer les tests
make shell       # Shell dans le conteneur bot
make stats       # Stats de déduplication Redis
make clean       # Arrêter et supprimer les volumes
```

## Métriques Prometheus exposées

| Métrique | Description |
|---|---|
| `ebay_scrapes_total` | Nombre total de scans effectués |
| `ebay_listings_found` | Nombre d'annonces trouvées par scan |
| `ebay_listings_stored` | Nombre d'annonces stockées en base |
| `ebay_opportunities_total` | Nombre total d'opportunités détectées |
| `ebay_scrape_duration_seconds` | Durée d'un scan |
| `ebay_redis_connections` | Connexions Redis actives |
| `ebay_db_connections` | Connexions PostgreSQL actives |

## Catégories ciblées

| Catégorie | Mots-clés par défaut |
|---|---|
| Télévision | `smart tv 4k`, `tv oled`, `tv qled` |
| Appareil photo | `appareil photo reflex`, `appareil photo mirrorless` |

Élargissement possible à d'autres catégories via modification de `bot/utils/settings.py`.

## FAQ

**Comment ajouter de nouvelles catégories ?**  
Édite les listes `CATEGORY_KEYWORDS` et `CATEGORY_IDS` dans `bot/utils/settings.py`.

**Le bot tourne 24/7 ?**  
Oui, il boucle en continu avec l'intervalle défini dans `SCAN_INTERVAL`. Un `restart: unless-stopped` dans le docker-compose assure le redémarrage au reboot.

**Comment voir les annonces en base ?**  
`docker compose exec postgres psql -d ebay -c "SELECT * FROM listings ORDER BY created_at DESC LIMIT 10;"`

## License

MIT License - voir le fichier [LICENSE](LICENSE).
