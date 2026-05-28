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
WORKER_DIR = REPO_ROOT / "cloudflare" / "worker"

# Smoke E2E — payload identificável pra fácil cleanup + reconhecimento humano
SMOKE_LEAD_NAME = "[SETUP-TEST] pode deletar"
SMOKE_LEAD_EMAIL = "setup-test@zxlab.local"


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
    """Faz o deploy e retorna a URL CANÔNICA (sem hash de branch).

    Wrangler imprime URL com hash do deploy (ex: https://abc1234.lp-xxx.pages.dev),
    mas o canonical estável é https://<project_name>.pages.dev — esse que
    o aluno divulga e que vai no allowed_origins.
    """
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
    # Confirmar via output que o deploy completou (não bloqueia se não bater).
    if not re.search(r"https://[a-z0-9-]+\.pages\.dev", out):
        print(f"⚠️  URL .pages.dev não apareceu no output do wrangler. Confira manualmente:\n{out[-400:]}")
    return f"https://{project_name}.pages.dev"


def _http(args: list, timeout: int = 15) -> tuple:
    """curl helper que retorna (status_code_str, body_text). Erro = ('000', '')."""
    try:
        result = subprocess.run(
            ["curl", "-sS", "--max-time", str(timeout), "-w", "\n%{http_code}"] + args,
            capture_output=True, text=True, timeout=timeout + 5,
        )
        out = result.stdout
        if "\n" not in out:
            return ("000", out)
        body, _, code = out.rpartition("\n")
        return (code.strip() or "000", body)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ("000", "")


def _update_allowed_origins(lp_config_id: str, pages_url: str) -> bool:
    """Adiciona pages_url no allowed_origins do lp_configs (via wrangler d1 execute)."""
    if not pages_url:
        return False
    # Lê origins atuais
    sel = subprocess.run(
        ["wrangler", "d1", "execute", "lp-builder-db", "--remote", "--json",
         "--command", f"SELECT allowed_origins FROM lp_configs WHERE id = '{lp_config_id}'"],
        cwd=str(WORKER_DIR), capture_output=True, text=True, timeout=30,
    )
    if sel.returncode != 0:
        print(f"⚠️  SELECT allowed_origins falhou: {(sel.stderr or '')[-200:]}")
        return False
    current = []
    try:
        payload = json.loads(sel.stdout)
        rows = payload[0].get("results", []) if isinstance(payload, list) else payload.get("results", [])
        if rows:
            current = json.loads(rows[0].get("allowed_origins") or "[]")
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        pass
    if pages_url in current:
        print(f"♻️  {pages_url} já está em allowed_origins.")
        return True
    new = list(current) + [pages_url]
    new_json = json.dumps(new, ensure_ascii=False).replace("'", "''")
    upd = subprocess.run(
        ["wrangler", "d1", "execute", "lp-builder-db", "--remote",
         "--command", f"UPDATE lp_configs SET allowed_origins = '{new_json}' WHERE id = '{lp_config_id}'"],
        cwd=str(WORKER_DIR), capture_output=True, text=True, timeout=30,
    )
    if upd.returncode != 0:
        print(f"⚠️  UPDATE allowed_origins falhou: {(upd.stderr or '')[-200:]}")
        return False
    print(f"✅ {pages_url} adicionado em allowed_origins (CORS liberado).")
    return True


def _cleanup_test_lead() -> None:
    """Remove lead de teste do D1 via wrangler d1 (não HTTP — mais robusto)."""
    result = subprocess.run(
        ["wrangler", "d1", "execute", "lp-builder-db", "--remote",
         "--command", f"DELETE FROM leads WHERE email = '{SMOKE_LEAD_EMAIL}'"],
        cwd=str(WORKER_DIR), capture_output=True, text=True, timeout=30,
    )
    if result.returncode == 0:
        print("✅ Lead de teste limpo do D1.")
    else:
        print(f"⚠️  Lead de teste deixado no CRM. Pode deletar manualmente pelo botão 🗑")
        print(f"   (DELETE falhou: {(result.stderr or '')[-150:]})")


