# Migration v2 — Setup 9 (28/05/26)

> **Quem precisa ler:** se você clonou o repo **antes de 28/05/26** e já rodou `setup_cloudflare.py` no seu Mac.
>
> **Quem pode pular:** clone novo a partir de 29/05/26 — os fixes já estão aplicados, nada a fazer.

Esta versão do template corrige 15+ bugs descobertos em revisão por agents (Security/Performance/Tests + Codex). Pra você que já tem setup rodando, **3 passos rápidos** garantem que tudo continue funcionando com as melhorias.

---

## Passo 1 — Conferir `wrangler.toml`

Abra `cloudflare/worker/wrangler.toml` e veja a linha 10. **Se aparecer**:

```toml
database_id = "PREENCHIDO_PELO_SETUP_CLOUDFLARE_PY"
```

→ nada a fazer aqui.

**Se aparecer um UUID** (ex: `database_id = "d7a151bb-..."`), você herdou o ID do banco de quem criou o template. **Tem que resetar**:

```bash
# Edite manualmente, troque pelo placeholder:
database_id = "PREENCHIDO_PELO_SETUP_CLOUDFLARE_PY"
```

Depois rode `python3 setup/setup_cloudflare.py` — ele vai detectar o seu próprio D1 (ou criar novo) e preencher de novo.

> Não vamos perder seus leads — o D1 do seu projeto continua intacto na sua conta Cloudflare. O `wrangler.toml` é só o *ponteiro*, e o `setup_cloudflare.py` localiza ele de novo via `wrangler d1 list`.

---

## Passo 2 — Aplicar migrations do schema

O schema do D1 ganhou colunas novas (briefing, token_hash, fallback_contact_url em `lp_configs`; page_url, referrer em `leads`). Rode:

```bash
python3 setup/setup_cloudflare.py
```

Ele **detecta automaticamente** quais colunas faltam (via `PRAGMA table_info`) e aplica só os `ALTER` necessários. Idempotente — pode rodar várias vezes sem quebrar.

---

## Passo 3 — Regerar `lp-public.json`

A LP nova espera `features` como objetos `{icon, title, desc}` (antes era array de strings). Rode:

```bash
python3 setup/setup_minicrm.py
```

Ele detecta features no formato antigo e migra automaticamente. Backup salvo em `lp-template/public/lp-public.json.bak`.

---

## Bônus — Mudanças que valem você conhecer

- **Chat IA**: provider padrão agora é **Groq** (Llama 3.3 70B, gratis sem cartão). Se você usou Gemini antes e a quota estourou: rode `python3 setup/setup_chat_ia.py` e escolha opção 1 (Groq). Pega key em https://console.groq.com/keys.
- **CORS**: o setup agora cuida automaticamente de `allowed_origins` pós-deploy. Você não precisa mais editar manualmente quando o domínio `.pages.dev` muda.
- **CRM**: novo endpoint `PATCH /leads/:id` realmente persiste mudança de status (antes era optimistic e perdia ao recarregar).
- **Cache do Pages**: agora tem `_headers` configurado pra não cachear HTML/JSON — fixes aparecem imediatamente sem precisar de hard reload.
- **Pasta `components/`**: movida pra `lp-template/public/components/`. Se você tem fork local com mudanças em `lp-template/components/`, mova-as pra `public/components/` antes do `git pull`.

---

Dúvida? Abre issue em https://github.com/zxmarketingdigital/zx-control-setup9-lp-builder-cro/issues ou pergunta no grupo do ZX Control Scale.
