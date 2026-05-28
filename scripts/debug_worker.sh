#!/usr/bin/env bash
# scripts/debug_worker.sh — wrapper de `wrangler tail` com filtros úteis
#
# Mostra só logs com ERROR/WARN do Worker em tempo real, ignorando o ruído
# de [GET 200 OK] que enche o terminal.
#
# Uso:
#   ./scripts/debug_worker.sh                 # streaming tudo (ERROR/WARN)
#   ./scripts/debug_worker.sh capture-lead    # filtra só rotas que batem em capture-lead
#   ./scripts/debug_worker.sh chat-ia         # filtra só chat
#
# Requer: jq (já vem com macOS), wrangler logado.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKER_DIR="$REPO_ROOT/cloudflare/worker"
FILTER="${1:-}"

if ! command -v wrangler >/dev/null 2>&1; then
  echo "❌ wrangler não encontrado. Instale: npm install -g wrangler"
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "⚠️  jq não encontrado — output vai vir cru. brew install jq"
  cd "$WORKER_DIR" && exec wrangler tail --format=pretty
fi

cd "$WORKER_DIR"

echo "🔍 Tailing Worker (Ctrl+C pra sair). Filtro: ${FILTER:-tudo}"
echo

wrangler tail --format=json | jq --unbuffered -r --arg filter "$FILTER" '
  # Só interessa eventos com erro ou status 4xx/5xx, ou se filter bater no URL.
  select(
    (.logs[]?.level == "error") or
    (.logs[]?.level == "warn") or
    (.outcome == "exception") or
    (.event.response.status >= 400) or
    ($filter != "" and (.event.request.url | tostring | contains($filter)))
  )
  | "\(.eventTimestamp // .timestamp // "?") [\(.outcome // "?")] \(.event.request.method // "?") \(.event.request.url // "?") → \(.event.response.status // "?")\n  \(.logs[]?.message[]? // "")"
'
