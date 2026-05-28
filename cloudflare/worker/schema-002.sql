-- Migration 002 — Setup 9 (team-review fixes)
--
-- ⚠️  NÃO rodar este arquivo direto (`wrangler d1 execute --file=schema-002.sql`)
--     se o D1 já recebeu alguma das colunas — ALTER ADD COLUMN sem IF NOT EXISTS
--     dá erro `duplicate column name`.
--
-- ✅  Fonte canônica de migração: `python3 setup/setup_cloudflare.py`
--     Ele detecta colunas faltando via `PRAGMA table_info(...)` e aplica
--     só os ALTERs necessários, individual e idempotente.
--
-- Este arquivo serve como documentação do delta + fallback manual:
-- se você precisa aplicar uma coluna específica, copie a linha e rode:
--   wrangler d1 execute lp-builder-db --remote --command "ALTER TABLE..."

-- ============================================================
-- lp_configs (3 colunas novas)
-- ============================================================

-- C5: briefing carregado server-side (antes vinha do cliente — prompt injection)
ALTER TABLE lp_configs ADD COLUMN briefing TEXT NOT NULL DEFAULT '';

-- C5: URL de fallback (wa.me/…) usado no canned response do chat IA
ALTER TABLE lp_configs ADD COLUMN fallback_contact_url TEXT;

-- H3: token_hash (sha-256) por LP — substitui env.LP_TOKEN shared
ALTER TABLE lp_configs ADD COLUMN token_hash TEXT;

-- ============================================================
-- leads (2 colunas novas)
-- ============================================================

-- H8: atribuição de tráfego (URL real onde lead converteu)
ALTER TABLE leads ADD COLUMN page_url TEXT;

-- H8: referrer (origem antes da LP — google, instagram, etc)
ALTER TABLE leads ADD COLUMN referrer TEXT;

-- ============================================================
-- Índices (CREATE IF NOT EXISTS é seguro)
-- ============================================================

-- M5: query `WHERE lp_config_id=? ORDER BY created_at DESC` agora
-- usa índice composto em vez de sort em memória.
CREATE INDEX IF NOT EXISTS idx_leads_lp_created
  ON leads(lp_config_id, created_at DESC);
