---
name: system-design
description: Define and maintain a project design system in `.looper/design.html`, including visual tokens, typography, spacing, surfaces, states, accessibility, and reusable component decisions. Use when bootstrapping, reviewing, or changing the visual language of an interface.
---

# System Design

Use this skill to turn visual decisions into a small, explicit, versionable design system. The source of truth is always the project's `.looper/design.html`; do not create a parallel token file unless the project explicitly requests one.

## Workflow

1. Read `.looper/design.html` and any existing UI implementation before proposing changes. Preserve accepted decisions and consolidate duplicates.
2. Inspect the supplied visual reference when available (for example, a local HTML file) and extract its principles, not its incidental markup. If the reference cannot be opened, continue from the user's description and mark unresolved choices as `[PREENCHER]`.
3. Define semantic tokens before component-specific values. Prefer named roles such as `color.surface.canvas`, `color.text.primary`, `color.action.primary`, `space.4`, `radius.md`, and `shadow.sm`; record raw values beside their intended use.
4. Cover at least: brand and color palette, typography and hierarchy, spacing/density, layout/container sizes, radii, borders, elevation, motion, focus, responsive breakpoints, and component states.
5. Specify loading, empty, error, success, disabled, hover, active, and focus behavior where applicable. Document reduced-motion behavior and minimum contrast (4.5:1 normal text, 3:1 large text and UI components).
6. Update the most relevant section of `.looper/design.html` and record only durable, approved decisions. Keep tokens inspectable in HTML/CSS and do not invent product identity, fonts, colors, or measurements presented as confirmed facts.

## Token format

Keep tokens easy to consume in CSS or application code. Use a compact table or grouped lists with a stable token name, value, and purpose. Prefer a small scale over one-off values:

```md
| Token | Value | Uso |
|---|---|---|
| `font.family.base` | `Inter, system-ui, sans-serif` | Texto da interface |
| `font.size.body` | `1rem / 1.5` | Texto normal |
| `space.4` | `16px` | Respiro padrão |
| `radius.md` | `12px` | Cards e controles |
```

Do not add emojis to interface guidance. Names, labels, and states must use text or the project's icon library.

## Boundaries

This skill defines the visual contract; it does not implement screens or replace modern web/API guidance. When a UI change is made, consult the tokens here and update this document if the change establishes a reusable visual rule.
