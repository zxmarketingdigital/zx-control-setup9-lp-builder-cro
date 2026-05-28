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
| 1 | Hook + por que LP profissional vence template | 00:00 | 05:00 | `BUNNY_GUID_S9_C1` |
| 2 | Demo end-to-end: briefing → LP publicada em 40min | 05:00 | 13:00 | `BUNNY_GUID_S9_C2` |
| 3 | Walkthrough das 8 etapas no Claude do aluno | 13:00 | 31:00 | `BUNNY_GUID_S9_C3` |
| 4 | Mini CRM + Chat IA com streaming explicados | 31:00 | 41:00 | `BUNNY_GUID_S9_C4` |
| 5 | Casos de uso reais: precificação e venda | 41:00 | 48:00 | `BUNNY_GUID_S9_C5` |
| 6 | Fechamento + /clonar-lp pra próximo cliente | 48:00 | 50:00 | `BUNNY_GUID_S9_C6` |


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

- **O que mostra:** Coleta nicho, oferta, persona, dores, objeções, CTA
- **Frase-chave:** "Aqui o setup coleta nicho, oferta, persona, dores, objeções, cta"
- **Duração estimada:** 2min


#### Etapa 2 — Design System

- **O que mostra:** Define cores + tipografia + espaçamento da LP
- **Frase-chave:** "Aqui o setup define cores + tipografia + espaçamento da lp"
- **Duração estimada:** 2min


#### Etapa 3 — Copy alta conversão

- **O que mostra:** Hero, features, objeções, FAQ, CTA escritos pelo Claude
- **Frase-chave:** "Aqui o setup hero, features, objeções, faq, cta escritos pelo claude"
- **Duração estimada:** 2min


#### Etapa 4 — LP build

- **O que mostra:** Gera HTML/Vite com cores+copy do briefing
- **Frase-chave:** "Aqui o setup gera html/vite com cores+copy do briefing"
- **Duração estimada:** 2min


#### Etapa 5 — Cloudflare setup (ou --local-only)

- **O que mostra:** Login Cloudflare + D1 + Worker + secrets
- **Frase-chave:** "Aqui o setup login cloudflare + d1 + worker + secrets"
- **Duração estimada:** 2min


#### Etapa 6 — Mini CRM

- **O que mostra:** Rota /crm da LP listando leads
- **Frase-chave:** "Aqui o setup rota /crm da lp listando leads"
- **Duração estimada:** 2min


#### Etapa 7 — Chat IA

- **O que mostra:** Configura provider (Gemini grátis ou Claude SDK) + streaming SSE
- **Frase-chave:** "Aqui o setup configura provider (gemini grátis ou claude sdk) + streaming sse"
- **Duração estimada:** 2min


#### Etapa 8 — Deploy + métricas

- **O que mostra:** Publica LP em Cloudflare Pages + ativa Web Analytics + UTM tracking
- **Frase-chave:** "Aqui o setup publica lp em cloudflare pages + ativa web analytics + utm tracking"
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