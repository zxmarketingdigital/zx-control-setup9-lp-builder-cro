#!/usr/bin/env python3
"""Setup 9 — Etapa 6: Mini CRM.

Injeta WORKER_URL + LP_TOKEN no crm.html (substitui placeholders).
Smoke: GET /leads no Worker e mostra count. Em modo local-only, usa path local.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from setup_base import (
    ensure_dirs,
    ensure_env_file,
    load_env,
    progress_banner,
    save_env,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
LP_DIR = REPO_ROOT / "lp-template"
CRM_HTML = LP_DIR / "crm.html"
CONFIG_JSON = LP_DIR / "lp-config.json"


PLACEHOLDER_WORKER = "__WORKER_URL__"
PLACEHOLDER_TOKEN = "__LP_TOKEN__"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _mascarar(token: str) -> str:
    if not token:
        return ""
    if len(token) < 10:
        return token[:2] + "…"
    return f"{token[:6]}…{token[-4:]}"


def main() -> int:
    ensure_dirs()
    ensure_env_file()
    progress_banner(6, 8, "Mini CRM")

    if not CRM_HTML.exists():
        print(f"❌ {CRM_HTML} não encontrado. Repo incompleto.")
        return 1

    env = load_env()
    cfg = _read_json(CONFIG_JSON)
    lp_token = env.get("LP_TOKEN", "")
    if not lp_token:
        print("❌ LP_TOKEN ausente. Rode setup_lp_build.py primeiro.")
        return 1

    local_only = env.get("LOCAL_ONLY", "false").lower() == "true"
    if local_only:
        endpoint = "/api"
        print(f"ℹ️  Modo local-only — endpoint relativo {endpoint} (servir via python -m http.server e proxy local)")
    else:
        endpoint = env.get("WORKER_URL", "").strip()
        if not endpoint:
            print("❌ WORKER_URL ausente. Rode setup_cloudflare.py primeiro.")
            return 1
        print(f"ℹ️  Worker URL: {endpoint}")

    html = CRM_HTML.read_text(encoding="utf-8")
    if PLACEHOLDER_WORKER not in html and PLACEHOLDER_TOKEN not in html:
        print(f"⚠️  Placeholders {PLACEHOLDER_WORKER}/{PLACEHOLDER_TOKEN} não encontrados em crm.html. Re-injetando direto.")
    html_novo = html.replace(PLACEHOLDER_WORKER, endpoint).replace(PLACEHOLDER_TOKEN, lp_token)
    CRM_HTML.write_text(html_novo, encoding="utf-8")
    print(f"✅ crm.html injetado com WORKER_URL e LP_TOKEN (token mascarado: {_mascarar(lp_token)})")

    if not local_only and endpoint:
        url_leads = f"{endpoint}/leads"
        try:
            result = subprocess.run(
                ["curl", "-sS", "-H", f"Authorization: Bearer {lp_token}", url_leads],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    data = json.loads(result.stdout)
                    count = len(data) if isinstance(data, list) else data.get("count", "?")
                    print(f"✅ Smoke /leads OK — {count} leads")
                except json.JSONDecodeError:
                    print(f"⚠️  /leads retornou texto não-JSON: {result.stdout[:200]}")
            else:
                print(f"⚠️  /leads falhou: {(result.stderr or result.stdout)[:200]}")
        except subprocess.TimeoutExpired:
            print("⚠️  Timeout na chamada /leads — Worker pode não estar respondendo.")

    save_env({"MINICRM_DONE": "true"})
    print()
    nome = cfg.get("name", "Cliente")
    print(f"✅ Mini CRM pronto pra {nome}.")
    print("   Após deploy (etapa 8), acesse: <URL-LP>/crm.html")
    print("\n➡️  Próximo passo: python3 setup/setup_chat_ia.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
