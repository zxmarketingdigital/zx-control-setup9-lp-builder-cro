#!/usr/bin/env python3
"""Setup 9 — Etapa 7: Chat IA (Groq, Gemini ou Claude).

Groq (recomendado): Llama 3.3 70B grátis, sem cartão.
Gemini: fallback, free tier compartilhado por conta Google.
Claude: SDK pago — exige confirmação de spend limit.

Modo full → wrangler secret put. Modo local-only → salva no env.
Validação: GET /models (não consome quota).
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
    # /chat-ia é endpoint público — não precisa de X-LP-Token. Só X-LP-Id.
    # Mas no smoke, passamos um Origin que está na allowlist pra simular a LP.
    cfg_path = REPO_ROOT / "lp-template" / "lp-config.json"
    lp_id = ""
    origin_header = ""
    try:
        import json as _json
        cfg = _json.loads(cfg_path.read_text(encoding="utf-8"))
        lp_id = cfg.get("id", "")
        origins = cfg.get("allowed_origins", [])
        if origins:
            origin_header = origins[0] if origins[0].startswith("http") else f"https://{origins[0]}"
    except (OSError, _json.JSONDecodeError):
        pass

    url = f"{worker_url}/chat-ia"
    payload = json.dumps({"messages": [{"role": "user", "content": "Olá, isso é um teste."}]})
    print(f"🧪 Smoke POST {url}")
    try:
        curl_cmd = [
            "curl", "-sS", "-N", "--max-time", "15",
            "-H", "Content-Type: application/json",
            "-H", f"X-LP-Id: {lp_id}",
        ]
        if origin_header:
            curl_cmd += ["-H", f"Origin: {origin_header}"]
        curl_cmd += ["-X", "POST", "-d", payload, url]
        result = subprocess.run(
            curl_cmd,
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


def _validate_groq_key(key: str) -> str:
    """GET /models — não consome quota. Retorna 'ok' / 'rate_limited' / 'invalid' / 'network'."""
    try:
        result = subprocess.run(
            ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "10",
             "-H", f"Authorization: Bearer {key}",
             "https://api.groq.com/openai/v1/models"],
            capture_output=True, text=True, timeout=12,
        )
        code = (result.stdout or "").strip()
    except subprocess.TimeoutExpired:
        return "network"
    except FileNotFoundError:
        return "network"
    if code == "200":
        return "ok"
    if code == "401":
        return "invalid"
    if code == "429":
        return "rate_limited"
    return "network"


def coletar_groq() -> str:
    print()
    print("⚡ Provider: Groq (Llama 3.3 70B — RECOMENDADO)")
    print("   Por que Groq: IA gratuita da Meta rodando em hardware ultra-rápido,")
    print("   sem cartão de crédito. Free tier de centenas de chats/dia,")
    print("   muito mais que o Gemini.")
    print()
    print("   Passo-a-passo (30s):")
    print("   1. Abra: https://console.groq.com/keys")
    print("   2. Faça login com Google")
    print("   3. Clique em 'Create API Key' → cole abaixo")
    print()
    key = _input_secret("Cole a GROQ_API_KEY (formato gsk_...): ")
    if not key:
        return ""
    status = _validate_groq_key(key)
    if status == "ok":
        print("✅ Key Groq validada (HTTP 200 em /models).")
        return key
    if status == "invalid":
        print("❌ Key rejeitada (HTTP 401). Confere se copiou inteira.")
        return ""
    if status == "rate_limited":
        print("⚠️  Key aceita mas rate-limited AGORA (429). Pode ser quota por minuto (30 RPM).")
        print("    Se persistir, sua conta atingiu o cap diário — chat IA vai cair em canned.")
        conf = input("    Gravar mesmo assim? [s/N]: ").strip().lower()
        if conf != "s":
            print("ℹ️  Tente de novo em 1 min ou volte com outra key.")
            return ""
        return key
    print("⚠️  Não consegui validar (timeout/rede). Vou gravar mesmo assim — testa depois com /chat-ia.")
    return key


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
    print("  1) Groq — Llama 3.3 70B grátis (RECOMENDADO, sem cartão)")
    print("  2) Gemini grátis — Google AI Studio")
    print("  3) Claude SDK — pago, exige spend limit")
    print("  4) Pular — chat fica em canned fallback (sem IA real)")
    escolha = input("Escolha [1/2/3/4]: ").strip()

    if escolha not in {"1", "2", "3", "4"}:
        print("❌ Escolha inválida.")
        return 1

    chat_provider = ""
    updates: dict = {}

    if escolha == "4":
        updates["CHAT_PROVIDER"] = "canned"
        updates["CHAT_IA_DONE"] = "true"
        save_env(updates)
        print("ℹ️  Provider salvo: canned (chat IA responde mensagem fixa com link de contato).")
        print("\n➡️  Próximo passo: python3 setup/setup_deploy.py")
        return 0

    if escolha == "1":
        groq_key = coletar_groq()
        if not groq_key:
            print("❌ Key Groq vazia.")
            return 1
        if local_only:
            updates["GROQ_API_KEY"] = groq_key
        else:
            if not _set_secret("GROQ_API_KEY", groq_key):
                return 1
        chat_provider = "groq"

    if escolha == "2":
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

    if escolha == "3":
        claude_key = coletar_claude()
        if not claude_key:
            print("❌ Key Claude vazia ou spend limit não confirmado.")
            return 1
        if local_only:
            updates["ANTHROPIC_API_KEY"] = claude_key
        else:
            if not _set_secret("ANTHROPIC_API_KEY", claude_key):
                return 1
        chat_provider = "claude"

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
