---
name: lp-from-design-md
description: "Gera LP single-file (HTML + CSS puro) a partir de qualquer design system do repo VoltAgent/awesome-design-md, aplicando uma copy fornecida nos tokens originais (cores, tipografia, radius, spacing). Use SEMPRE que o usuário disser: gera LP no estilo X, renderiza essa copy estilo Linear, cria demo no design Cursor, LP estilo VoltAgent, fazer LP no padrão Stripe, demo da copy no estilo Y, renderizar LP estilo Z, LP a partir do design system X."
model: sonnet
effort: medium
---

# /lp-from-design-md — Gerar LP a partir de qualquer design system

Cria uma LP single-file (HTML + CSS puro com CSS variables) renderizada com fidelidade 1:1 a um design system do repo `VoltAgent/awesome-design-md`. Aplica uma copy fornecida usando os tokens (cores, tipografia, radius, spacing) extraídos do `DESIGN.md` original.

## Quando usar

- "Gera LP no estilo Linear/Cursor/VoltAgent/Stripe/Vercel/etc."
- "Renderiza essa copy estilo X"
- "Cria demo da copy Y no design Z"
- "LP a partir do design system W"
- Toda vez que o usuário quiser comparar visualmente um conteúdo em um sistema visual específico antes de comprometer com um design final.

## Pré-requisitos

Repo `awesome-design-md` clonado em `~/projetos/awesome-design-md/`. Se não existir:
```bash
git clone https://github.com/VoltAgent/awesome-design-md.git ~/projetos/awesome-design-md
```

Slugs disponíveis: ver `ls ~/projetos/awesome-design-md/design-md/` (71 sistemas — linear.app, cursor, voltagent, vercel, stripe, claude, apple, airbnb, ferrari, spotify, etc.).

Showcase de referência com todos os 71 já renderizados: `~/projetos/lp-design-md-showcase/` (também acessível via Launcher ZX LAB → seção "Design & Demos").

## Passo a passo

### 1. Coletar entrada
Pedir ao usuário (se não vier no prompt):
- **Copy/conteúdo** (markdown, texto solto, ou arquivo `COPY.md` existente). Se for um produto ZX LAB conhecido (Agência IA 50K, Formação, Agente IA 15M), procurar primeiro em `~/projetos/lp-<produto>/COPY.md`.
- **Slug do design system** (ex: `linear.app`, `cursor`, `voltagent`). Se o usuário disser apenas o nome ("estilo Linear"), buscar match em `~/projetos/awesome-design-md/design-md/`.

### 2. Validar slug
```bash
ls ~/projetos/awesome-design-md/design-md/<slug>/DESIGN.md
```
Se não existe, listar opções e perguntar. Não inventar slug.

### 3. Ler e estudar o DESIGN.md
Ler o arquivo inteiro com Read. Identificar:
- **Cores**: canvas, surface(s), ink, ink-muted, hairline, primary, on-primary
- **Tipografia**: famílias display/body/mono, escala (display-xl/lg/md/headline/body), tracking, weights
- **Radius**: btn, card, panel
- **Spacing**: section, card, card-padding
- **Componentes destacados** no DESIGN.md (button-primary, feature-card, cta-banner, etc.)
- **"Do's and Don'ts"** quando existirem — respeitar regras (ex: Linear proíbe lavender como background; VoltAgent proíbe segundo accent)

Se o DESIGN.md tem **YAML frontmatter** (~60% dos casos), os tokens estão estruturados em `colors:`, `typography:`, etc. Copiar diretamente.

Se é **markdown puro** (VoltAgent, Vercel, Ollama, Warp, etc.), extrair hex codes do texto e classificar por contexto (atenção: `#faf9f6` em Warp é texto, não canvas — ler a descrição com cuidado).

### 4. Mapear fontes proprietárias para Google Fonts
Tabela de fallback rápida:
- SF Pro / Geist / Inter / Matter / FerrariSans / CursorGothic / Linear Display → **Inter**
- Tiempos / Copernicus → **Fraunces**
- Founders Grotesk / Monument → **Space Grotesk**
- Cereal / Spotify Circular / SpotifyMixUI / Circular → **DM Sans**
- IBM Plex → **IBM Plex Sans**
- Manrope → **Manrope**
- Mono (qualquer) → **JetBrains Mono**

Quando o DESIGN.md tem fonte proprietária pouco conhecida, ler o "Note on Font Substitutes" do próprio arquivo — quase todos sugerem substituto.

