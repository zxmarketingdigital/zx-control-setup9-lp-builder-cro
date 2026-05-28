#!/usr/bin/env python3
"""scripts/lib.py — helpers compartilhados pelos scripts de setup."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional


REPO_ROOT = Path(__file__).resolve().parent.parent
LP_TEMPLATE = REPO_ROOT / "lp-template"
WORKER_DIR = REPO_ROOT / "cloudflare" / "worker"


def run_cmd(
    cmd: list,
    cwd: Optional[Path] = None,
    check: bool = True,
    capture: bool = True,
    stdin_input: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """Wrap subprocess.run com defaults sensatos."""
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=check,
        capture_output=capture,
        text=True,
        input=stdin_input,
    )


def confirm(question: str, default: bool = False) -> bool:
    """Pergunta sim/não com default."""
    suffix = " [S/n]" if default else " [s/N]"
    resp = input(f"{question}{suffix}: ").strip().lower()
    if not resp:
        return default
    return resp in ("s", "sim", "y", "yes")


def read_lp_config(path: Optional[Path] = None) -> dict:
    """Lê lp-template/lp-config.json. Retorna dict vazio se não existe."""
    p = path or (LP_TEMPLATE / "lp-config.json")
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def write_lp_config(data: dict, path: Optional[Path] = None) -> Path:
    """Escreve lp-template/lp-config.json com indent=2."""
    p = path or (LP_TEMPLATE / "lp-config.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def update_lp_config(updates: dict) -> dict:
    """Merge shallow + escreve. Retorna config atualizado."""
    current = read_lp_config()
    current.update(updates)
    write_lp_config(current)
    return current


def cmd_exists(cmd: str) -> bool:
    """True se comando está no PATH."""
    try:
        subprocess.run(
            ["which", cmd],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def fail(msg: str, code: int = 1) -> "Any":
    """Print erro e exit."""
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(code)


def ok(msg: str) -> None:
    """Print sucesso."""
    print(f"✅ {msg}")


def warn(msg: str) -> None:
    """Print warning."""
    print(f"⚠️  {msg}")


def info(msg: str) -> None:
    """Print info."""
    print(f"ℹ️  {msg}")


def sanitize_slug(text: str) -> str:
    """Converte texto livre em slug kebab-case ASCII."""
    s = text.lower().strip()
    s = re.sub(r"[áàâãä]", "a", s)
    s = re.sub(r"[éèêë]", "e", s)
    s = re.sub(r"[íìîï]", "i", s)
    s = re.sub(r"[óòôõö]", "o", s)
    s = re.sub(r"[úùûü]", "u", s)
    s = re.sub(r"[ç]", "c", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    return s or "lp"
