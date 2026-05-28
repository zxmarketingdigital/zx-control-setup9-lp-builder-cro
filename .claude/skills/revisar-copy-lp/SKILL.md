---
name: revisar-copy-lp
description: Audita copy de uma seção da LP contra checklist CRO (hook force, benefícios concretos, CTA único, prova social, objeções respondidas, leitura 5ª série, gatilhos psicológicos). Use SEMPRE que o aluno disser "revisar copy", "auditar LP", "minha copy tá boa?", "checar conversão da copy", "auditoria de copy", "review copy LP".
model: sonnet
effort: medium
---

# /revisar-copy-lp

Audita copy de uma LP gerada pelo Setup 9 contra checklist CRO (Conversion Rate Optimization).

## Quando usar

Aluno terminou de gerar copy na etapa 3 do setup ou editou manualmente `lp-template/lp-config.json` e quer revisão antes do build/deploy.

## Como funciona

1. Lê `lp-template/lp-config.json` no diretório atual ou path passado via `--lp PATH`
2. Roda 7 checks por seção (hero, features, objeções, FAQ, CTA):
   - **Hook force**: headline tem benefício claro nas primeiras 10 palavras? (não usa "Apresentando…" / "Bem-vindos…")
   - **Specifidade**: numérico (R$, %, tempo) presente em ao menos 2 features?
   - **CTA único**: 1 botão CTA dominante por seção (não confunde leitor)?
   - **Prova social**: depoimento/case/número de usuários em algum lugar visível?
   - **Objeções respondidas**: top 3 objeções implícitas têm resposta no FAQ?
   - **Leitura 5ª série**: cada parágrafo <= 30 palavras, voz ativa, evita jargão técnico
   - **Gatilhos psicológicos**: urgência (escassez/prazo) e/ou autoridade (resultados comprovados) presentes?
3. Para cada finding: severity (block/warn/info) + sugestão acionável

## Output

```
🔍 Revisão Copy LP — Estúdio Camélia
═══════════════════════════════════════

HERO
  ✅ Hook force: benefício nas primeiras 8 palavras
  ⚠️  warn: headline tem 14 palavras (ideal ≤10)
       Sugestão: "Da identidade ao site em 2 semanas"

FEATURES (4 itens)
  ✅ Specifidade: "2 semanas", "R$3k" presentes
  ❌ block: feature #3 ("Equipe dedicada") não diz benefício, só recurso
       Sugestão: "Você fala direto com o designer — sem time de atendimento intermediando"

OBJECOES (3 itens)
  ✅ Top 3 objeções cobertas

FAQ (5 itens)
  ⚠️  warn: pergunta #4 tem 42 palavras (alongado)

CTA FINAL
  ✅ CTA único + verbo de ação
  ⚠️  warn: sem urgência explícita
       Sugestão: adicionar "Vagas pra Janeiro estão abrindo"

═══════════════════════════════════════
Score CRO: 7.5/10
Blockers: 1 · Warnings: 4 · OK: 12
```

## Comandos

```bash
/revisar-copy-lp                          # audita lp-template/lp-config.json no cwd
/revisar-copy-lp --lp ../outro/lp-config.json  # audita LP em outro path
/revisar-copy-lp --section hero           # só uma seção
/revisar-copy-lp --apply                  # aplica sugestões interactive (pergunta antes)
```

## Regras

- NÃO reescreva copy completa — só aponte problemas + sugestão curta
- Severity `block` se quebra conversão obvia (CTA confuso, sem prova social, hook fraco)
- NUNCA invente número/depoimento/garantia — só sugira ESPAÇO pra eles
- Score 0-10 é orientativo, não absoluto