### 5. Criar projeto
```bash
mkdir -p ~/projetos/lp-<copy-slug>-<design-slug>
```
Convenção de nome: `lp-<copy-slug>-<design-slug>` (ex: `lp-agencia-ia-50k-linear`, `lp-formacao-cientista-cursor`).

### 6. Renderizar `index.html`
Markup semântico, mobile-first. Estrutura mínima recomendada:
```
<header class="top-nav">         · sticky, brand mark + nav links + CTA
<div class="urgency-bar">        · opcional, só se a copy tiver
<main>
  <section class="hero">          · eyebrow + h1 (display-xl) + subhead + 2 CTAs + meta/prova social
  <section class="screenshot">    · opcional, demo de produto (terminal, UI mockup) — segue padrão do sistema
  <section class="strip">         · feature strip 3-4 cards (números/destaques)
  <section class="features">      · 6+ feature cards no grid 3-up
  <section class="content">       · masterclasses, módulos, etc. — usar padrão "changelog rows" se Linear; "bento" se Stripe
  <section class="metrics">       · números (alunos, países, garantia)
  <section class="guarantee">     · painel destacado com garantia
  <section class="faq">           · <details> nativo
  <section class="cta-banner">    · fechamento
<footer>
```

Adaptar à copy. Não incluir seções vazias.

### 7. Renderizar `styles.css`
Estrutura obrigatória:
```css
:root {
  /* TOKENS COPIADOS DO DESIGN.md — não inventar */
  --primary: #...;
  --on-primary: #...;
  --canvas: #...;
  --surface-1: #...;
  --ink: #...;
  --ink-muted: #...;
  --hairline: #...;
  /* etc. */

  --radius-btn: ...;
  --radius-card: ...;

  --s-section: 96px;  /* ou o spacing.section do sistema */

  --font-display: <fallback do sistema>;
  --font-body: <fallback do sistema>;
  --font-mono: <fallback do sistema>;
}
```

Regras:
- Usar `clamp()` no display (`clamp(40px, 7vw, 80px)`) para responsivo
- Preservar tracking/letter-spacing exato do DESIGN.md (ex: Linear -3px no display 80px)
- Cards: 1px hairline border + radius-card, sem box-shadow a menos que o sistema use
- Hover states sutis (background shift na surface ladder)
- Breakpoints: 1024px (3-up→2-up), 768px (2-up→1-up), 480px ajustes finais
- Prefers-reduced-motion respeitado em qualquer animação

### 8. Abrir no navegador
```bash
open ~/projetos/lp-<copy-slug>-<design-slug>/index.html
```

### 9. Reportar
- Caminho do projeto
- Tokens-chave aplicados (canvas, primary, fonte display)
- Decisões de adaptação da copy → componentes (ex: "demo Claude Code virou screenshot panel; 10 masterclasses como changelog rows")
- Próximos passos sugeridos: publicar a LP quando aprovada, ou gerar variante em outro design system

## Boas práticas

- **Fidelidade > criatividade**: ler a seção "Do's and Don'ts" do DESIGN.md antes de adicionar qualquer elemento decorativo
- **Inter quando em dúvida**: a maioria dos sistemas modernos cai em Inter como fallback público — não tente reinventar
- **Acento escasso**: sistemas como Linear usam o primary só em brand mark + CTA + focus. Não decore com a cor primária
- **CSS variables, não Tailwind**: o objetivo é fidelidade 1:1 ao DESIGN.md — Tailwind esconde os tokens em utility classes
- **Single file por LP, sem build step**: HTML + CSS puro. Zero dependências de Node/npm
- **Ler exemplo de referência**: `~/projetos/lp-agencia-ia-50k-linear/` é a primeira LP rica gerada com este padrão (Linear, full copy 50K)

## Anti-padrões

- ❌ Adicionar Tailwind/Vite/Astro "para ficar mais profissional" — quebra a fidelidade
- ❌ Inventar paleta complementar — o sistema já documenta tudo
- ❌ Usar emojis se o sistema não usa
- ❌ Drop-shadows em sistemas dark que documentam não usar (Linear, VoltAgent)
- ❌ Pill-button onde o sistema usa radius-md (ex: Linear)
- ❌ Salvar em pasta com nome conflitante com LP de produção (ex: `lp-agencia-ia-50k` é a produção; usar `lp-agencia-ia-50k-<design>`)

## Recursos disponíveis

- Repo de design systems: `~/projetos/awesome-design-md/` (71 sistemas prontos pra usar como referência)
