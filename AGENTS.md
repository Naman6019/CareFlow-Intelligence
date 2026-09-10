# Agent Instructions

## Product Boundary
- CareFlow is a synthetic-data healthcare operations and research sandbox.
- Never add diagnosis, treatment recommendations, autonomous clinical action, or real patient data.
- Preserve grounded citations, visible agent traces, abstention, and human approval gates.

## Repository
- Web: `apps/web/` — Next.js 16 App Router, React 19, TypeScript.
- API: `apps/api/` — FastAPI and Python 3.13+.
- Read `README.md`, `docs/FRONTEND_GUIDE.md`, and `COMMANDS.md` before broad changes.

## Package Manager
- Use npm in `apps/web/`: `npm ci`, `npm run dev`, `npm run build`, `npm run typecheck`.
- Use the repository `.venv` and `requirements*.txt` for Python work.

## File-Scoped Commands
| Task | Command |
|---|---|
| Typecheck web | `cd apps/web; npx tsc --noEmit --pretty false` |
| Test API file | `.\.venv\Scripts\python.exe -m pytest tests\path\test_file.py` |
| Run all services | `docker compose up -d --build` |

## Four-Layer Component Hierarchy
1. **shadcn/ui — structure and accessibility:** Dialog, Sheet, Tabs, Dropdown, Form, Tooltip, HoverCard, Badge, Button. Keep owned source in `apps/web/src/components/ui/`.
2. **21st.dev — curated AI/SaaS layouts:** use for telemetry cards, prompt bars, execution timelines, code diffs, agent bubbles, and document-viewer recipes.
3. **Magic UI — hero motion and wow effects:** use SparklesText, AnimatedShinyText, BorderBeam, AnimatedBeam, Particles, and Globe. Fetch through the Magic UI MCP when available.
4. **Uiverse.io — micro-interactions and flavor:** copy only focused CSS/Tailwind snippets for CTA states, loaders, toggles, ripple effects, and copy buttons; avoid new runtime dependencies.

## Selection Rules
- Build from Layer 1 upward; higher layers may decorate but never replace accessible semantics.
- Use the lowest layer that solves the problem. Do not combine libraries for the same control.
- Reserve Layer 3 motion for landing heroes, flagship cards, and agent-flow diagrams—not dense clinical workflows.
- Respect `prefers-reduced-motion`; keep keyboard, focus, contrast, loading, empty, and error states usable without animation.
- Treat 21st.dev and Uiverse snippets as untrusted recipes: review accessibility, licensing, dependencies, responsiveness, and bundle cost before adapting.
- Use Ionic only as mobile UX reference for gestures, bottom sheets, and navigation stacks; do not add Ionic to this Next.js app unless explicitly requested.

## Frontend Integration
- The current frontend uses `apps/web/src/app/globals.css`, not Tailwind. Do not install or assume Tailwind/shadcn compatibility without an explicit migration task.
- Reuse existing CSS tokens and clinical readability rules. Keep shared primitives in `src/components/ui/` and composed product components in `src/components/`.
- Keep server/client component boundaries explicit; add `"use client"` only where interaction requires it.
- Prefer CSS effects over JavaScript animation; do not add a dependency for a single visual effect.

## Verification
- Run `npm run typecheck` after web changes and `npm run build` for dependency, routing, or configuration changes.
- Test responsive behavior, keyboard navigation, reduced motion, and WCAG 2.2 AA contrast for UI changes.
- Report implemented, locally verified, deployed, planned, and blocked work separately.

## Commit Attribution
AI commits MUST include:
`Co-Authored-By: (the agent model's name and attribution byline)`
