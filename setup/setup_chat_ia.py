#!/usr/bin/env python3
"""Setup 9 — Etapa 7: Chat IA (Gemini grátis ou Claude SDK).

Gemini: passo-a-passo pra criar key no AI Studio.
Claude: exige confirmação de spend limit antes de aceitar key.
Modo full → wrangler secret put. Modo local-only → salva no env.
Smoke: POST /chat-ia com mensagem teste.
"""
from __future__ import annotations

import getpass
import json
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
WORKER_DIR = REPO_ROOT / "cloudflare" / "worker"


def _input_secret(prompt: str) -> str:
    """Lê API key sem ecoar quando possível."""
    try:
        return getpass.getpass(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def _set_secret(secret_name: str, value: str) -> bool:
    if not value:
        return False
    try:
        result = subprocess.run(
            ["wrangler", "secret", "put", secret_name],
            cwd=str(WORKER_DIR),
            input=value + "\n",
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"✅ Secret {secret_name} gravado no Worker.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Falha ao gravar {secret_name}: {(e.stderr or '')[-300:]}")
        return False
    except FileNotFoundError:
        print("❌ wrangler não encontrado.")
        return False


def _smoke_chat(worker_url: str, lp_token: str) -> None:
    if not worker_url:
        print("⚠️  Sem WORKER_URL — pulando smoke do chat.")
        return
    url = f"{worker_url}/chat-ia"
    payload = json.dumps({"messages": [{"role": "user", "content": "Olá, isso é um teste."}]})
    print(f"🧪 Smoke POST {url}")
    try:
        result = subprocess.run(
            [
                "curl", "-sS", "-N", "--max-time", "15",
                "-H", "Content-Type: application/json",
                "-H", f"Authorization: Bearer {lp_token}",
                "-X", "POST", "-d", payload, url,
            ],
            capture_output=True, text=True, check=False, timeout=20,
        )
        body = (result.stdout or "")[:400]
        if result.returncode == 0 and body:
            if "data:" in body or "event:" in body or "content" in body:
                print("✅ Chat respondeu (streaming SSE ou JSON detectado).")
            else:
                print(f"⚠️  Resposta inesperada: {body[:200]}")
        else:
            print(f"⚠️  Smoke falhou: {(result.stderr or result.stdout)[:300]}")
    except subprocess.TimeoutExpired:
        print("⚠️  Timeout no smoke do chat (15s).")


def coletar_gemini() -> str:
    print()
    print("🧠 Provider: Gemini (grátis no AI Studio)")
    print("   Passo-a-passo:")
    print("   1. Abra: https://aistudio.google.com")
    print("   2. Clique em 'Get API key' (canto superior esquerdo)")
    print("   3. Clique em 'Create API key in new project'")
    print("   4. Copie a key (formato AIza…)")
    print()
    return _input_secret("Cole a GEMINI_API_KEY (não vai aparecer enquanto digita): ")


def coletar_claude() -> str:
    print()
    print("🧠 Provider: Claude (Anthropic SDK — pago por uso)")
    print("   ATENÇÃO: antes de criar a key, DEFINA spend limit no console.")
    print("   1. Abra: https://console.anthropic.com")
    print("   2. Settings → Limits → defina spend limit mensal (ex: USD 20)")
    print("   3. Settings → API Keys → Create Key")
    print()
    conf = input("Você JÁ definiu o spend limit? [s/N]: ").strip().lower()
    if conf != "s":
        print("❌ Volte e defina o spend limit antes de continuar.")
        return ""
    return _input_secret("Cole a ANTHROPIC_API_KEY: ")


def main() -> int:
    ensure_dirs()
    ensure_env_file()
    progress_banner(7, 8, "Chat IA")

    env = load_env()
    local_only = env.get("LOCAL_ONLY", "false").lower() == "true"
    worker_url = env.get("WORKER_URL", "")
    lp_token = env.get("LP_TOKEN", "")

    print("Provider do Chat IA:")
    print("  1) Gemini grátis (recomendado)")
    print("  2) Claude SDK (pago — exige spend limit)")
    print("  3) Ambos (Gemini default, fallback Claude)")
    escolha = input("Escolha [1/2/3]: ").strip()

    if escolha not in {"1", "2", "3"}:
        print("❌ Escolha inválida.")
        return 1

    chat_provider = ""
    updates: dict = {}

    if escolha in {"1", "3"}:
        gemini_key = coletar_gemini()
        if not gemini_key:
            print("❌ Key Gemini vazia.")
            return 1
        if local_only:
            updates["GEMINI_API_KEY"] = gemini_key
        else:
            if not _set_secret("GEMINI_API_KEY", gemini_key):
                return 1
        chat_provider = "gemini"

    if escolha in {"2", "3"}:
        claude_key = coletar_claude()
        if not claude_key:
            print("❌ Key Claude vazia ou spend limit não confirmado.")
            return 1
        if local_only:
            updates["ANTHROPIC_API_KEY"] = claude_key
        else:
            if not _set_secret("ANTHROPIC_API_KEY", claude_key):
                return 1
        chat_provider = "claude" if escolha == "2" else "both"

    updates["CHAT_PROVIDER"] = chat_provider
    updates["CHAT_IA_DONE"] = "true"
    save_env(updates)
    print(f"✅ Provider salvo: {chat_provider}")

    if not local_only:
        time.sleep(2)
        _smoke_chat(worker_url, lp_token)

    print("\n➡️  Próximo passo: python3 setup/setup_deploy.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