def _smoke_pages(pages_url: str, worker_url: str, lp_config_id: str) -> bool:
    """Smoke E2E completo: LP load + capture-lead real + chat-ia stream + cleanup.

    Retorna True se TODOS os testes passarem (200/204 esperados).
    """
    print()
    print("🧪 Smoke E2E (LP + Worker + CRM)")
    all_ok = True

    # 1. LP carrega
    code, _ = _http(["-o", "/dev/null", pages_url + "/"], timeout=15)
    ok1 = code == "200"
    print(f"   {'✅' if ok1 else '❌'} GET {pages_url}/ → HTTP {code}")
    all_ok = all_ok and ok1

    if not worker_url:
        return all_ok

    # 2. CORS preflight /capture-lead
    code, _ = _http([
        "-o", "/dev/null", "-X", "OPTIONS",
        "-H", f"Origin: {pages_url}",
        "-H", "Access-Control-Request-Method: POST",
        "-H", "Access-Control-Request-Headers: content-type, x-lp-id",
        f"{worker_url}/capture-lead?lp_id={lp_config_id}",
    ])
    ok2 = code == "204"
    print(f"   {'✅' if ok2 else '❌'} OPTIONS /capture-lead → HTTP {code} (CORS)")
    all_ok = all_ok and ok2

    # 3. POST /capture-lead real (lead identificável)
    payload = json.dumps({
        "name": SMOKE_LEAD_NAME,
        "email": SMOKE_LEAD_EMAIL,
        "whatsapp": "11999998888",
        "utm_source": "setup-smoke",
    }, ensure_ascii=False)
    code, body = _http([
        "-X", "POST",
        "-H", f"Origin: {pages_url}",
        "-H", f"X-LP-Id: {lp_config_id}",
        "-H", "Content-Type: application/json",
        "-d", payload,
        f"{worker_url}/capture-lead?lp_id={lp_config_id}",
    ])
    ok3 = code == "200" and '"ok":true' in body
    print(f"   {'✅' if ok3 else '❌'} POST /capture-lead → HTTP {code} {'(lead criado)' if ok3 else body[:80]}")
    all_ok = all_ok and ok3

    # 4. POST /chat-ia (msg curta, lê só 1º chunk pra não custar tokens)
    chat_payload = json.dumps({"messages": [{"role": "user", "content": "ping"}]})
    code, body = _http([
        "-X", "POST",
        "-H", f"Origin: {pages_url}",
        "-H", f"X-LP-Id: {lp_config_id}",
        "-H", "Content-Type: application/json",
        "-d", chat_payload,
        "--max-time", "10",
        f"{worker_url}/chat-ia?lp_id={lp_config_id}",
    ], timeout=15)
    ok4 = code == "200" and "data:" in body
    provider = ""
    m = re.search(r'"provider":"([^"]+)"', body)
    if m:
        provider = f" ({m.group(1)})"
    print(f"   {'✅' if ok4 else '❌'} POST /chat-ia → HTTP {code} (SSE stream){provider}")
    all_ok = all_ok and ok4

    # 5. Cleanup
    _cleanup_test_lead()
    return all_ok


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

    # Atualiza allowed_origins no D1 com o domínio canônico .pages.dev
    # — evita ter que rodar setup_cloudflare.py de novo só por causa de CORS.
    if worker_url and lp_config_id:
        _update_allowed_origins(lp_config_id, pages_url)

    time.sleep(2)
    smoke_ok = _smoke_pages(pages_url, worker_url, lp_config_id)
    if not smoke_ok:
        print()
        print("⚠️  Smoke E2E teve falhas. Revise os erros acima antes de divulgar a LP.")
        print("    Possíveis causas: GROQ_API_KEY não configurada, daily_limit estourado,")
        print("    DNS Pages ainda propagando (espera 30s e reabre LP no browser).")

    save_env({"LP_DEPLOYED_URL": pages_url, "DEPLOY_DONE": "true"})
    banner_final(pages_url, worker_url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
