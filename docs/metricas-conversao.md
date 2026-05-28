# Métricas de Conversão — Setup 9

LP do Setup 9 vem com **3 fontes de métrica** integradas. Aluno (ou cliente do aluno) consegue responder "minha LP converte?".

## 1. Cloudflare Web Analytics

**Privacy-first, sem cookie consent, free tier ilimitado.**

Ativado em `setup_deploy.py`. Injeta script tag no `<head>` do `index.html`:

```html
<script defer src='https://static.cloudflareinsights.com/beacon.min.js'
  data-cf-beacon='{"token": "..."}'></script>
```

### O que mede
- Pageviews por URL
- Visitantes únicos
- Países / dispositivos / browsers
- Eventos custom via JS (futuro)

### Onde ver
- dash.cloudflare.com → Analytics & Logs → Web Analytics → Sites → escolha a LP

### Como puxar via API
```bash
curl "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/rum/v2/{site_tag}/visits" \
  -H "Authorization: Bearer $CF_API_TOKEN"
```

A skill `/analisar-leads-crm` faz essa chamada se token disponível.

## 2. UTM Tracking nos leads

UTMs (`utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term`) são parseados client-side e gravados em `leads.utm_*` em cada captura.

### Como funciona
1. Visitante chega na LP com `?utm_source=facebook&utm_campaign=lancamento_jan`
2. JS armazena UTMs em `sessionStorage`
3. Modal de captura inclui UTMs como hidden fields no POST
4. Worker grava em `leads.utm_*`
5. CRM (rota `/crm`) filtra/agrupa por UTM

### Convenções de UTM (sugeridas pro cliente do aluno)

| Param | Exemplo | Como usar |
|-------|---------|-----------|
| `utm_source` | `facebook` `google` `instagram_organico` `direct` | Plataforma de origem |
| `utm_medium` | `ads` `organic` `email` | Tipo de tráfego |
| `utm_campaign` | `lancamento_jan_2026` | Nome da campanha (mesmo nome no Meta/Google) |
| `utm_content` | `video_30s` `carrossel_a` | Variante criativa (pra A/B) |
| `utm_term` | `arquitetura` `decoração` | Keyword (Google Ads) |

## 3. Métricas operacionais do Worker

| Endpoint | O que retorna |
|----------|---------------|
| `GET /health` | `{ok:true, lp_count}` — sanity check |
| `GET /usage` | Counts diários por endpoint (rate limit) |

E tabela `usage_counters` (D1) com histórico.

## Cálculos práticos

### Conversão da LP
```
conversão = captures / pageviews
```

Pra um cliente B2B SaaS típico, esperar 2-8%. Abaixo de 2% = problema (copy, hook, oferta). Acima de 10% = excelente, considerar escalar tráfego.

### CPL (Custo por Lead) — se aluno integrar Meta Ads
```
CPL = gasto_ads / captures
```

A skill `/meta-metrics-fetcher` (Setup 6) puxa gasto. Cruzar com captures por UTM source.

### Funil completo
```
visitantes → captures → qualificados → converteu
```

Conversão por etapa visível em `/analisar-leads-crm`.

### CAC (Custo de Aquisição) — só faz sentido com cliente real
```
CAC = gasto_total / clientes_convertidos
```

Aluno geralmente foca em CPL primeiro; CAC vem em ciclos longos.

## Como aluno entrega métricas ao cliente

1. `/exportar-leads-csv` → planilha de leads
2. `/analisar-leads-crm` → diagnóstico do funil
3. Screenshot CF Web Analytics (manual)

Futuro (Setup 10+): relatório consolidado PDF auto-gerado.

## Limitações conhecidas

- CF Web Analytics não trackeia eventos custom de modal/scroll (só pageviews) na v1
- UTM tracking é client-side — bot tráfego ou ad-blockers podem suprimir
- D1 region us-east → latência ~200-400ms BR pode afetar tempo de captura percebido
