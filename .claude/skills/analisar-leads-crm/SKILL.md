---
name: analisar-leads-crm
description: Diagnostica leads do Mini CRM do Setup 9 — identifica leads parados (sem follow-up), agrupa por UTM source, calcula conversão e sugere mensagem de retomada por canal. Use SEMPRE que o aluno disser "analisar leads", "leads parados", "como retomar contato", "qual canal converte mais", "diagnóstico do CRM", "como tá o funil".
model: sonnet
effort: medium
---

# /analisar-leads-crm

Diagnostica o Mini CRM da LP do Setup 9: leads parados, breakdown UTM, conversão e sugestões de follow-up.

## Quando usar

Aluno (ou cliente do aluno) quer entender:
- Quais leads estão parados há muito tempo
- Qual UTM source converte melhor
- Como retomar contato com leads em `em_conversa` que não evoluíram
- Conversão geral da LP (captures / pageviews)

## Como funciona

1. Lista LPs disponíveis (varre `~/.operacao-ia/lps/*/lp-config.json`)
2. Pergunta qual analisar (ou auto se tem só 1)
3. Faz `GET {worker_url}/leads?lp_id={id}` com paginação até esgotar
4. (Opcional) Puxa Cloudflare Web Analytics via API se TOKEN disponível em env (pageviews/visitantes)
5. Análise:
   - **Leads parados:** status `em_conversa` há mais de 7 dias sem update → flag pra retomada
   - **Funil:** counts por status (novo → em_conversa → qualificado → converteu/abandonou)
   - **Conversão por UTM source:** breakdown de `converteu` por canal
   - **ROI implícito:** se UTM tem custo (futuro: integrar Meta ADS via skill `/meta-metrics-fetcher`), calcula CPL
6. Pra cada lead parado, sugere mensagem de retomada **personalizada por canal**:
   - WhatsApp (mais íntimo): tom acolhedor, 1 pergunta aberta
   - Email (mais formal): assunto curto, 3 linhas, CTA marcar call

## Output

```
📊 Análise CRM — "Estúdio Camélia"
═══════════════════════════════════════

PERÍODO: últimos 30 dias

FUNIL
  Pageviews:        2,341 (CF Analytics)
  Captures:           127 (5.4% conversão)
  novo:                78
  em_conversa:         29
  qualificado:         12  ← 9.4% dos captures
  converteu:            5  ← 3.9% dos captures · CPA implícito não calculado (faltam custos)
  abandonou:            3

LEADS PARADOS (em_conversa há 7+ dias sem update): 11
  Maria Silva       (whatsapp · facebook · há 12d)
  João Pereira      (email · google · há 9d)
  ...

SUGESTÕES DE RETOMADA (Maria Silva como exemplo):
  Canal: WhatsApp
  Mensagem sugerida:
    "Oi Maria! Ainda tô animada pra ajudar com seu projeto.
     Posso tirar uma dúvida que ficou pra trás?"
  Por quê: tom acolhedor, 1 pergunta aberta, lembra contexto sem cobrar.

CONVERSÃO POR UTM SOURCE
  facebook (Meta Ads):  67 leads → 3 converteu (4.5%) ← campeão
  google:               31 leads → 2 converteu (6.5%) ← maior taxa
  instagram_organico:   14 leads → 0 converteu (0%)
  direct (sem UTM):     15 leads → 0 converteu (0%)

INSIGHTS
  ⚠️  instagram_organico atrai volume mas não converte — revisar copy do post?
  ✅ google tem menor volume mas maior taxa — testar aumentar bid
  📈 11 leads em_conversa há 7d+ representam ~R$33k de oportunidade (ticket médio R$3k)

PRÓXIMOS PASSOS
  1. Retomar contato com 11 leads parados (mensagens sugeridas acima)
  2. Investigar conversão zero do instagram_organico
  3. Considerar aumentar bid Google (CPC ainda OK?)
  4. Exportar tudo com /exportar-leads-csv pra entregar pro cliente
```

## Comandos

```bash
/analisar-leads-crm                           # interativo
/analisar-leads-crm --lp {id} --periodo 30d  # rápido
/analisar-leads-crm --parados                 # só leads em_conversa parados
/analisar-leads-crm --utm                     # foco em breakdown UTM
```

## Regras

- NÃO envia mensagens automaticamente — só sugere e aluno decide
- Tom de retomada SEMPRE acolhedor, nunca cobrança
- Conversão calculada: `converteu / captures` (não `converteu / pageviews`)
- Pageviews vêm de CF Analytics se token disponível, senão "n/a"
- Leads parados = `status='em_conversa'` AND `(NOW - updated_at) > 7 dias` (futuro: aceita configurar threshold)
- Quando faltar contexto (custos ADS), explicita "CPA não calculado" em vez de inventar
