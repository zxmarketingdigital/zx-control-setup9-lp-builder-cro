#!/usr/bin/env python3
"""Setup 9 — Etapa 3: Copy alta conversão.

Escolha de framework (PAS/AIDA/BAB), Claude escreve cada seção (hero,
features, objeções, FAQ, CTA) ou aluno cola direto. Lint avisa palavras
técnicas. Grava copy estruturado em lp-config.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

from setup_base import (
    ensure_dirs,
    ensure_env_file,
    progress_banner,
    save_env,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
LP_DIR = REPO_ROOT / "lp-template"
CONFIG_JSON = LP_DIR / "lp-config.json"
BRIEFING_MD = LP_DIR / "briefing.md"

FRAMEWORKS = {"1": "PAS", "2": "AIDA", "3": "BAB"}

PALAVRAS_TECNICAS = {"endpoint", "api", "webhook", "schema", "jwt"}


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


def _lint_tecnico(texto: str, secao: str) -> None:
    palavras = [p.strip(".,;:()\"'!?").lower() for p in texto.split()]
    encontradas = [p for p in palavras if p in PALAVRAS_TECNICAS]
    if len(encontradas) > 2:
        print(f"⚠️  Lint [{secao}]: {len(encontradas)} palavras técnicas detectadas ({', '.join(set(encontradas))}). Revise pra linguagem mais simples.")


def _coletar_multilinha(prompt: str) -> str:
    """Coleta input multi-linha. Linhas em branco SÃO preservadas.
    Para terminar: linha contendo apenas '.' (ponto) ou 'EOF'."""
    print(prompt)
    print("(termine com '.' em linha sozinha ou 'EOF')")
    linhas = []
    while True:
        try:
            linha = input()
        except EOFError:
            break
        stripped = linha.strip()
        if stripped in (".", "EOF"):
            break
        linhas.append(linha)
    return "\n".join(linhas).strip()


def _coletar_secao(nome: str, framework: str, briefing_path: Path) -> str:
    print()
    print(f"━━ Seção: {nome.upper()} ━━")
    print("Quer que o Claude escreva ou você cola pronto?")
    print("  1) Claude escreve (vou dar instrução pra você colar)")
    print("  2) Eu colo o texto pronto")
    opc = input("Escolha [1/2]: ").strip()

    if opc == "1":
        print()
        print(f"📝 Cole no Claude o briefing.md ({briefing_path}) e peça:")
        print(f"   \"Escreva a seção {nome} da LP no framework {framework}.\"")
        print()
        texto = _coletar_multilinha(f"Depois cole o texto retornado aqui:")
    else:
        texto = _coletar_multilinha(f"Cole o texto da seção {nome}:")
    _lint_tecnico(texto, nome)
    return texto


def _coletar_hero(framework: str, briefing_path: Path) -> dict:
    """Hero estruturado: headline + subheadline + cta_label."""
    print()
    print("━━ Seção: HERO (3 sub-campos) ━━")
    headline = input("Hero headline (frase forte de impacto, 1 linha): ").strip()
    subheadline = input("Hero subheadline (1-2 linhas expandindo a promessa): ").strip()
    cta_label = input("Hero CTA label (texto exato do botão, ex: 'Quero meu diagnóstico'): ").strip()
    _lint_tecnico(headline + " " + subheadline + " " + cta_label, "hero")
    return {
        "headline": headline,
        "subheadline": subheadline,
        "cta_label": cta_label,
    }


def _coletar_cta_final(framework: str, briefing_path: Path) -> dict:
    """CTA final estruturado: headline + subheadline + button_label."""
    print()
    print("━━ Seção: CTA FINAL (3 sub-campos) ━━")
    headline = input("CTA headline (ex: 'Pronto pra começar?'): ").strip()
    subheadline = input("CTA subheadline (frase incentivando ação): ").strip()
    button_label = input("CTA button label (texto do botão): ").strip()
    _lint_tecnico(headline + " " + subheadline + " " + button_label, "cta")
    return {
        "headline": headline,
        "subheadline": subheadline,
        "button_label": button_label,
    }


def _coletar_lista(nome: str, framework: str, briefing_path: Path, n: int) -> list:
    print(f"\n>> {n} itens em {nome}. Cole UM por vez. Linha vazia entre itens.")
    itens = []
    for i in range(1, n + 1):
        print(f"\nItem {i}/{n} de {nome}:")
        texto = _coletar_secao(f"{nome} #{i}", framework, briefing_path)
        if texto:
            itens.append(texto)
    return itens


def _coletar_faq(framework: str, briefing_path: Path, n: int = 5) -> list:
    print(f"\n>> {n} perguntas+respostas no FAQ.")
    faq = []
    for i in range(1, n + 1):
        print(f"\nFAQ {i}/{n}")
        pergunta = input(f"  Pergunta {i}: ").strip()
        if not pergunta:
            continue
        resposta = _coletar_secao(f"FAQ resposta #{i}", framework, briefing_path)
        faq.append({"q": pergunta, "a": resposta})
    return faq


def main() -> int:
    ensure_dirs()
    ensure_env_file()
    progress_banner(3, 8, "Copy alta conversão")

    if not BRIEFING_MD.exists() or not CONFIG_JSON.exists():
        print("❌ Briefing ou lp-config.json não encontrados. Rode etapas 1 e 2 primeiro.")
        return 1

    print("Qual framework de copy?")
    print("  1) PAS (Problem → Agitate → Solution)")
    print("  2) AIDA (Attention → Interest → Desire → Action)")
    print("  3) BAB (Before → After → Bridge)")
    fr = input("Escolha [1/2/3]: ").strip()
    framework = FRAMEWORKS.get(fr)
    if not framework:
        print("❌ Escolha inválida.")
        return 1

    hero = _coletar_hero(framework, BRIEFING_MD)
    features = _coletar_lista("features", framework, BRIEFING_MD, 3)
    objections = _coletar_lista("objeções", framework, BRIEFING_MD, 3)
    faq = _coletar_faq(framework, BRIEFING_MD, 5)
    cta = _coletar_cta_final(framework, BRIEFING_MD)

    cfg = _read_json(CONFIG_JSON)
    cfg["copy"] = {
        "framework": framework,
        "hero": hero,
        "features": features,
        "objections": objections,
        "faq": faq,
        "cta": cta,
    }
    _write_json(CONFIG_JSON, cfg)

    print(f"\n✅ Copy salvo em {CONFIG_JSON}")
    save_env({"COPY_DONE": "true"})
    print("\n➡️  Próximo passo: python3 setup/setup_lp_build.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
