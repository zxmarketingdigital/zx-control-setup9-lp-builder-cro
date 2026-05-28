---
name: clonar-lp
description: Duplica LP existente do Setup 9 pra novo cliente em ~15 minutos. Reaproveita briefing + design system + Worker + D1, gera novo lp_config_id + LP_TOKEN. Use SEMPRE que o aluno disser "clonar LP", "duplicar LP", "nova LP pro próximo cliente", "outra LP igual", "copiar essa LP".
model: sonnet
effort: medium
---

# /clonar-lp

Clona uma LP existente do Setup 9 pra um novo cliente reaproveitando estrutura + Worker + D1.

## Quando usar

Aluno já entregou 1 LP pro cliente A com Setup 9 e quer entregar pro cliente B sem refazer briefing/design/copy do zero.

## Como funciona

1. Lista LPs existentes (varre `~/.operacao-ia/lps/*/lp-config.json`)
2. Pergunta qual clonar
3. Pergunta nome do novo cliente + nicho similar/diferente
4. Cria nova pasta `~/.operacao-ia/lps/{novo_id}/` com:
   - `lp-config.json` (cópia adaptada: novo `id`, novo `lp_token`, mesmo `design_system`, novo `name`, novo `allowed_origins[]`)
   - `briefing.md` (cópia editável — aluno ajusta diferenças)
5. **No Worker:** insere nova row em `lp_configs` (mesmo Worker URL, novo `lp_config_id`) via `wrangler d1 execute --remote`
6. **Secrets:** mesmo Worker = mesmo `GEMINI_API_KEY` + `ANTHROPIC_API_KEY`. **Mas LP_TOKEN é por LP** — atualiza secret se necessário (decisão: 1 LP_TOKEN global ou 1 por LP? na v1, 1 por Worker — todas LPs do mesmo Worker compartilham). Veja `cloudflare/worker/src/auth.ts`.
7. Pergunta se quer adaptar copy ou manter:
   - "Manter" → só substitui nome do cliente + CTA principal em todos textos
   - "Adaptar" → roda mini-briefing (3 perguntas: nicho, oferta principal, diferencial) → Claude regenera copy mantendo estrutura
8. Build + deploy CF Pages como novo projeto (`lp-{novo_short}`)
9. Print BANNER com URLs novas

## Comandos

```bash
/clonar-lp                                # interativo (lista + escolhe)
/clonar-lp --de {lp_config_id} --novo "Cliente B"  # direto
/clonar-lp --manter-copy                  # pula adaptação de copy
```

## Output

```
🔁 Clonar LP — origem "Estúdio Camélia" → novo "Boutique Açaí"
═══════════════════════════════════════

✅ Novo lp_config_id: 7a3b...
✅ Novo LP_TOKEN gerado
✅ Row em lp_configs inserida (Worker https://lp-builder-worker.workers.dev)
✅ Copy adaptada (3 ajustes: nome, nicho infoproduto→food, CTA "Cardápio digital")
✅ Build OK (lp-template/dist/)
✅ Deploy: https://lp-boutiqueacai.pages.dev

Tempo: 11min 32s

Próximo: configure custom domain em dash.cloudflare.com (instruções no docs/troubleshooting.md)
```

## Regras

- NUNCA sobrescreve LP original — sempre cria nova
- LP_TOKEN sempre regenerado (UUID4 hex 32)
- Same Worker URL OK (multi-tenant via `lp_config_id`)
- Manter `design_system` por default; adaptar copy se nicho mudou
- Allowed_origins vazio por default — aluno preenche com domínio do novo cliente
