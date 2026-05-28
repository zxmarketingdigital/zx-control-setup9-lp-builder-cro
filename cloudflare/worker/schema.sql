-- Setup 9 — Schema D1 (SQLite serverless)
-- Aplicar via: wrangler d1 execute lp-builder-db --file=schema.sql
-- Migrations: schema-002.sql (briefing/token_hash/page_url/referrer)

CREATE TABLE IF NOT EXISTS lp_configs (
  id                   TEXT PRIMARY KEY,
  owner_id             TEXT NOT NULL,
  name                 TEXT NOT NULL,
  allowed_origins      TEXT NOT NULL DEFAULT '[]',  -- JSON array de origins permitidos
  daily_limit          INTEGER NOT NULL DEFAULT 800,
  briefing             TEXT NOT NULL DEFAULT '',    -- system prompt do chat IA (server-side)
  fallback_contact_url TEXT,                        -- wa.me/... pra canned response
  token_hash           TEXT,                        -- sha-256 hex do lp_token (auth admin)
  created_at           TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_lp_configs_owner ON lp_configs(owner_id);

CREATE TABLE IF NOT EXISTS leads (
  id           TEXT PRIMARY KEY,
  lp_config_id TEXT NOT NULL,
  name         TEXT NOT NULL,
  email        TEXT,
  whatsapp     TEXT,
  status       TEXT NOT NULL DEFAULT 'novo'
               CHECK(status IN ('novo','em_conversa','qualificado','encaminhado_humano','converteu','abandonou')),
  utm_source   TEXT,
  utm_medium   TEXT,
  utm_campaign TEXT,
  utm_content  TEXT,
  utm_term     TEXT,
  page_url     TEXT,
  referrer     TEXT,
  created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (lp_config_id) REFERENCES lp_configs(id)
);
CREATE INDEX IF NOT EXISTS idx_leads_lp ON leads(lp_config_id);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at);
CREATE INDEX IF NOT EXISTS idx_leads_lp_created ON leads(lp_config_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leads_utm_source ON leads(utm_source);

CREATE TABLE IF NOT EXISTS chat_messages (
  id           TEXT PRIMARY KEY,
  lp_config_id TEXT NOT NULL,
  lead_id      TEXT,  -- pode ser null se visitante não virou lead ainda
  session_id   TEXT NOT NULL,
  role         TEXT NOT NULL,  -- user|assistant|system
  content      TEXT NOT NULL,
  provider     TEXT,  -- gemini|claude|canned
  created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (lp_config_id) REFERENCES lp_configs(id),
  FOREIGN KEY (lead_id) REFERENCES leads(id)
);
CREATE INDEX IF NOT EXISTS idx_chat_lp ON chat_messages(lp_config_id);
CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_created ON chat_messages(created_at);

CREATE TABLE IF NOT EXISTS usage_counters (
  lp_config_id TEXT NOT NULL,
  day          TEXT NOT NULL,  -- YYYY-MM-DD UTC
  endpoint     TEXT NOT NULL,  -- capture-lead|chat-ia
  count        INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (lp_config_id, day, endpoint)
);
