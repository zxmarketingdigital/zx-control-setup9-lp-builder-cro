# Provedores de Chat IA — Setup 9

O Worker do Setup 9 suporta 3 provedores de IA pro chat da LP, com fallback automático: **Groq → Gemini → Claude → canned**. Você configura no `setup_chat_ia.py` (etapa 7) — pode usar só 1 ou combinar pra redundância.

## Comparativo rápido

| Provider | Modelo padrão | Quem é | Quando escolher |
|---|---|---|---|
| **Groq** ⭐ | Llama 3.3 70B (Meta) | Inferência ultra-rápida em hardware próprio | Default. Grátis sem cartão, mais cota que Gemini, latência <500ms |
| **Gemini** | gemini-2.0-flash | Google AI Studio | Se já tem chave Google e prefere stack Google |
| **Claude** | Haiku 4.5 (atual) | Anthropic | Quando qualidade > custo (PT-BR superior, respostas mais comerciais) |

> ⚠️ **Quotas e preços mudam.** Não documentamos aqui pra não desatualizar.
> Consulte a billing console do provider escolhido + o agregador
> [artificialanalysis.ai](https://artificialanalysis.ai/) pra comparativo vivo.

## Onde criar a key

- **Groq**: https://console.groq.com/keys (login com Google, 30s)
- **Gemini**: https://aistudio.google.com → "Get API key"
- **Claude**: https://console.anthropic.com/settings/keys — **defina spend limit antes** em Settings → Limits

## Como configurar

```bash
python3 setup/setup_chat_ia.py
# Escolha 1 (Groq), 2 (Gemini), 3 (Claude) ou 4 (pular)
# Cole a key — script valida via GET /models (não consome quota) e grava como secret no Worker
```

Pra trocar de provider depois: rode o mesmo script de novo, escolha outro. O Worker tenta na ordem: Groq → Gemini → Claude → canned. Se você só tem Groq configurado e ele falhar (rate limit, indisponibilidade), cai pro fallback genérico ("Estou com alta demanda, fale com a equipe…").

## Combinar providers (redundância)

Pode setar múltiplos secrets no Worker:

```bash
echo "gsk_..." | wrangler secret put GROQ_API_KEY     --cwd cloudflare/worker
echo "sk-ant-..." | wrangler secret put ANTHROPIC_API_KEY --cwd cloudflare/worker
```

O Worker tenta Groq primeiro; se 5xx/429, tenta Claude; se Claude tbm falhar, canned. Custo zero em condições normais, mas robustez quando um provider tem incidente.

## Cobrança

- **Groq + Gemini**: free tier suficiente pra LPs com <500 visitantes/dia. Acima disso, leia billing console pra confirmar.
- **Claude**: 100% pago. Defina spend limit no console antes de subir pra produção — `setup_chat_ia.py` exige confirmação.

## Trocar modelo padrão

Edite `cloudflare/worker/src/chat-adapter.ts`:
- Groq: `model: "llama-3.3-70b-versatile"` → veja https://console.groq.com/docs/models
- Gemini: `models/gemini-2.0-flash` → veja https://ai.google.dev/gemini-api/docs/models
- Claude: `claude-haiku-4-5-20251001` → veja https://docs.claude.com/en/docs/about-claude/models

Depois `cd cloudflare/worker && wrangler deploy`.
