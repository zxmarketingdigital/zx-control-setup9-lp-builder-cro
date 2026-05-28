#!/usr/bin/env python3
"""Setup 9 — Etapa 8: Deploy + métricas.

Injeta Cloudflare Web Analytics opcional, cria projeto Pages,
faz deploy do dist/, captura URL pages.dev, roda smoke E2E (LP 200 + CORS).
Modo local-only: instrui aluno a servir local.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
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
DIST_DIR = LP_DIR / "dist"
DIST_INDEX = DIST_DIR / "index.html"


def _short_id(full_id: str) -> str:
    safe = re.sub(r"[^a-z0-9]", "", full_id.lower())
    return safe[:8] or "lp"


def _run(cmd: list, cwd: Optional[Path] = None, check: bool = False, timeout: int = 120) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=check,
        timeout=timeout,
    )


def _inject_analytics(token: str) -> None:
    if not DIST_INDEX.exists():
        return
    snippet = (
        f'<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
        f'data-cf-beacon=\'{{"token": "{token}"}}\'></script>'
    )
    html = DIST_INDEX.read_text(encoding="utf-8")
    if token in html:
        print("ℹ️  Web Analytics já injetado.")
        return
    if "</head>" in html:
        html = html.replace("</head>", f"  {snippet}\n</head>", 1)
    else:
        html = snippet + "\n" + html
    DIST_INDEX.write_text(html, encoding="utf-8")
    print("✅ Cloudflare Web Analytics injetado em dist/index.html")


def modo_local_only() -> int:
    if not DIST_INDEX.exists():
        print(f"❌ {DIST_INDEX} não existe — rode setup_lp_build.py.")
        return 1
    print()
    print("✅ Modo local-only. Pra servir a LP:")
    print(f"   cd {DIST_DIR}")
    print("   python3 -m http.server 5173")
    print()
    print("   Depois abra: http://localhost:5173")
    save_env({"DEPLOY_DONE": "true", "LP_DEPLOYED_URL": "http://localhost:5173"})
    return 0


def _pages_create(project_name: str) -> bool:
    result = _run(["wrangler", "pages", "project", "create", project_name, "--production-branch", "main"], check=False)
    out = (result.stdout or "") + (result.stderr or "")
    if result.returncode == 0:
        print(f"✅ Pages project '{project_name}' criado.")
        return True
    if "already exists" in out.lower():
        print(f"♻️  Pages project '{project_name}' já existe — reaproveitando.")
        return True
    print(f"❌ Falha ao criar project: {out[-400:]}")
    return False


def _pages_deploy(project_name: str) -> Optional[str]:
    result = _run(
        [
            "wrangler", "pages", "deploy", str(DIST_DIR),
            "--project-name", project_name,
            "--branch", "main",
            "--commit-dirty=true",
        ],
        check=False,
        timeout=180,
    )
    out = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        print(f"❌ Deploy Pages falhou: {out[-500:]}")
        return None
    m = re.search(r"https://[a-z0-9-]+\.pages\.dev", out)
    if not m:
        print(f"⚠️  URL .pages.dev não capturada. Output:\n{out[-500:]}")
        return None
    return m.group(0)


def _smoke_pages(pages_url: str, worker_url: str) -> None:
    print()
    print("🧪 Smoke E2E")
    r1 = subprocess.run(
        ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", pages_url + "/"],
        capture_output=True, text=True,
    )
    print(f"   GET {pages_url}/  → HTTP {r1.stdout.strip()}")

    if worker_url:
        r2 = subprocess.run(
            [
                "curl", "-sS", "-X", "OPTIONS",
                "-H", f"Origin: {pages_url}",
                "-H", "Access-Control-Request-Method: POST",
                "-o", "/dev/null", "-w", "%{http_code}",
                f"{worker_url}/capture-lead",
            ],
            capture_output=True, text=True,
        )
        print(f"   OPTIONS {worker_url}/capture-lead → HTTP {r2.stdout.strip()} (CORS)")


def banner_final(lp_url: str, worker_url: str) -> None:
    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  🎉 SETUP 9 COMPLETO!")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"   LP:        {lp_url}")
    print(f"   CRM:       {lp_url}/crm.html")
    print(f"   Worker:    {worker_url or '(local-only)'}")
    print()
    print("   Próximos passos:")
    print("   • Editar copy/design e re-rodar etapas 3/4 → setup_deploy.py")
    print("   • Clonar pro próximo cliente: /clonar-lp")
    print("   • Monitorar leads: abra a URL /crm.html com seu token")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


def main() -> int:
    ensure_dirs()
    ensure_env_file()
    progress_banner(8, 8, "Deploy + métricas")

    env = load_env()
    local_only = env.get("LOCAL_ONLY", "false").lower() == "true"
    if local_only:
        return modo_local_only()

    lp_config_id = env.get("LP_CONFIG_ID", "")
    worker_url = env.get("WORKER_URL", "")
    if not lp_config_id:
        print("❌ LP_CONFIG_ID ausente. Rode setup_lp_build.py.")
        return 1
    if not DIST_INDEX.exists():
        print(f"❌ {DIST_INDEX} não existe — rode setup_lp_build.py.")
        return 1

    print("Ativar Cloudflare Web Analytics? [s/N]:")
    if input().strip().lower() == "s":
        print("Crie um site em: https://dash.cloudflare.com/?to=/:account/web-analytics")
        token = input("Cole o token de Web Analytics (ou ENTER pra pular): ").strip()
        if token:
            _inject_analytics(token)

    print()
    print("Confirma deploy em Cloudflare Pages? [s/N]:")
    if input().strip().lower() != "s":
        print("⏸️  Deploy cancelado pelo usuário.")
        return 0

    project_name = f"lp-{_short_id(lp_config_id)}"
    if not _pages_create(project_name):
        return 1
    pages_url = _pages_deploy(project_name)
    if not pages_url:
        return 1
    print(f"✅ LP deployed: {pages_url}")

    print()
    print("Quer adicionar custom domain agora? [s/N]:")
    if input().strip().lower() == "s":
        print("Configure em: https://dash.cloudflare.com → Workers & Pages → "
              f"{project_name} → Custom domains")
        print("Cole CNAME do seu domínio apontando pra:", pages_url.replace("https://", ""))
        input("Aperte ENTER quando terminar.")

    time.sleep(2)
    _smoke_pages(pages_url, worker_url)

    save_env({"LP_DEPLOYED_URL": pages_url, "DEPLOY_DONE": "true"})
    banner_final(pages_url, worker_url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
