-- Schéma PostgreSQL pour le bot eBay Opportunities
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table listings
CREATE TABLE IF NOT EXISTS listings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_id         VARCHAR(64) NOT NULL,
    title           TEXT NOT NULL,
    raw_price       VARCHAR(32) NOT NULL,
    numeric_price   DECIMAL(10,2),
    url             VARCHAR(4096) NOT NULL,
    category_id     VARCHAR(16) NOT NULL,
    category_name   VARCHAR(64) NOT NULL,
    total_price     DECIMAL(10,2),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_listings_item_id
    ON listings (item_id);

CREATE INDEX IF NOT EXISTS idx_listings_category_id
    ON listings (category_id);

CREATE INDEX IF NOT EXISTS idx_listings_created_at
    ON listings (created_at DESC);

-- Table market_prices (historique du prix moyen par catégorie)
CREATE TABLE IF NOT EXISTS market_prices (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_id  VARCHAR(16) NOT NULL,
    avg_price    DECIMAL(10,2) NOT NULL,
    min_price    DECIMAL(10,2) NOT NULL,
    max_price    DECIMAL(10,2) NOT NULL,
    sample_size  INTEGER NOT NULL,
    computed_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_market_prices_cat_day
    ON market_prices (category_id, DATE(computed_at));

-- Table scan_runs
CREATE TABLE IF NOT EXISTS scan_runs (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    start_time TIMESTAMPTZ DEFAULT NOW(),
    duration_s REAL,
    listings_found INTEGER DEFAULT 0,
    listings_stored INTEGER DEFAULT 0,
    opportunities INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    notes TEXT
);

-- Table notifications
CREATE TABLE IF NOT EXISTS notifications (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    listing_id   UUID REFERENCES listings(id) ON DELETE CASCADE,
    channel      VARCHAR(16) NOT NULL CHECK (channel IN ('telegram','discord','slack')),
    item_id      VARCHAR(64) NOT NULL,
    score        REAL,
    sent_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_channel
    ON notifications (channel);

-- Table score_history (historique des scores)
CREATE TABLE IF NOT EXISTS score_history (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_id      VARCHAR(64) NOT NULL,
    category_id  VARCHAR(16) NOT NULL,
    score        REAL NOT NULL,
    raw_price    VARCHAR(32) NOT NULL,
    url          VARCHAR(4096) NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_score_history_item_id
    ON score_history (item_id);

-- Vue: dernières annonces avec score
CREATE OR REPLACE VIEW latest_scored_listings AS
SELECT
    l.item_id,
    l.title,
    l.raw_price,
    l.numeric_price,
    l.total_price,
    l.category_id,
    l.category_name,
    l.url,
    s.score,
    l.created_at
FROM listings l
JOIN score_history s ON l.item_id = s.item_id
ORDER BY l.created_at DESC
LIMIT 100;

-- Table sponsors (extension future)
CREATE TABLE IF NOT EXISTS sponsors (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name          VARCHAR(128) NOT NULL,
    channel       VARCHAR(16) NOT NULL CHECK (channel IN ('telegram','discord')),
    message       TEXT NOT NULL,
    display_rules VARCHAR(256) DEFAULT ''
);
