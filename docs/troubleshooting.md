# Troubleshooting — Setup 9 LP Builder

Erros comuns e como resolver.

## `wrangler login` não abre browser

```bash
wrangler login
# Esperando: abre browser em accounts.cloudflare.com
```

Se nada acontecer:
1. Copie a URL que apareceu no terminal
2. Cole manualmente no browser (mesmo desktop)
3. Aprove o token
4. Volte ao terminal — deve continuar

Sem sucesso? Modo alternativo (API token):
```bash
export CLOUDFLARE_API_TOKEN="..."   # gere em dash.cloudflare.com/profile/api-tokens
wrangler whoami
```

## `wrangler d1 create` falha com "unauthorized"

Conta gratuita Cloudflare tem D1 ativado por default, mas se aluno acabou de criar conta pode demorar alguns minutos pra "Workers" virar disponível.

Verificar:
```bash
wrangler whoami    # confirma login
wrangler d1 list   # se vazio + sem erro, é OK pra criar
```

Se ainda 401: aguarde 10min depois do signup; recheque em dash.cloudflare.com/?to=/:account/workers-and-pages.

## Worker deploya mas `/health` retorna 500

Provavelmente o D1 binding falhou. Verifique:

```bash
cd cloudflare/worker
cat wrangler.toml | grep database_id    # deve estar preenchido
wrangler tail                            # logs em tempo real
curl https://lp-builder-worker.workers.dev/health
```

Se `database_id` ainda for `PREENCHIDO_PELO_SETUP_CLOUDFLARE_PY`, rode `setup/setup_cloudflare.py` de novo.

## Chat IA retorna canned/silent

Ordem de tentativa: **Groq → Gemini → Claude → canned**. Se cai sempre em canned:

```bash
# Verificar secrets setados
wrangler secret list --cwd cloudflare/worker
# Esperado: LP_TOKEN + algum de GROQ_API_KEY/GEMINI_API_KEY/ANTHROPIC_API_KEY

# Testar Groq direto (GET /models não consome quota)
curl -H "Authorization: Bearer gsk_..." https://api.groq.com/openai/v1/models | head -c 200

# Ver logs do Worker em tempo real (filtra só erros)
./scripts/debug_worker.sh chat-ia
```

Causas comuns:
- HTTP 401 Groq → key inválida, regerar em https://console.groq.com/keys
- HTTP 429 Groq → rate limit por minuto (30 RPM). Aguarde 1min.
- HTTP 429 Gemini → cota free esgotou (1500/dia, **por conta Google**, compartilhado entre projetos). Espera reset 00h UTC ou troca pra Groq via `setup_chat_ia.py`.

## Chat IA exibe resposta vazia (bubble cinza pequeno)

Em versões antigas do template, o histórico Alpine não atualizava em tempo real. Sintoma: chat envia mensagem, mas o bubble do bot fica vazio (chip cinza pequeno).

Causa: `chatMessages.push(botMsg)` cria proxy reativo do objeto, mas mutar `botMsg.content` direto (variável local) não dispara re-render.

Fix: mutar via índice — `chatMessages[botIdx].content += delta`. Já corrigido no template atual; se ainda aparece, faça `git pull` e rode `bun run build` no `lp-template/`.

## CRM mostra "Erro ao carregar leads: Failed to fetch"

Sintoma: CRM abre, prompt aceita o LP_TOKEN, mas tabela fica vazia + alert de erro.

Causa: endpoint admin do Worker (`GET /leads`, `PATCH /leads/:id`, `/usage`) retornando JSON **sem headers CORS** — preflight passa mas response real é bloqueada silenciosamente pelo browser.

Fix: confirmar que `cloudflare/worker/src/index.ts` usa `jsonWithCors()` em vez de `c.json()` nesses endpoints. Se o seu commit é antigo, faça `git pull` + `cd cloudflare/worker && wrangler deploy`.

## "Failed to fetch" no form de captura, mas curl direto funciona

Causa: preflight CORS do browser bate em `OPTIONS /capture-lead` **sem** `?lp_id=` (browser não inclui headers custom no preflight). Worker retorna 204 sem `Access-Control-Allow-Origin` → preflight falha → POST nunca acontece.

Fix: client deve incluir `?lp_id=...` na URL do fetch (não só no header X-LP-Id). Já corrigido no template atual; `git pull` + rebuild se aparecer.

## CORS bloqueia captura na LP em produção

Modal envia o lead mas browser console mostra "CORS blocked":

1. Confirme domínio da LP está em `lp_configs.allowed_origins`:
   ```bash
   wrangler d1 execute lp-builder-db --remote \
     --command "SELECT id, allowed_origins FROM lp_configs WHERE id='$LP_CONFIG_ID'"
   ```
2. Se faltar:
   ```bash
   wrangler d1 execute lp-builder-db --remote \
     --command "UPDATE lp_configs SET allowed_origins='[\"https://cliente.com\"]' WHERE id='$LP_CONFIG_ID'"
   ```
3. Limpe cache do browser e recarregue

## `bun: command not found`

```bash
curl -fsSL https://bun.sh/install | bash
exec $SHELL    # recarrega PATH
bun --version
```

Setup também aceita `npm`/`node` como fallback. Se nem isso:

```bash
brew install node    # macOS
```

## LP em `localhost:5173` mas Worker em `workers.dev` → CORS

Inclua `http://localhost:5173` em `allowed_origins` durante dev. Em produção remova.

## Pages deploy: "project name conflict"

Aluno tem projeto Pages com mesmo nome em outra conta ou foi deletado mas DNS persistiu. Renomeie:

```bash
# Em setup_deploy.py, scriptado:
PROJECT="lp-${LP_CONFIG_ID_SHORT}-v2"
wrangler pages project create "$PROJECT" --production-branch main
```

## Custom domain não propaga

Após adicionar custom domain em dash CF Pages, espere até 5min e force:

```bash
# Limpa cache do browser
# Em outro terminal:
curl -I https://lp-cliente.com.br    # deve responder 200 com headers CF
```

Se demorar mais de 30min, verifique CNAME no zone DNS:
- `lp-cliente.com.br` deve apontar pra `lp-{short}.pages.dev`

## E2E na CI falha com Playwright timeout

Logs em `playwright-report/` (artifact upload em failure).

Causas comuns:
- `wrangler dev` não subiu nos 8s do `sleep` → aumente o `sleep` em `.github/workflows/full-e2e.yml`
- SANDBOX_MODE não está setado → mock IA não ativa, chamada real falha sem keys

## Modo `--local-only`: como migrar pra Cloudflare depois?

```bash
# 1. Rodar setup_cloudflare.py sem --local-only desta vez
python3 setup/setup_cloudflare.py
# 2. Reimportar leads locais pro D1:
sqlite3 ~/.operacao-ia/lps/$LP_CONFIG_ID/local.db ".dump leads" | \
  wrangler d1 execute lp-builder-db --remote --command -
# 3. Atualizar lp-config.json: worker_url = nova URL, lp_token = secret
```

## `gh repo clone` pede senha

Setup repo deve ser **public** (regra ZX LAB). Confirme:
```bash
gh repo view zxmarketingdigital/zx-control-setup9-lp-builder-cro --json visibility
```

Se private: peça pra Rafael rodar `gh repo edit --visibility public`.

---

Mais dúvidas? Abrir issue em https://github.com/zxmarketingdigital/zx-control-setup9-lp-builder-cro/issues
