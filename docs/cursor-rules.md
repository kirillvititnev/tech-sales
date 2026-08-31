# Cursor rules (index)

White Shop development is steered from `.cursor/rules/` and `AGENTS.md`:

- **Apple HIG** — storefront / Mini App UI
- **skills-first** — defensive allowlist only (`.cursor/skills/`); never load `.vendor/cybersecurity-skills/` or offensive skills
- **graphify** — query/path/explain before broad exploration; AST update on agent stop via hooks
- **Multi-agent roster** — `AGENTS.md` + `white-shop-*` skills under `.cursor/skills/`

Project skills: see `.cursor/skills/README.md`.
The full 800+ cybersecurity pack is archived offline under `.vendor/cybersecurity-skills/` (gitignored) and blocked from reads by `.cursor/hooks/block-cyber-pack.sh`.
