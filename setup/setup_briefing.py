#!/usr/bin/env python3
"""Setup 9 — Etapa 1: Briefing do cliente.

Modo rápido (template por nicho) ou Modo profundo (10 perguntas estruturadas
com autosave retomável). Output: lp-template/briefing.md + atualiza
lp-template/lp-config.json com name + cta_principal.
"""
from __future__ import annotations

import json
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
BRIEFINGS_DIR = LP_DIR / "briefings"
BRIEFING_MD = LP_DIR / "briefing.md"
CONFIG_JSON = LP_DIR / "lp-config.json"
STATE_JSON = LP_DIR / "briefing-state.json"


NICHOS = {
    "1": ("b2b-saas-clean", "B2B SaaS clean"),
    "2": ("infoproduto-bold", "Infoproduto bold"),
    "3": ("agencia-criativa", "Agência criativa"),
    "4": ("ecommerce", "E-commerce"),
    "5": ("servico-local", "Serviço local"),
}


PERGUNTAS_PROFUNDO = [
    ("segmento", "Qual é o segmento/nicho do cliente? (ex: clínica odontológica, SaaS de RH)"),
    ("oferta", "Qual é a oferta principal? (produto, serviço, ticket médio)"),
    ("persona", "Quem é o público-alvo? (faixa etária, cargo, contexto)"),
    ("dores", "Top 3 dores que essa persona sente (separe por ; )"),
    ("objecoes", "Top 3 objeções de compra (separe por ; )"),
    ("prova_social", "Prova social disponível (cases, depoimentos, números)"),
    ("garantia", "Existe garantia? Qual? (ex: 7 dias, satisfação ou dinheiro de volta)"),
    ("cta_principal", "CTA principal (texto exato do botão, ex: 'Quero meu diagnóstico')"),
    ("conversao_esperada", "Conversão esperada (% ou faixa, ex: 3-5% de visitantes vira lead)"),
    ("referencias", "URLs de modelos de referência (até 3, separe por espaço; opcional)"),
]


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


def _atualizar_config(updates: dict) -> None:
    cfg = _read_json(CONFIG_JSON)
    cfg.update(updates)
    _write_json(CONFIG_JSON, cfg)


def _template_fallback(slug: str, nome_legivel: str) -> str:
    """Template mínimo caso lp-template/briefings/{slug}.md não exista."""
    return (
        f"# Briefing — {nome_legivel}\n\n"
        f"> Template pré-fabricado para nicho **{nome_legivel}**.\n"
        f"> Edite os campos abaixo com os dados reais do cliente.\n\n"
        "## Cliente\n- Nome: \n- Site/IG: \n\n"
        "## Oferta\n- Produto/serviço: \n- Ticket médio: \n\n"
        "## Persona\n- Quem é: \n- Dor principal: \n\n"
        "## Objeções\n- 1. \n- 2. \n- 3. \n\n"
        "## Prova social\n- \n\n"
        "## CTA principal\n- Texto: \n"
    )


def _carregar_template_nicho(slug: str, nome_legivel: str) -> str:
    template_path = BRIEFINGS_DIR / f"{slug}.md"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    print(f"⚠️  Template {template_path} não encontrado — usando fallback genérico.")
    return _template_fallback(slug, nome_legivel)


def modo_rapido() -> int:
    print("📋 Modo rápido — escolha um nicho:")
    for k, (_, nome) in NICHOS.items():
        print(f"  {k}) {nome}")
    print()
    escolha = input("Nicho [1-5]: ").strip()
    if escolha not in NICHOS:
        print("❌ Escolha inválida.")
        return 1
    slug, nome_legivel = NICHOS[escolha]
    conteudo = _carregar_template_nicho(slug, nome_legivel)

    nome_cliente = input("Nome do cliente: ").strip() or "Cliente"
    cta = input("CTA principal (texto do botão): ").strip() or "Quero saber mais"

    LP_DIR.mkdir(parents=True, exist_ok=True)
    header = f"# Briefing — {nome_cliente}\n\n> Nicho: {nome_legivel}\n> CTA principal: {cta}\n\n"
    BRIEFING_MD.write_text(header + conteudo, encoding="utf-8")
    _atualizar_config({
        "name": nome_cliente,
        "cta_principal": cta,
        "nicho": slug,
    })
    print(f"✅ Briefing salvo em {BRIEFING_MD}")
    return 0


def modo_profundo() -> int:
    LP_DIR.mkdir(parents=True, exist_ok=True)
    state = _read_json(STATE_JSON)
    if state:
        print("🔄 Briefing em andamento detectado. Continuar de onde parou? [s/N]:")
        resp = input().strip().lower()
        if resp != "s":
            # Confirmação dupla — apagar autosave é destrutivo.
            print("⚠️  Tem certeza? O briefing atual será APAGADO e você começa do zero. [s/N]:")
            conf = input().strip().lower()
            if conf != "s":
                print("ℹ️  Operação cancelada. Retomando do estado salvo.")
            else:
                state = {}
                STATE_JSON.unlink(missing_ok=True)

    state.setdefault("respostas", {})
    nome_cliente = state.get("nome_cliente") or input("Nome do cliente: ").strip() or "Cliente"
    state["nome_cliente"] = nome_cliente
    _write_json(STATE_JSON, state)

    for key, pergunta in PERGUNTAS_PROFUNDO:
        if key in state["respostas"] and state["respostas"][key]:
            print(f"⏭️  [{key}] já respondido — pulando.")
            continue
        resp = input(f"{pergunta}\n> ").strip()
        state["respostas"][key] = resp
        _write_json(STATE_JSON, state)

    respostas = state["respostas"]
    linhas = [f"# Briefing — {nome_cliente}\n"]
    for key, pergunta in PERGUNTAS_PROFUNDO:
        linhas.append(f"## {pergunta}\n\n{respostas.get(key, '').strip()}\n")
    BRIEFING_MD.write_text("\n".join(linhas), encoding="utf-8")

    _atualizar_config({
        "name": nome_cliente,
        "cta_principal": respostas.get("cta_principal", "").strip() or "Quero saber mais",
    })
    print(f"✅ Briefing profundo salvo em {BRIEFING_MD}")
    print(f"   State retomável: {STATE_JSON}")
    return 0


def main() -> int:
    ensure_dirs()
    ensure_env_file()
    progress_banner(1, 8, "Briefing do cliente")

    print("Como você quer montar o briefing?")
    print("  1) Modo rápido (template por nicho — ~5min)")
    print("  2) Modo profundo (10 perguntas com autosave — ~20min)")
    escolha = input("Escolha [1/2]: ").strip()

    if escolha == "1":
        rc = modo_rapido()
    elif escolha == "2":
        rc = modo_profundo()
    else:
        print("❌ Escolha inválida. Saindo.")
        return 1

    if rc == 0:
        save_env({"BRIEFING_DONE": "true"})
        print("\n➡️  Próximo passo: python3 setup/setup_design_system.py")
    return rc


if __name__ == "__main__":
    sys.exit(main())
