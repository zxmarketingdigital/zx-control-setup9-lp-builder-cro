# MasterClass — Setup 9: LP Builder Profissional + Mini CRM + Chat IA

Roteiro da aula em vídeo gravada pelo Rafael. Cortes referenciados por timestamp + GUID Bunny (preenchido após upload).

## Bunny Library

`Library ID: 629692`

## Estrutura geral (duração estimada: 50min)

1. **Hook de abertura** (00:00 — 00:15)
2. **Visão geral do setup** (00:15 — 00:05:00)
3. **Demo da instalação** (00:05:00 — 00:13:00)
4. **Walkthrough das 8 etapas** (00:13:00 — 00:31:00)
5. **Fechamento + próximos passos** (00:31:00 — final)

## Cortes (atualizar com BUNNY_GUID após upload)

| # | Título | Start | End | Bunny GUID |
|---|--------|-------|-----|------------|
| 1 | Hook + visão geral | 00:00 | 09:06 | `0dc06fe0-02e8-4e93-bf51-fa6a1386c2f2` |
| 2 | Demo: briefing → DS → LP → Cloudflare | 09:06 | 37:28 | `c408d82c-f073-4b66-a984-961d503d53c5` |
| 3 | Chat IA + publicação | 37:28 | 49:29 | `346d14f7-e573-47fe-b652-310560aa144f` |
| 4 | Skill revisão + dry run | 49:29 | 1:10:10 | `ec6c94aa-c313-4e80-8c0c-a6656d3f9314` |
| 5 | Cota Gemini + fixes + Q&A | 1:10:10 | 1:30:12 | `a6d7d906-4a6a-4c03-9bc2-8862e94aa5e5` |
| 6 | Performance + fechamento | 1:30:12 | 1:41:57 | `aeeb4317-1f6f-40d7-92d9-b48ec74257ff` |


## Roteiro

### Hook (00:00 — 00:15)

> Pare de entregar template genérico. Bora montar LP de verdade em 40 minutos?

### Visão geral (00:15 — 00:05:00)

O ZX Flow nos ensinou captura + chat IA. Setup 9 dá o passo que faltava: a LP profissional em si — briefing rico, design system definido, copy de alta conversão, métricas integradas. Tudo no Cloudflare grátis, com auto-fallback Gemini→Claude no chat. Pro próximo cliente, clonar em 15min.

**Pontos a tocar:**
- Por que template genérico não vende e LP profissional vende
- Briefing rico em 2 modos: rápido (5 nichos pré-fab) e profundo (autosave retomável)
- Design system definido ANTES do código + skills locais embedadas
- Worker com auth + CORS + rate limit + streaming SSE + auto-fallback
- Mini CRM como rota /crm da própria LP (sem React separado)
- Métricas reais de conversão (CF Web Analytics + UTM tracking)
- Caso de uso: cobrar R$1500-3000 por LP do cliente final


### Demo da instalação (00:05:00 — 00:13:00)

Demonstrar o aluno abrindo terminal, executando `git clone` + `claude`, e o Claude começando o setup.

**Frases-chave:**
- "Olha como é simples — você clona, abre o Claude, e ele faz tudo."
- "Não precisa digitar comando nenhum a mais — o Claude conduz."

### Walkthrough das etapas (00:13:00 — 00:31:00)


#### Etapa 1 — Briefing do cliente

- **O que mostra:** Escolha entre modo rápido (5 nichos pré-fabricados) ou modo profundo (10 perguntas com autosave retomável).
- **Frase-chave:** "Antes de qualquer linha de código, a gente entende quem é o cliente e o que ele vende."
- **Duração estimada:** 3min


#### Etapa 2 — Design System

- **O que mostra:** Defina paleta, tipografia e radius em 1 minuto — 5 arquétipos prontos ou customizado via skills locais (/huashu-design, /design-md).
- **Frase-chave:** "O visual já sai definido aqui — depois é só o código consumir essas variáveis."
- **Duração estimada:** 2min


#### Etapa 3 — Copy alta conversão

- **O que mostra:** Aluno escolhe framework (PAS / AIDA / BAB), pede pro Claude escrever cada seção (hero, features, objeções, FAQ, CTA) baseado no briefing, e ajusta o que quiser.
- **Frase-chave:** "Aqui é onde a LP deixa de parecer template e vira oferta real."
- **Duração estimada:** 4min


#### Etapa 4 — LP build

- **O que mostra:** O script gera LP_TOKEN único, monta `lp-public.json` sem segredos, instala deps (bun → npm fallback) e roda o build do Vite.
- **Frase-chave:** "A LP estática fica pronta — preview em localhost:5173, código limpinho pra deploy."
- **Duração estimada:** 2min


#### Etapa 5 — Cloudflare setup (ou --local-only)

- **O que mostra:** wrangler login no browser, D1 criado, schema aplicado, secret LP_TOKEN gravado, Worker deployed, /health smoke 200.
- **Frase-chave:** "Tudo no plano grátis da Cloudflare — ninguém te cobra R$ pra capturar lead nem rodar o chat."
- **Duração estimada:** 3min


#### Etapa 6 — Mini CRM

- **O que mostra:** Acessar `<URL>/crm.html`, colar lp_token, ver leads em tempo real, filtrar por status (novo / em_conversa / qualificado / converteu / abandonou), exportar CSV.
- **Frase-chave:** "O CRM é a própria LP — uma rota /crm.html com token. Sem React separado, sem painel terceiro."
- **Duração estimada:** 3min


#### Etapa 7 — Chat IA

- **O que mostra:** Aluno cola Gemini API key (grátis), script grava como secret no Worker, smoke test envia "Olá" pro /chat-ia, streaming SSE volta. Fallback Claude se Gemini quebrar.
- **Frase-chave:** "O chat tira dúvida do visitante 24/7 — sem você responder mensagem na madrugada."
- **Duração estimada:** 3min


#### Etapa 8 — Deploy + métricas

- **O que mostra:** Cloudflare Web Analytics opcional, `wrangler pages deploy ./dist`, URL `.pages.dev`, smoke E2E (LP 200 + CORS no Worker), banner final com URLs.
- **Frase-chave:** "Em ~40 minutos a LP está no ar com captura, CRM e chat IA — tudo medindo conversão."
- **Duração estimada:** 2min



### Fechamento (00:31:00 — final)

> Pronto! Setup 9 instalado. Próxima semana a gente solta o Setup 10. Bons agentes!

**CTA único:**
> "Qualquer dúvida fala no grupo. Próximo setup em ~7 dias."

NUNCA mencionar preço, White Label, versão anterior, ou outro produto.

---

## Upload checklist

Após gravar e cortar:

- [ ] Cortes salvos em `~/Movies/setup9-cortes/`
- [ ] Upload Bunny: `/cortar-aula-setup --gravacao /path/setup9.mp4 --setup 9`
- [ ] BUNNY_GUIDs preenchidos nesta tabela (substituir `BUNNY_GUID_S9_C*`)
- [ ] Commit + push do MASTERCLASS.md atualizado
- [ ] Painel S9-0 das áreas de membros atualizado com GUIDs reais
- [ ] Re-deploy CF Pages das turmas-alvo
