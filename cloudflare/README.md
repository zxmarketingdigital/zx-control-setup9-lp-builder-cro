# Cloudflare Worker — LP Builder

Worker (Hono) que serve API pra captura de leads + chat IA + listagem CRM + métricas. Persistência em D1 (SQLite serverless).

## Estrutura

```
cloudflare/worker/
├─ src/
│  ├─ index.ts          # Hono router (endpoints públicos + autenticados)
│  ├─ auth.ts           # valida X-LP-Token + CORS por allowed_origins
│  ├─ chat-adapter.ts   # streaming SSE: Gemini → Claude → canned
│  ├─ rate-limit.ts     # cap diário por (lp_config_id, endpoint)
│  └─ types.ts          # Env bindings
├─ wrangler.toml        # config (D1 binding + vars)
├─ schema.sql           # CREATE TABLE leads, lp_configs, chat_messages, usage_counters
├─ package.json
└─ tsconfig.json
```

## Setup (geralmente automatizado por `setup/setup_cloudflare.py`)

```bash
# 1. Login Cloudflare (abre browser)
wrangler login

# 2. Criar D1 database
wrangler d1 create lp-builder-db
# Copia o database_id retornado e cola em wrangler.toml

# 3. Aplicar schema
cd cloudflare/worker
bun install
bun run db:migrate

# 4. Setar secrets
wrangler secret put LP_TOKEN          # token compartilhado entre LPs do Worker
wrangler secret put GEMINI_API_KEY    # chat IA default
wrangler secret put ANTHROPIC_API_KEY # chat IA fallback (opcional)

# 5. Deploy
bun run deploy
```

Após deploy, o Worker fica em `https://lp-builder-worker.<account>.workers.dev`.

## Endpoints

| Rota | Auth | Função |
|------|------|--------|
| `GET /health` | público | `{ok:true, lp_count:N}` — usado como gate da skill T4 |
| `POST /capture-lead` | `X-LP-Token` + CORS + rate limit | Insere lead em D1 com UTM |
| `GET /leads?lp_id=...` | `X-LP-Token` | Lista leads paginados |
| `POST /chat-ia` | `X-LP-Token` + rate limit | Streaming SSE com fallback |
| `GET /usage` | `X-LP-Token` | Counts diários por endpoint |

Headers obrigatórios em chamadas autenticadas:

```
X-LP-Token: <token do wrangler secret>
X-LP-Id: <uuid do lp_config>
```

ou via query string `?lp_id=...`.

## Multi-tenant

Cada LP tem 1 row em `lp_configs` com:

- `id` (uuid) — referenciado nos requests
- `owner_id` (hash do email do aluno)
- `allowed_origins` (JSON array — CORS dinâmico)
- `daily_limit` (default 800)

LPs diferentes podem compartilhar o mesmo Worker. Validação é feita por `lp_config_id` + token.

## Rate limit

- Cap padrão: 800 requests/dia por `(lp_config_id, endpoint)`
- Margem confortável vs Gemini free tier (1500/dia)
- `GET /usage` retorna counts atuais — útil pra alerta 80%

## Auto-fallback do chat IA

Ordem de tentativa (em `src/chat-adapter.ts`):

1. **Gemini** (se `GEMINI_API_KEY` setada) — modelo `gemini-2.0-flash`
2. **Claude** (se `ANTHROPIC_API_KEY` setada) — modelo `claude-haiku-4-5`
3. **Canned response** — "Estou com alta demanda. Fale com humano: wa.me/..."

Em qualquer erro (rate limit, timeout, key missing), tenta o próximo provider.

## Smoke E2E

```bash
# Health
curl https://lp-builder-worker.workers.dev/health

# Captura lead
curl -X POST https://lp-builder-worker.workers.dev/capture-lead \
  -H "Content-Type: application/json" \
  -H "X-LP-Token: $LP_TOKEN" \
  -H "X-LP-Id: $LP_CONFIG_ID" \
  -H "Origin: https://your-lp-domain.com" \
  -d '{"name":"Teste","email":"teste@example.com"}'

# Lista leads
curl https://lp-builder-worker.workers.dev/leads?lp_id=$LP_CONFIG_ID \
  -H "X-LP-Token: $LP_TOKEN"
```

## Troubleshooting

Ver `docs/troubleshooting.md` na raiz do repo.
