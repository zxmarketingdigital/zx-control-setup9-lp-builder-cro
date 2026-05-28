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


# Features pré-fabricadas por nicho — formato {icon, title, desc} que o
# template HTML (features.html) consome via x-for. Aluno edita depois
# em lp-template/lp-config.json (campo copy.features) ou via setup_copy.py.
NICHO_FEATURES = {
    "b2b-saas-clean": [
        {"icon": "⚡", "title": "Implantação em 7 dias",
         "desc": "Onboarding guiado por especialista, integrações prontas — sem projeto interno paralelo."},
        {"icon": "📊", "title": "Dashboard de ROI em tempo real",
         "desc": "Você vê o impacto financeiro de cada feature usada — não fica refém de relatório trimestral."},
        {"icon": "🔒", "title": "SOC 2 + LGPD compliant",
         "desc": "Compliance pronto pra TI exigente. Dados em região São Paulo, audit log incluso."},
    ],
    "infoproduto-bold": [
        {"icon": "🚀", "title": "Método validado em 8 dígitos",
         "desc": "Mais de 10 mil alunos passaram pelo mesmo passo a passo que você vai receber agora."},
        {"icon": "🎯", "title": "Comunidade ativa diariamente",
         "desc": "Grupo exclusivo no WhatsApp + lives quinzenais — você nunca trava sozinho."},
        {"icon": "💎", "title": "Garantia incondicional de 7 dias",
         "desc": "Testa sem risco. Se não for o que esperava, devolvemos 100% sem perguntas."},
    ],
    "agencia-criativa": [
        {"icon": "📈", "title": "Estratégia validada em 8 dígitos",
         "desc": "Replicamos o método que já gerou mais de R$ 50 milhões em lançamentos para infoprodutores e agências."},
        {"icon": "🎨", "title": "Copy + criativo + tráfego como peça única",
         "desc": "Nada de equipes desconectadas. Tudo orquestrado por um time sênior que entende o seu funil de ponta a ponta."},
        {"icon": "📊", "title": "Painel ao vivo com seus números",
         "desc": "Acompanhe conversão, CPA, ROAS e LTV em tempo real — clareza total para decidir escala ou ajuste."},
    ],
    "ecommerce": [
        {"icon": "🛒", "title": "Frete grátis a partir de R$ 199",
         "desc": "Envio expresso pra todo Brasil, rastreamento na conta e troca sem custo em 30 dias."},
        {"icon": "💳", "title": "Parcelamento em até 12x sem juros",
         "desc": "Pix com 5% off ou cartão em 12x — você escolhe a forma que cabe no seu mês."},
        {"icon": "⭐", "title": "+10 mil avaliações 5 estrelas",
         "desc": "Produto testado por uma comunidade real — leia o que os clientes dizem antes de decidir."},
    ],
    "servico-local": [
        {"icon": "📍", "title": "Atendimento na sua região",
         "desc": "Profissional local que conhece o bairro, com agenda flexível pra encaixar no seu dia."},
        {"icon": "✅", "title": "Orçamento sem compromisso",
         "desc": "Avaliação grátis na primeira visita, com proposta clara em até 24h e sem letra miúda."},
        {"icon": "🛡️", "title": "Garantia de serviço por 90 dias",
         "desc": "Se algo der errado, voltamos sem custo. Sua confiança é o nosso ativo mais importante."},
    ],
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

    # Features estruturadas por nicho — template HTML (features.html) espera
    # array de {icon, title, desc}. Aluno edita depois via setup_copy.py ou
    # direto em lp-template/lp-config.json.
    features = NICHO_FEATURES.get(slug, [])
    cfg_updates = {
        "name": nome_cliente,
        "cta_principal": cta,
        "nicho": slug,
    }
    if features:
        cfg = _read_json(CONFIG_JSON)
        copy_block = cfg.get("copy") or {}
        # Não sobrescreve copy se aluno já preencheu via setup_copy.py
        if not copy_block.get("features"):
            copy_block["features"] = features
            cfg_updates["copy"] = copy_block
    _atualizar_config(cfg_updates)
    print(f"✅ Briefing salvo em {BRIEFING_MD}")
    if features and "copy" in cfg_updates:
        print(f"✅ {len(features)} features pré-fabricadas gravadas em lp-config.json")
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
