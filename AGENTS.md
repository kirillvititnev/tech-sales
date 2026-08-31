# White Shop — multi-agent roster

Orchestrator (human talks here) routes work. Specialists stay in their lane.
Always run `graphify query` / `path` / `explain` before broad codebase exploration.

| Agent | Owns | Skills |
|---|---|---|
| **Orchestrator** | Scope, route, merge criteria, refuse out-of-policy work | `white-shop-orchestration`, skills-first, graphify, `verification-before-completion` |
| **Storefront / design** | `apps/web` except `/admin`; Mini App HIG | `white-shop-storefront-mini`, apple-design, `vercel-react-best-practices` |
| **API / accounts** | `apps/api` JWT, checkout, bonuses, PII | JWT / GDPR / rate-limit allowlist, `test-driven-development` |
| **Catalog / parser** | `apps/worker`, offer identity, price lists | `white-shop-parser-identity`, `test-driven-development` |
| **Admin** | `apps/web/src/app/admin/**` | HIG grouped lists; `vercel-react-best-practices` |
| **QA** | Tests first; pytest + browser verify | `test-driven-development`, `playwright-best-practices`, `webapp-testing`, `verification-before-completion` |
| **Release / security** | CI, Compose, secrets, prod checklist | `white-shop-release`, `code-review` + Trivy / Actions / gitleaks allowlist |

Ecosystem skills live under `.agents/skills/` (see `skills-lock.json`). Product + security allowlist under `.cursor/skills/`.

## Routing

1. One ticket = one specialist (or Orchestrator + QA).
2. Do not mix parser identity work with JWT/PII in the same session.
3. QA must not weaken failing tests to make green.
4. Release prepares a checklist; **human** confirms production deploy.
5. Never load `.vendor/cybersecurity-skills/` or offensive skills.
6. Before claiming done or opening a PR: run `verification-before-completion`.

## Definition of done (every feature)

- graphify orientation used if >1 file touched
- relevant tests green (`make test` or scoped pytest/node)
- UI changes verified in browser when storefront/admin
- no secrets committed; allowlist skills only for security work
