# Segurança — Setup 9 LP Builder

Setup 9 trata dados de leads de clientes do aluno. Estes são os controles obrigatórios.

## Auth do Worker (LP_TOKEN por LP)

Endpoints admin (`GET /leads`, `PATCH /leads/:id`, `GET /usage`) exigem header `X-LP-Token`. O token NÃO é comparado contra um valor único compartilhado — o Worker faz **SHA-256 timing-safe compare** contra `lp_configs.token_hash` (per-LP):

- `setup_cloudflare.py` calcula `hashlib.sha256(LP_TOKEN).hexdigest()` e grava em `lp_configs.token_hash`
- Worker (`cloudflare/worker/src/auth.ts`) faz `crypto.subtle.digest('SHA-256', input)` + compare char-a-char com XOR (constant-time)
- Token em plaintext só existe em 2 lugares: secret do Worker (criptografado em rest pelo Cloudflare) e `~/.operacao-ia/config/setup9.env` no Mac do aluno (gitignored)
- Rotação: rode `setup_cloudflare.py` de novo após gerar novo LP_TOKEN — ele atualiza o `token_hash` no D1

**Fallback de compat**: se `lp_configs.token_hash` é NULL (setups antigos), Worker cai pra compare direto contra `env.LP_TOKEN` (sem timing-safe). Recomendado rodar a migration pra encerrar esse path.

## Origin obrigatório (endpoints públicos)

`POST /capture-lead` e `POST /chat-ia` são chamados pelo browser do visitante (sem token). Segurança vem de **3 camadas**:

1. **Origin obrigatório** — header `Origin` ausente → 403 `origin_required`. Bloqueia curl/Postman/server-to-server.
2. **Allowlist** — `lp_configs.allowed_origins` (JSON array no D1) define quais Origin podem postar:

```json
["https://cliente.com.br", "http://localhost:5173", "https://*.pages.dev"]
```

Formatos aceitos: `https://<host>[:port]`, `http://localhost[:port]`, ou `https://*.pages.dev` (wildcard — Worker faz suffix match).

3. **Rate limit** — cap diário (800/dia por LP+endpoint) — 429 quando excedido. Acima cap o Worker rejeita sem chamar a IA, prevenindo abuse de billing.

Default proibido `*`. `setup_deploy.py` atualiza automaticamente `allowed_origins` no D1 com o domínio `*.pages.dev` canônico após o primeiro deploy.

## Rate limit (anti-abuse)

Cap diário 800 req/dia por `(lp_config_id, endpoint)`. Excedido → 429.

- Endpoint `GET /usage` retorna counts atuais
- Skill futura `/alertar-uso-lp` pode notificar 80%

## Spend limits do Chat IA

### Claude SDK (Anthropic)

**OBRIGATÓRIO** setar spend limit ANTES de criar API key:

1. https://console.anthropic.com → Settings → Limits
2. Defina mensal (ex: $5-10) e configure email de alerta em 80%
3. Só então crie a key em → API Keys

Setup força confirmação interativa nesta etapa.

### Gemini (Google AI)

Free tier limitado por design (1500 req/dia, 60 req/min). Sem custo. Worker cap 800/dia adiciona margem.

Pra produção alta, aluno troca pra paid tier Google AI Platform — mas isso fica explicitamente fora do Setup 9.

## Dados sensíveis

| Item | Onde fica | Commitado? |
|------|-----------|------------|
| LP_TOKEN | `wrangler secret` + `~/.operacao-ia/config/setup9.env` | NÃO |
| GEMINI/ANTHROPIC keys | `wrangler secret` + `~/.operacao-ia/config/setup9.env` | NÃO |
| D1_DATABASE_ID | `cloudflare/worker/wrangler.toml` | SIM (público, sem risco) |
| Leads (nome/email/WhatsApp) | D1 (no Cloudflare do aluno) | NÃO |
| briefing.md | `lp-template/briefing.md` | SIM (sem dados de cliente final) |

`.gitignore` cobre `*.db`, `.env`, `lp-config.json` (gerado por LP, contém LP_TOKEN), `briefing-state.json`.

## LGPD (resumo prático)

- LP captura nome + email + WhatsApp + UTMs
- Aluno deve incluir link de política de privacidade no footer (template inclui placeholder)
- Aluno é controlador dos dados; ZX LAB não tem acesso
- Cliente do aluno pode solicitar export (`/exportar-leads-csv`) ou exclusão (`/analisar-leads-crm --delete-lead {id}` — futuro)

## Recuperação de incidente

| Cenário | Ação |
|---------|------|
| LP_TOKEN vazado | `wrangler secret put LP_TOKEN <novo>` + atualizar lp-config.json de cada LP afetada |
| Worker URL exposto sem origin allowlist | Update `lp_configs.allowed_origins` via `wrangler d1 execute --remote --command "UPDATE..."` |
| Suspeita de scrape em massa | `GET /usage` mostra padrão; pra mitigar imediato, abaixar `daily_limit` da LP via UPDATE |
| Lead vazado | LGPD: notificar titular + autoridade conforme Art. 48 |

## Auditoria

- Worker tem `[observability] enabled = true` em wrangler.toml → logs visíveis em Cloudflare dashboard
- Tabela `chat_messages` registra cada conversa (provider usado, content, timestamp)
- Tabela `usage_counters` registra contagem diária

## Roadmap (fora v1)

- LP_TOKEN por LP (não compartilhado)
- Rotação automática de secrets
- Webhook de notificação em 80% de uso
- WAF rule pra bloquear bots conhecidos
- Encryption-at-rest opcional (D1 já criptografa, mas claims explícitos)
