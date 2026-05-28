#!/usr/bin/env python3
"""Setup 9 — Etapa 2: Design System.

Pré-fab por arquétipo (5 opções) ou customizado via skill local
(/huashu-design ou /design-md). Gera CSS vars em lp-template/styles.css
e atualiza lp-config.json.design_system.
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
STYLES_CSS = LP_DIR / "styles.css"


ARQUETIPOS = {
    "1": {
        "slug": "b2b-saas-clean",
        "nome": "B2B SaaS clean",
        "primary": "#2563EB",
        "secondary": "#0F172A",
        "font_heading": "Inter",
        "font_body": "Inter",
        "radius": "8px",
    },
    "2": {
        "slug": "infoproduto-bold",
        "nome": "Infoproduto bold",
        "primary": "#EA580C",
        "secondary": "#1E293B",
        "font_heading": "Plus Jakarta Sans",
        "font_body": "Inter",
        "radius": "12px",
    },
    "3": {
        "slug": "agencia-criativa",
        "nome": "Agência criativa",
        "primary": "#DB2777",
        "secondary": "#18181B",
        "font_heading": "Space Grotesk",
        "font_body": "Inter",
        "radius": "16px",
    },
    "4": {
        "slug": "ecommerce",
        "nome": "E-commerce",
        "primary": "#16A34A",
        "secondary": "#0F172A",
        "font_heading": "Inter",
        "font_body": "Inter",
        "radius": "10px",
    },
    "5": {
        "slug": "servico-local",
        "nome": "Serviço local",
        "primary": "#1E3A8A",
        "secondary": "#0F172A",
        "font_heading": "Inter",
        "font_body": "Inter",
        "radius": "6px",
    },
}


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


def _gerar_css(ds: dict) -> str:
    return (
        "/* Auto-gerado por setup_design_system.py — não editar manualmente */\n"
        ":root {\n"
        f"  --primary: {ds['primary']};\n"
        f"  --secondary: {ds['secondary']};\n"
        f"  --font-heading: '{ds['font_heading']}', system-ui, sans-serif;\n"
        f"  --font-body: '{ds['font_body']}', system-ui, sans-serif;\n"
        f"  --radius: {ds['radius']};\n"
        "  --bg: #ffffff;\n"
        "  --text: #0f172a;\n"
        "  --muted: #64748b;\n"
        "}\n\n"
        "body { font-family: var(--font-body); color: var(--text); background: var(--bg); }\n"
        "h1, h2, h3, h4 { font-family: var(--font-heading); color: var(--secondary); }\n"
        ".btn-primary { background: var(--primary); color: #fff; border-radius: var(--radius); padding: 12px 24px; }\n"
    )


def escolher_pre_fab() -> Optional[dict]:
    print("Arquétipos pré-fabricados:")
    for k, v in ARQUETIPOS.items():
        print(f"  {k}) {v['nome']} — {v['primary']} / {v['font_heading']}")
    escolha = input("Escolha [1-5]: ").strip()
    if escolha not in ARQUETIPOS:
        print("❌ Escolha inválida.")
        return None
    return ARQUETIPOS[escolha]


def modo_customizado() -> Optional[dict]:
    print()
    print("📐 Modo customizado — use uma skill local pra gerar o design.")
    print("   No Claude Code, rode antes:")
    print("     /huashu-design   (alta fidelidade, exploração visual)")
    print("     /design-md       (DESIGN.md estruturado)")
    print()
    primary = input("Cor primária (hex, ex #2563EB): ").strip()
    secondary = input("Cor secundária (hex, ex #0F172A): ").strip()
    font_heading = input("Fonte heading [Inter]: ").strip() or "Inter"
    font_body = input("Fonte body [Inter]: ").strip() or "Inter"
    radius = input("Border-radius [8px]: ").strip() or "8px"
    if not primary or not secondary:
        print("❌ Cores obrigatórias.")
        return None
    return {
        "slug": "custom",
        "nome": "Custom",
        "primary": primary,
        "secondary": secondary,
        "font_heading": font_heading,
        "font_body": font_body,
        "radius": radius,
    }


def main() -> int:
    ensure_dirs()
    ensure_env_file()
    progress_banner(2, 8, "Design System")

    if not BRIEFING_MD.exists():
        print("❌ Briefing não encontrado. Rode setup_briefing.py primeiro.")
        return 1

    print("Como você quer definir o design system?")
    print("  1) Arquétipo pré-fab (5 opções)")
    print("  2) Customizado (via /huashu-design ou /design-md)")
    escolha = input("Escolha [1/2]: ").strip()

    if escolha == "1":
        ds = escolher_pre_fab()
    elif escolha == "2":
        ds = modo_customizado()
    else:
        print("❌ Escolha inválida.")
        return 1

    if ds is None:
        return 1

    cfg = _read_json(CONFIG_JSON)
    cfg["design_system"] = {
        "primary": ds["primary"],
        "secondary": ds["secondary"],
        "font_heading": ds["font_heading"],
        "font_body": ds["font_body"],
        "radius": ds["radius"],
    }
    _write_json(CONFIG_JSON, cfg)

    STYLES_CSS.write_text(_gerar_css(ds), encoding="utf-8")
    print(f"✅ Design system salvo em {CONFIG_JSON}")
    print(f"✅ CSS vars gerados em {STYLES_CSS}")

    save_env({"DESIGN_SYSTEM_DONE": "true"})
    print("\n➡️  Próximo passo: python3 setup/setup_copy.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
