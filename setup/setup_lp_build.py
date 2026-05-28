#!/usr/bin/env python3
"""Setup 9 — Etapa 4: LP build.

Valida lp-config.json (design + copy + name), gera LP_TOKEN + lp_config_id,
pede allowed_origins, instala deps (bun ou npm) e roda build.
Smoke check: dist/index.html contém o nome do cliente.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import uuid
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
LP_COMPONENTS_LEGACY = LP_DIR / "components"
LP_PUBLIC_COMPONENTS = LP_DIR / "public" / "components"
CONFIG_JSON = LP_DIR / "lp-config.json"
PUBLIC_DIR = LP_DIR / "public"
PUBLIC_JSON = PUBLIC_DIR / "lp-public.json"
DIST_INDEX = LP_DIR / "dist" / "index.html"
WORKER_DIR = REPO_ROOT / "cloudflare" / "worker"
WORKER_PKG = WORKER_DIR / "package.json"

# Chaves expostas no JSON público (servido pela LP). lp_token NUNCA entra aqui.
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


def _write_public_json(cfg: dict) -> None:
    """Grava lp-template/public/lp-public.json (servido pela LP) sem lp_token."""
    public_cfg = {k: cfg[k] for k in PUBLIC_KEYS if k in cfg}
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_JSON.write_text(
        json.dumps(public_cfg, indent=2, ensure_ascii=False),
        encoding="utf-8",
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


def _which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


def _run(cmd: list, cwd: Path, timeout: int = 300) -> int:
    """Executa subprocess com timeout (default 5min). Sem isso, `bun install`
    em rede flaky/offline pode pendurar indefinidamente."""
    print(f"$ {' '.join(cmd)}  (cwd={cwd})")
    try:
        result = subprocess.run(
            cmd, cwd=cwd, check=True, capture_output=True, text=True, timeout=timeout,
        )
        if result.stdout:
            print(result.stdout.strip()[-500:])
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro em {' '.join(cmd)}:")
        if e.stderr:
            print(e.stderr.strip()[-1000:])
        return e.returncode or 1
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout ({timeout}s) em {' '.join(cmd)} — sem internet?")
        print("    Tente: `bun install` manualmente naquela pasta com a rede OK.")
        return 124


def _migrate_legacy_components() -> None:
    """Defesa pra alunos que clonaram antes do move components/ → public/components/.

    Se a pasta antiga ainda existir e a nova não tiver todos os arquivos,
    copia os faltantes (sem sobrescrever). Não apaga a antiga — aluno faz
    `git rm -r lp-template/components/` depois.
    """
    if not LP_COMPONENTS_LEGACY.exists() or not LP_COMPONENTS_LEGACY.is_dir():
        return
    LP_PUBLIC_COMPONENTS.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src in LP_COMPONENTS_LEGACY.glob("*.html"):
        dst = LP_PUBLIC_COMPONENTS / src.name
        if not dst.exists():
            dst.write_bytes(src.read_bytes())
            copied += 1
    if copied:
        print(f"⚠️  {copied} componentes copiados de lp-template/components/ pra public/components/")
        print("    Apague a pasta antiga: git rm -r lp-template/components/")


def _ensure_worker_deps() -> int:
    """Roda bun/npm install em cloudflare/worker/ — pra hono resolver antes
    do setup_cloudflare.py fazer `wrangler deploy`.

    Skip se node_modules/ já existe (assume install OK de run anterior).
    Aluno pode forçar re-install deletando a pasta manualmente.
    """
    if not WORKER_PKG.exists():
        print(f"⚠️  {WORKER_PKG} não existe — pulando install do worker.")
        return 0
    if not WORKER_DIR.exists():
        return 0
    worker_modules = WORKER_DIR / "node_modules"
    if worker_modules.exists() and (worker_modules / "hono").exists():
        print("♻️  Worker deps já instaladas (node_modules/hono existe) — skip.")
        return 0
    print("📦 Instalando deps do Worker (cloudflare/worker/)...")
    if _which("bun"):
        cmd = ["bun", "install"]
    elif _which("npm"):
        cmd = ["npm", "install"]
    else:
        print("❌ Nem bun nem npm encontrados pro Worker.")
        return 1
    return _run(cmd, WORKER_DIR)


def main() -> int:
    ensure_dirs()
    ensure_env_file()
    progress_banner(4, 8, "LP build")

    # Defesa pós-refactor (commit 98144c2): mover components legacy → public/
    _migrate_legacy_components()

    # Garantir deps do Worker — evita falha em setup_cloudflare.py (hono missing)
    if _ensure_worker_deps() != 0:
        return 1

    cfg = _read_json(CONFIG_JSON)
    faltando = []
    for chave in ("design_system", "copy", "name"):
        if not cfg.get(chave):
            faltando.append(chave)
    if faltando:
        print(f"❌ lp-config.json incompleto. Faltando: {', '.join(faltando)}")
        return 1

    env = load_env()
    lp_token = env.get("LP_TOKEN") or uuid.uuid4().hex
    lp_config_id = cfg.get("id") or str(uuid.uuid4())
    cfg["id"] = lp_config_id
    cfg["lp_token"] = lp_token

    origens = cfg.get("allowed_origins") or []
    if not origens:
        print("Quais domínios vão hospedar essa LP? (pelo menos 1; aceita 'localhost' pra dev)")
        print("Cole separado por espaço (ex: cliente.com.br www.cliente.com.br localhost):")
        raw = input("> ").strip()
        origens = [o for o in raw.split() if o]
        if not origens:
            print("❌ Pelo menos 1 origem é obrigatória.")
            return 1
    cfg["allowed_origins"] = origens
    _write_json(CONFIG_JSON, cfg)

    # JSON público (sem lp_token) — servido pela LP em runtime
    _write_public_json(cfg)
    print(f"✅ lp-public.json gerado em {PUBLIC_JSON} (sem lp_token)")

    if not LP_DIR.exists():
        print(f"❌ Pasta {LP_DIR} não existe — repo incompleto.")
        return 1

    if _which("bun"):
        pm = "bun"
        install_cmd = ["bun", "install"]
        build_cmd = ["bun", "run", "build"]
    elif _which("npm"):
        pm = "npm"
        install_cmd = ["npm", "install"]
        build_cmd = ["npm", "run", "build"]
    else:
        print("❌ Nem bun nem npm encontrados. Instale um deles antes de continuar.")
        return 1

    print(f"📦 Package manager: {pm}")
    if _run(install_cmd, LP_DIR) != 0:
        return 1
    if _run(build_cmd, LP_DIR) != 0:
        return 1

    if not DIST_INDEX.exists():
        print(f"❌ Build não gerou {DIST_INDEX}")
        return 1
    html = DIST_INDEX.read_text(encoding="utf-8", errors="ignore")
    nome = cfg.get("name", "")
    if nome and nome not in html:
        print(f"⚠️  Smoke check: nome '{nome}' não encontrado em {DIST_INDEX.name}. Verifique o template.")
    else:
        print(f"✅ Smoke check OK — {DIST_INDEX.name} contém '{nome}'")

    save_env({
        "LP_BUILT": "true",
        "LP_TOKEN": lp_token,
        "LP_CONFIG_ID": lp_config_id,
    })

    print()
    print(f"✅ LP construída em {LP_DIR / 'dist'}")
    print(f"   Preview local: cd lp-template && {pm} run dev")
    print(f"   LP_TOKEN salvo no env (mascarado): {lp_token[:6]}…{lp_token[-4:]}")
    print(f"   LP_CONFIG_ID: {lp_config_id}")
    print("\n➡️  Próximo passo: python3 setup/setup_cloudflare.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
