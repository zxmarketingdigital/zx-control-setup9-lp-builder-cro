# ZX Control — Setup 9: LP Builder Profissional + Mini CRM + Chat IA

Setup oficial da Semana 9 do ZX Control Scale. Pare de entregar template genérico ao cliente — entregue **LP profissional com captura de leads, mini CRM e chat IA**, tudo no Cloudflare grátis. Em ~90 minutos pro primeiro cliente, 15 minutos pro próximo via `/clonar-lp`.

## Pré-requisitos

- **macOS** (Linux/Windows funcionam parcialmente — sem LaunchAgents)
- **Setup 8 do ZX Control concluído** (`phase_completed >= 8` em `~/.operacao-ia/config/config.json`)
- **Python 3.9+** — geralmente já vem com macOS
- **Claude Code** instalado e configurado
- **Node 18+** (block) e **bun** (warning — `brew install bun`; se faltar, npm é fallback)
- **Conta Cloudflare grátis** — `wrangler login` abre o browser pra criar/entrar
- **Gemini API key** — `aistudio.google.com` → Get API key (1500 req/dia grátis)
- *(opcional)* **Claude API key** — `console.anthropic.com` → **defina spend limit ANTES** de criar a key

## Instalação

```bash
gh repo clone zxmarketingdigital/zx-control-setup9-lp-builder-cro
cd zx-control-setup9-lp-builder-cro
claude
```

Ao abrir o Claude, ele aguarda você digitar **`INICIAR SETUP SEMANA 9`** para começar.

A partir daí o setup é guiado — **8 etapas**, cada uma com explicação + execução + validação.

## O que você terá no final

- LP profissional pronta pra cliente em ~90 minutos (40min no modo rápido)
- Mini CRM próprio com filtros, status, UTM tracking e export CSV
- Chat IA streaming respondendo dúvidas com base no briefing
- Métricas de conversão integradas (Cloudflare Web Analytics + UTM)
- Skill `/clonar-lp` pra duplicar pro próximo cliente em 15 minutos

## Estrutura

```
zx-control-setup9-lp-builder-cro/
├─ CLAUDE.md            # roteiro de instalação (lido pelo Claude Code)
├─ MASTERCLASS.md       # roteiro da aula em vídeo
├─ README.md            # este arquivo
├─ setup/               # scripts Python das 8 etapas
├─ lp-template/         # LP estática (Vite + Alpine + Tailwind CDN)
│  ├─ index.html        # LP pública
│  ├─ crm.html          # mini CRM
│  ├─ components/       # componentes HTML
│  ├─ briefings/        # templates por nicho (modo rápido)
│  └─ public/           # arquivos servidos publicamente
├─ cloudflare/worker/   # Worker (Hono) + schema D1 (SQLite serverless)
├─ scripts/             # automações pós-setup
├─ docs/                # documentação (troubleshooting, segurança, métricas)
└─ .claude/skills/      # skills locais (clonar-lp, analisar-leads-crm, etc.)
```

## Comandos pós-instalação (skills locais)

```
/clonar-lp                  Duplica LP existente pra novo cliente em ~15min
/revisar-copy-lp            Audita copy contra checklist CRO
/exportar-leads-csv         Exporta leads em CSV pra entregar ao cliente
/analisar-leads-crm         Diagnostica leads parados, sugere follow-up por UTM source
```

## Limitações conhecidas

- **D1 region us-east** — latência ~200-400ms BR. Pra Setup 10+ avaliamos Hyperdrive ou region pinning quando disponível.
- **Gemini PT-BR < Claude em copy persuasiva** — pra chat IA premium, configure Claude SDK como provider principal (com spend limit setado).
- **Sem RAG via PDFs nesta v1** — system prompt do chat = `briefing.md` + `lp-config.json`. Upload de docs vira RAG no Setup 10+.
- **Rate limit Gemini grátis (1500 req/dia)** — Worker cap 800/dia por LP + auto-fallback Claude SDK + canned response previnem quebra silenciosa.

## Troubleshooting & docs

- `docs/troubleshooting.md` — erros comuns por etapa
- `docs/seguranca.md` — modelo de auth (LP_TOKEN admin vs CORS público) e boas práticas
- `docs/metricas-conversao.md` — Cloudflare Web Analytics + UTM tracking

## Suporte

Mentoria semanal ZX Control: https://zxlab.com.br/mission-control

Repo público: https://github.com/zxmarketingdigital/zx-control-setup9-lp-builder-cro
