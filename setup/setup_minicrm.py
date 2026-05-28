#!/usr/bin/env python3
"""Setup 9 — Etapa 6: Mini CRM.

Grava WORKER_URL + LP_TOKEN em lp-config.json (privado, gitignored) e
regenera lp-public.json (sem lp_token, servido pela LP). crm.html lê tudo
em runtime via fetch — sem placeholders.
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
PUBLIC_DIR = LP_DIR / "public"
PUBLIC_JSON = PUBLIC_DIR / "lp-public.json"

# Mesma allowlist do setup_lp_build.py — manter sincronizado.
PUBLIC_KEYS = (
    "id",
    "name",
    "design_system",
    "copy",
    "worker_url",
    "allowed_origins",
    "fallback_contact_url",
    "cta_principal",
    "nicho",
)


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _migrate_features(features) -> list:
    """Migra features formato antigo (string[]) pro novo ({icon,title,desc}[]).

    Aluno que rodou setup antes pode ter features como array de strings.
    Template HTML novo (features.html) espera objetos. Esta função:
    - se já é objeto, mantém intacto
    - se é string, split em ':' (título antes, desc depois) ou usa string toda
      como desc com ícone padrão ✨
    """
    if not isinstance(features, list):
        return features
    out = []
    for item in features:
        if isinstance(item, dict):
            out.append(item)
        elif isinstance(item, str):
            text = item.strip()
            if ":" in text:
                title, _, desc = text.partition(":")
                out.append({"icon": "✨", "title": title.strip(), "desc": desc.strip()})
            else:
                # Pega 1ª frase como título, resto como desc.
                first_period = text.find(".")
                if 0 < first_period < 60:
                    title = text[:first_period].strip()
                    desc = text[first_period + 1:].strip() or title
                else:
                    title = text[:60].strip()
                    desc = text
                out.append({"icon": "✨", "title": title, "desc": desc})
        # Outros tipos: descarta (defensive)
    return out


def _write_public_json(cfg: dict) -> None:
    """Merge inteligente: preserva campos existentes em lp-public.json que
    NÃO vêm de lp-config.json (ex: ajustes manuais do aluno em campos extras),
    e atualiza só os campos canônicos. Backup salvo em .bak.
    """
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Ler existente (se houver) e fazer backup.
    existing = _read_json(PUBLIC_JSON) if PUBLIC_JSON.exists() else {}
    if existing:
        backup = PUBLIC_JSON.with_suffix(".json.bak")
        backup.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # 2. Extrair campos canônicos de cfg, migrando features se necessário.
    canonical = {k: cfg[k] for k in PUBLIC_KEYS if k in cfg}
    if isinstance(canonical.get("copy"), dict):
        copy_block = dict(canonical["copy"])
        if "features" in copy_block:
            copy_block["features"] = _migrate_features(copy_block["features"])
        canonical["copy"] = copy_block

    # 3. Merge: existing + canonical override (canonical wins pra campos sobrepostos).
    merged = {**existing, **canonical}

    # 4. Garantia: nunca deixar lp_token vazar.
    merged.pop("lp_token", None)

    PUBLIC_JSON.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


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

    # Merge worker_url + lp_token em lp-config.json (privado, gitignored).
    cfg["worker_url"] = endpoint
    cfg["lp_token"] = lp_token
    _write_json(CONFIG_JSON, cfg)
    print(f"✅ worker_url e lp_token gravados em lp-config.json (token mascarado: {_mascarar(lp_token)})")

    # Regenera lp-public.json com worker_url incluso (mas SEM lp_token).
    _write_public_json(cfg)
    print(f"✅ lp-public.json regenerado em {PUBLIC_JSON} (sem lp_token)")

    if not local_only and endpoint:
        url_leads = f"{endpoint}/leads"
        lp_config_id = cfg.get("id", "")
        try:
            result = subprocess.run(
                [
                    "curl", "-sS",
                    "-H", f"X-LP-Token: {lp_token}",
                    "-H", f"X-LP-Id: {lp_config_id}",
                    f"{url_leads}?lp_id={lp_config_id}",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    data = json.loads(result.stdout)
                    leads = data.get("leads", data) if isinstance(data, dict) else data
                    count = len(leads) if isinstance(leads, list) else "?"
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
