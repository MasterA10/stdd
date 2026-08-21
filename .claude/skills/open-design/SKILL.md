---
name: open-design
description: Design System, UI Templates, Components, and Craft Navigator for creating web/mobile interfaces, dashboards, and landing pages. Use whenever building, refining, or styling UI screens, selecting design tokens, extracting components, or applying high-polish design principles.
---

# Open Design System & UI Navigator

Use the real Open Design library stored locally on this Mac. The library is intentionally external to the project and must not be copied into the repository.

## Locate the local library

Treat the directory containing the matching `SKILL.md` as `OPEN_DESIGN_ROOT`. Do not assume a volume name, username, or fixed absolute path.

Search these locations in order:

1. `$HOME/.agents/skills/open-design`
2. `$HOME` for `.agents/skills/open-design/SKILL.md`
3. `/Volumes` for `.agents/skills/open-design/SKILL.md`

On macOS, a portable-drive installation commonly matches:

```text
/Volumes/*/N-DOWNLOADS/arquitetura-migracao/.agents/skills/open-design
```

Use a read-only search when the path is not known:

```bash
find "$HOME" /Volumes -type f -path '*/.agents/skills/open-design/SKILL.md' -print 2>/dev/null
```

If no result is found, report that the external Open Design library is unavailable. Do not create a substitute library, copy the large external directory, or invent its assets.

## Navigate on demand

After locating `OPEN_DESIGN_ROOT`, read only the files needed for the current interface task:

- Design systems: `design-systems/<name>/components.html`, `DESIGN.md`, `tokens.css`, or `design-tokens.json`
- Templates: `design-templates/<name>/example.html`
- Craft guidance: `craft/<topic>.md`
- Specialized workflows: `skills/<skill-name>/SKILL.md`

Choose the design system or template based on the requested product, visual language, and interaction needs. Do not load the whole library at once.

## Quality baseline

For interface work, consult the relevant craft guidance, especially `craft/anti-ai-slop.md`, `craft/accessibility-baseline.md`, and `craft/state-coverage.md`. Preserve semantic HTML, keyboard access, visible focus, readable contrast, responsive behavior, and complete loading, empty, error, disabled, hover, active, and focus states when applicable.

Use the external files as design references and source material. Implement the result in the project’s own code and assets unless the user explicitly requests otherwise.
