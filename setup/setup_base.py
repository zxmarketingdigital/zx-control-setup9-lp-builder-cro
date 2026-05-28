#!/usr/bin/env python3
"""Setup 9 — setup_base: cria estrutura de pastas + .env do aluno.

Idempotente: pode rodar várias vezes sem efeito colateral.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional


OPERACAO_IA = Path.home() / ".operacao-ia"
CONFIG_DIR = OPERACAO_IA / "config"
ENV_FILE = CONFIG_DIR / "setup9.env"

SUBDIRETORIOS = ["config", "scripts", "leads", "lps"]


def ensure_dirs() -> None:
    """Cria ~/.operacao-ia/{config,scripts,leads,lps} se faltar."""
    OPERACAO_IA.mkdir(parents=True, exist_ok=True)
    for sub in SUBDIRETORIOS:
        (OPERACAO_IA / sub).mkdir(parents=True, exist_ok=True)


def ensure_env_file() -> Path:
    """Garante que ~/.operacao-ia/config/setup9.env existe (vazio se novo)."""
    if not ENV_FILE.exists():
        template = (
            "# Setup 9 — LP Builder Profissional + Mini CRM + Chat IA\n"
            "# Edite conforme avança pelas etapas. Nunca commitar este arquivo.\n"
            "\n"
            "# Cloudflare (preenchido em setup_cloudflare.py)\n"
            "CLOUDFLARE_ACCOUNT_ID=\n"
            "D1_DATABASE_ID=\n"
            "WORKER_URL=\n"
            "\n"
            "# Chat IA — escolha 1 (preenchido em setup_chat_ia.py)\n"
            "GEMINI_API_KEY=\n"
            "ANTHROPIC_API_KEY=\n"
            "\n"
            "# Token de autenticação por LP (gerado por LP em setup_lp_build.py)\n"
            "LP_TOKEN=\n"
            "\n"
            "# Modo local-only (sem Cloudflare) — true | false\n"
            "LOCAL_ONLY=false\n"
        )
        ENV_FILE.write_text(template, encoding="utf-8")
    return ENV_FILE


def load_env() -> dict:
    """Lê variáveis do setup9.env como dict (sem export)."""
    if not ENV_FILE.exists():
        return {}
    env: dict = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def save_env(updates: dict) -> None:
    """Atualiza chaves no setup9.env preservando comentários e ordem."""
    ensure_env_file()
    existing = ENV_FILE.read_text(encoding="utf-8").splitlines()
    new_lines = []
    handled: set = set()
    for line in existing:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                handled.add(key)
                continue
        new_lines.append(line)
    for key, value in updates.items():
        if key not in handled:
            new_lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def progress_banner(etapa: int, total: int = 8, titulo: str = "") -> None:
    """Banner de progresso visual."""
    pct = int((etapa / total) * 10)
    bar = "█" * pct + "░" * (10 - pct)
    print()
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Setup 9 — Etapa {etapa}/{total}  [{bar}]")
    if titulo:
        print(f"  {titulo}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()


def main() -> int:
    ensure_dirs()
    env_path = ensure_env_file()
    progress_banner(0, 8, "Boas-vindas + setup base")
    print(f"✅ Pastas garantidas em {OPERACAO_IA}")
    print(f"✅ Arquivo de credenciais em {env_path}")
    print()
    print("Próximo passo: rodar setup_briefing.py (etapa 1)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
