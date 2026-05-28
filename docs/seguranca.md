# Segurança — Setup 9 LP Builder

Setup 9 trata dados de leads de clientes do aluno. Estes são os controles obrigatórios.

## Auth do Worker (LP_TOKEN)

Todo request a endpoints autenticados exige header `X-LP-Token`. O token vive como secret do Worker (`wrangler secret put LP_TOKEN`) e NUNCA aparece em código commitado.

- Rotacionar: `wrangler secret put LP_TOKEN` (novo valor) + atualizar `lp-config.json` da(s) LP(s) que usam esse Worker
- Aluno pode (futuro) usar 1 LP_TOKEN por LP — v1 mantém 1 por Worker por simplicidade

## CORS por allowed_origins

`lp_configs.allowed_origins` (JSON array em D1) define quais domínios podem chamar o Worker:

```json
["https://cliente.com.br", "https://www.cliente.com.br", "http://localhost:5173"]
```

Default proibido `*`. Toda LP precisa preencher pelo menos 1 origin no setup (etapa 4). Origin não declarado retorna 403.

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
