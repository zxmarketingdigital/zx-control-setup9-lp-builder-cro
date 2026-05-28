---
name: exportar-leads-csv
description: Exporta leads do Mini CRM em CSV pra entregar ao cliente. Aceita filtros (status, periodo, UTM). Use SEMPRE que o aluno disser "exportar leads", "leads em CSV", "manda os leads pra ele", "baixar leads", "planilha de leads", "exportar contatos".
model: haiku
effort: low
---

# /exportar-leads-csv

Exporta leads de uma LP do Setup 9 pra CSV.

## Quando usar

Aluno quer entregar relatório de leads pro cliente, ou fazer análise externa (Excel/Sheets), ou subir em outra ferramenta de CRM.

## Como funciona

1. Lista LPs disponíveis (varre `~/.operacao-ia/lps/*/lp-config.json`)
2. Pergunta qual LP exportar
3. Pergunta filtros (interativo):
   - Período: últimos 7d / 30d / desde sempre / range customizado
   - Status: todos / só novos / só qualificados / só converteu
   - UTM source: todos / específica (filtra dropdown)
4. Faz `GET {worker_url}/leads?lp_id={id}&status=...&from=...&to=...` (com paginação até esgotar)
5. Gera CSV com header: `nome,email,whatsapp,status,utm_source,utm_medium,utm_campaign,utm_content,utm_term,data_captura`
6. Salva em `~/Downloads/leads-{lp_name}-{date}.csv` (UTF-8 BOM pra compat Excel)
7. Abre Finder/Explorer no arquivo (Mac: `open -R {path}`)

## Comandos

```bash
/exportar-leads-csv                            # interativo
/exportar-leads-csv --lp {id} --periodo 30d   # rápido
/exportar-leads-csv --status qualificado --utm-source facebook
```

## Output

```
📤 Exportar leads — "Estúdio Camélia"
═══════════════════════════════════════

LP:        Estúdio Camélia (id: a4f3...)
Filtros:   últimos 30 dias, todos os status
Total:     127 leads

✅ Salvo em: ~/Downloads/leads-estudio-camelia-2026-05-28.csv (12.4 KB)

Breakdown:
  novo:              78 (61%)
  em_conversa:       29 (23%)
  qualificado:       12 ( 9%)
  converteu:          5 ( 4%)
  abandonou:          3 ( 2%)

Top UTM source:
  facebook (Meta Ads): 67 (53%)
  google:              31 (24%)
  instagram_organico:  14 (11%)
  outros:              15 (12%)
```

## Regras

- CSV em UTF-8 com BOM (`﻿`) — compatibilidade Excel
- Vírgula como separador (padrão internacional). Pra Excel BR, dica "Importar como UTF-8" inclusa no output
- Campos com vírgula ou quebra de linha entre aspas duplas (RFC 4180)
- Telefone como TEXTO (`="55..."`) pra Excel não cortar leading zero
- NUNCA exporta o `lp_token` ou `lp_config_id` no CSV (são segredos operacionais)
- LGPD: arquivo inclui linha header com "Exportado em {date} — uso conforme política de privacidade da LP"
