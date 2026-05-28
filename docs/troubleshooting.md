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

Ordem de tentativa: Gemini → Claude → canned. Se cai sempre em canned:

```bash
# Verificar secrets setados
wrangler secret list
# Esperado: LP_TOKEN, GEMINI_API_KEY (e opcionalmente ANTHROPIC_API_KEY)

# Testar Gemini direto
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=$GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"contents":[{"parts":[{"text":"oi"}]}]}'
```

Se Gemini falha com 429 → cota free esgotou hoje (1500/dia). Aguarde reset (00h PT) ou ative Claude fallback.

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
