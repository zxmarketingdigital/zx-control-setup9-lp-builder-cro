#!/usr/bin/env python3
"""Setup 9 — Etapa 5: Cloudflare setup (D1 + Worker) ou --local-only.

Modo local-only: cria SQLite local com schema.
Modo full: wrangler login → d1 create → schema apply → INSERT lp_configs
→ wrangler secret put LP_TOKEN → wrangler deploy → smoke /health.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

from setup_base import (
    OPERACAO_IA,
    ensure_dirs,
    ensure_env_file,
    load_env,
    progress_banner,
    save_env,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
LP_DIR = REPO_ROOT / "lp-template"
CONFIG_JSON = LP_DIR / "lp-config.json"
CLOUDFLARE_DIR = REPO_ROOT / "cloudflare"
WORKER_DIR = CLOUDFLARE_DIR / "worker"
WRANGLER_TOML = WORKER_DIR / "wrangler.toml"
SCHEMA_SQL = WORKER_DIR / "schema.sql"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


def _run(cmd: list, cwd: Optional[Path] = None, input_text: Optional[str] = None, check: bool = True) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=check,
        capture_output=True,
        text=True,
        input=input_text,
    )


def modo_local_only(cfg: dict) -> int:
    lp_id = cfg.get("id")
    if not lp_id:
        print("❌ lp_config_id não encontrado. Rode setup_lp_build.py primeiro.")
        return 1
    lp_db_dir = OPERACAO_IA / "lps" / lp_id
    lp_db_dir.mkdir(parents=True, exist_ok=True)
    db_path = lp_db_dir / "local.db"

    if not SCHEMA_SQL.exists():
        print(f"❌ {SCHEMA_SQL} não existe. Repo incompleto.")
        return 1

    schema = SCHEMA_SQL.read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()

    print(f"✅ SQLite local criado em {db_path}")
    save_env({"LOCAL_ONLY": "true", "LOCAL_DB_PATH": str(db_path)})
    print("\n➡️  Pra servir a LP localmente:")
    print("    cd lp-template/dist && python3 -m http.server 5173")
    print("\n➡️  Próximo passo: python3 setup/setup_minicrm.py")
    return 0


def _wrangler_ok() -> bool:
    if not _which("wrangler"):
        print("❌ wrangler CLI não encontrado. Instale com: npm install -g wrangler")
        return False
    result = subprocess.run(["wrangler", "whoami"], capture_output=True, text=True)
    if result.returncode != 0 or "not authenticated" in (result.stdout + result.stderr).lower():
        print("⚠️  Você não está logado no Cloudflare.")
        print("   Rode em outro terminal: wrangler login")
        input("   Depois volte e aperte ENTER (ou digite 'ok'): ")
        result = subprocess.run(["wrangler", "whoami"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Ainda não autenticado. Saindo.")
            return False
    print(f"✅ Wrangler OK — {result.stdout.strip().splitlines()[-1] if result.stdout else 'autenticado'}")
    return True


def _d1_create_or_reuse() -> Optional[str]:
    toml_text = WRANGLER_TOML.read_text(encoding="utf-8") if WRANGLER_TOML.exists() else ""
    m = re.search(r'database_id\s*=\s*"([0-9a-f-]{36})"', toml_text)
    if m:
        print(f"♻️  D1 já configurado em wrangler.toml: {m.group(1)}")
        return m.group(1)

    try:
        result = _run(["wrangler", "d1", "create", "lp-builder-db"], cwd=WORKER_DIR, check=False)
    except FileNotFoundError:
        print("❌ wrangler não encontrado.")
        return None
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0 and "already exists" not in output.lower():
        print(f"❌ Erro ao criar D1: {output[-500:]}")
        return None
    m = re.search(r'database_id\s*=\s*"([0-9a-f-]{36})"', output)
    if not m:
        m = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", output)
    if not m:
        print("❌ Não consegui capturar database_id do output do wrangler.")
        print(output[-800:])
        return None
    return m.group(1)


def _patch_wrangler_toml(database_id: str) -> None:
    text = WRANGLER_TOML.read_text(encoding="utf-8")
    text = text.replace("PREENCHIDO_PELO_SETUP_CLOUDFLARE_PY", database_id)
    WRANGLER_TOML.write_text(text, encoding="utf-8")


_NAME_SAFE_RE = re.compile(r"[^A-Za-z0-9 ._\-]")
_UUID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


def _sanitize_name(value: str) -> str:
    """Whitelist rígido — só [A-Za-z0-9 ._-]. Resto é removido."""
    return _NAME_SAFE_RE.sub("", value or "").strip()[:120]


def _sanitize_allowed_origins(origins) -> str:
    """Valida cada origin como hostname/URL básico e re-serializa como JSON."""
    if isinstance(origins, str):
        try:
            parsed = json.loads(origins)
        except json.JSONDecodeError:
            parsed = [o.strip() for o in origins.split(",") if o.strip()]
    else:
        parsed = list(origins or [])

    clean = []
    for raw in parsed:
        s = str(raw).strip()
        # Aceita http://localhost:5173, https://foo.com, foo.com, *.foo.com
        if not s:
            continue
        if re.match(r"^[A-Za-z0-9.:_/\-*]+$", s):
            clean.append(s)
    return json.dumps(clean, ensure_ascii=False)


def _stable_owner_id(seed: str) -> str:
    """16 chars hex de sha256 (estável entre runs, ao contrário de hash())."""
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def modo_full(cfg: dict, env: dict) -> int:
    if not WRANGLER_TOML.exists() or not SCHEMA_SQL.exists():
        print(f"❌ Estrutura cloudflare/worker/ incompleta. wrangler.toml/schema.sql faltando.")
        return 1
    if not _wrangler_ok():
        return 1

    db_id = _d1_create_or_reuse()
    if not db_id:
        return 1
    _patch_wrangler_toml(db_id)
    print(f"✅ D1 database_id: {db_id}")

    schema_remote = _run(["wrangler", "d1", "execute", "lp-builder-db", "--remote", f"--file={SCHEMA_SQL}"], cwd=WORKER_DIR, check=False)
    if schema_remote.returncode != 0 and "already exists" not in (schema_remote.stdout + schema_remote.stderr).lower():
        print(f"⚠️  Schema apply teve warnings: {(schema_remote.stderr or '')[-300:]}")

    lp_config_id = cfg.get("id", "")
    if not _UUID_RE.match(lp_config_id):
        print(f"❌ lp_config_id inválido (esperado [A-Za-z0-9_-]{{1,64}}): {lp_config_id!r}")
        return 1

    owner_id = _stable_owner_id(env.get("LP_TOKEN", "") + lp_config_id)
    if not _UUID_RE.match(owner_id):
        print(f"❌ owner_id sanitização falhou: {owner_id!r}")
        return 1

    nome = _sanitize_name(cfg.get("name", ""))
    if not nome:
        print("❌ name do cliente vazio após sanitização. Rode setup_briefing.py.")
        return 1

    origins_json = _sanitize_allowed_origins(cfg.get("allowed_origins", []))

    # Monta SQL em arquivo temporário com escape de SQLite (aspas dobradas).
    # Nome/origins já passaram por whitelist; agora só escapar aspa simples.
    def _q(s: str) -> str:
        return s.replace("'", "''")

    sql_text = (
        f"INSERT OR REPLACE INTO lp_configs (id, owner_id, name, allowed_origins, daily_limit) "
        f"VALUES ('{_q(lp_config_id)}', '{_q(owner_id)}', '{_q(nome)}', '{_q(origins_json)}', 800);\n"
    )

    with tempfile.NamedTemporaryFile(
        "w", suffix=".sql", delete=False, dir=str(WORKER_DIR), encoding="utf-8"
    ) as tmp:
        tmp.write(sql_text)
        tmp_path = Path(tmp.name)

    try:
        ins = _run(
            ["wrangler", "d1", "execute", "lp-builder-db", "--remote", f"--file={tmp_path.name}"],
            cwd=WORKER_DIR,
            check=False,
        )
        if ins.returncode != 0:
            print(f"⚠️  INSERT lp_configs warning: {(ins.stderr or '')[-300:]}")
        else:
            print(f"✅ lp_configs row inserida (id={lp_config_id})")
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass

    lp_token = env.get("LP_TOKEN", "")
    if not lp_token:
        print("❌ LP_TOKEN ausente no env. Rode setup_lp_build.py primeiro.")
        return 1
    secret = _run(["wrangler", "secret", "put", "LP_TOKEN"], cwd=WORKER_DIR, input_text=lp_token + "\n", check=False)
    if secret.returncode != 0:
        print(f"⚠️  Secret put warning: {(secret.stderr or '')[-300:]}")
    else:
        print("✅ Secret LP_TOKEN gravado no Worker")

    deploy = _run(["wrangler", "deploy"], cwd=WORKER_DIR, check=False)
    output = (deploy.stdout or "") + (deploy.stderr or "")
    if deploy.returncode != 0:
        print(f"❌ Deploy falhou: {output[-600:]}")
        return 1
    m = re.search(r"https://[a-z0-9-]+\.[a-z0-9-]+\.workers\.dev", output)
    worker_url = m.group(0) if m else ""
    if worker_url:
        print(f"✅ Worker deployed: {worker_url}")
    else:
        print("⚠️  Não capturei URL do worker no output. Verifique manualmente.")

    if worker_url:
        time.sleep(2)
        health = subprocess.run(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", f"{worker_url}/health"], capture_output=True, text=True)
        if health.stdout.strip() == "200":
            print("✅ /health retornou 200 OK")
        else:
            print(f"⚠️  /health retornou HTTP {health.stdout.strip()} — verifique.")

    save_env({
        "WORKER_URL": worker_url,
        "D1_DATABASE_ID": db_id,
        "LOCAL_ONLY": "false",
    })
    print()
    print("📋 Resumo:")
    print(f"   Worker URL: {worker_url or '(verificar)'}")
    print(f"   D1 ID:      {db_id}")
    print("\n➡️  Próximo passo: python3 setup/setup_minicrm.py")
    return 0


def main() -> int:
    ensure_dirs()
    ensure_env_file()
    progress_banner(5, 8, "Cloudflare setup")

    cfg = _read_json(CONFIG_JSON)
    env = load_env()
    if not cfg.get("id"):
        print("❌ lp-config.json sem id. Rode setup_lp_build.py primeiro.")
        return 1

    print("Modo de execução:")
    print("  1) full        (Cloudflare D1 + Worker — recomendado)")
    print("  2) local-only  (SQLite local, sem Cloudflare)")
    escolha = input("Escolha [1/2]: ").strip()

    if escolha == "2":
        return modo_local_only(cfg)
    if escolha == "1":
        return modo_full(cfg, env)
    print("❌ Escolha inválida.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
