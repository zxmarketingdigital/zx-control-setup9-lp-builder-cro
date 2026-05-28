---
name: design-md
description: Analyze Stitch projects (or local HTML/URLs) and synthesize a semantic design system into DESIGN.md files. Use when the user asks to document the design system of a landing page, generate a DESIGN.md, audit visual consistency across pages, or prepare a design brief for Lovable/Stitch/frontend-design. Triggers: 'gerar design.md', 'documentar design system', 'extrair padrao visual', 'auditar lp design', 'design brief lp'.
model: sonnet
effort: medium
allowed-tools:
  - "stitch*:*"
  - "Read"
  - "Write"
  - "web_fetch"
  - "WebFetch"
  - "Bash"
---

# /design-md

- Analisa Stitch project / HTML / URL.
- Sintetiza Semantic Design System em `DESIGN.md`.
- Audita consistência visual e gera brief para Lovable/Stitch.

Detalhes completos: ler `reference.md` (mesma pasta).
