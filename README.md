# ZX Control — Setup 9: LP Builder Profissional + Mini CRM + Chat IA

Setup oficial da Semana 9 do ZX Control Scale. Pare de entregar template genérico ao cliente. Crie LP profissional, capture leads e atenda dúvidas com IA — tudo no Cloudflare grátis.

## Pré-requisitos

- macOS (Linux/Windows funcionam parcialmente — sem LaunchAgents)
- Setup 8 do ZX Control concluído (`phase_completed >= 8` em `~/.operacao-ia/config/config.json`)
- Python 3.9+
- Claude Code instalado e configurado
- {'recurso': 'Conta Cloudflare grátis', 'pra_que_serve': 'Hospedar LP + Worker + D1', 'como_obtem': 'wrangler login abre browser, aluno cria conta se não tiver'}
- {'recurso': 'Gemini API key', 'pra_que_serve': 'Chat IA default (grátis)', 'como_obtem': 'aistudio.google.com → Get API key → criar (1500 req/dia grátis)'}
- {'recurso': 'Claude API key (opcional)', 'pra_que_serve': 'Fallback premium do chat IA', 'como_obtem': 'console.anthropic.com → SETAR SPEND LIMIT antes de criar key'}
- {'recurso': 'Node 18+ ou bun', 'pra_que_serve': 'Build LP estática + dev server', 'como_obtem': 'brew install bun'}
- {'recurso': 'Python 3.10+', 'pra_que_serve': 'Rodar setup/setup_*.py', 'como_obtem': 'Vem com macOS ou brew install python'}

## Instalação

```bash
git clone https://github.com/zxmarketingdigital/lp-builder-cro
cd lp-builder-cro
claude
```

Ao abrir o Claude, ele vai aguardar você digitar **`INICIAR SETUP SEMANA 9`** para começar.

A partir daí o setup é guiado — 9 etapas, cada uma com explicação + execução + validação.

## O que será instalado

- **Cloudflare (Worker + D1 + Pages)** — Infra serverless grátis pra LP + captura de leads + chat IA
- **Vite + Tailwind CDN** — Build estático rápido da LP
- **4 skills locais embedadas** — /revisar-copy-lp, /clonar-lp, /exportar-leads-csv, /analisar-leads-crm
- **3 skills de design (cópias locais)** — /huashu-design, /design-md, /lp-from-design-md — só ativas neste repo, não global
- **Cloudflare Web Analytics + UTM tracking** — Métricas de conversão sem cookie consent


## Estrutura

```
lp-builder-cro/
├─ CLAUDE.md            # roteiro de instalação (lido pelo Claude Code)
├─ MASTERCLASS.md       # roteiro da aula em vídeo
├─ setup/               # scripts Python das etapas
├─ skills/              # SKILL.md (se aplicável)
├─ scripts/             # automações pós-setup
├─ docs/                # dashboard local (opcional)
└─ launchagents/        # plists macOS (opcional)
```

## Comandos pós-instalação

```
/revisar-copy-lp            Audita copy contra checklist CRO
/clonar-lp                  Duplica LP existente pra novo cliente em 15min
/exportar-leads-csv         Export leads em CSV pra entregar ao cliente
/analisar-leads-crm         Diagnostica leads parados, sugere follow-up por UTM source

```

## Limitações conhecidas

- **D1 region us-east**: Latência ~200-400ms BR. Pra Setup 10+ avaliamos Hyperdrive ou region pinning quando disponível.
- **Gemini PT-BR < Claude em copy persuasiva**: Pra chat IA premium, use Claude SDK como provider principal (com spend limit setado).
- **Sem RAG via PDFs nesta v1**: System prompt do chat = briefing.md + lp-config.json. Upload de docs vira RAG no Setup 10+.
- **Rate limit Gemini grátis (1500 req/dia)**: Worker cap 800/dia por LP + auto-fallback Claude SDK + canned response previnem quebra silenciosa.


## Suporte

Mentoria semanal ZX Control: https://zxlab.com.br/mission-control