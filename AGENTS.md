# White Shop — multi-agent roster

Orchestrator (human talks here) routes work. Specialists stay in their lane.
Always run `graphify query` / `path` / `explain` before broad codebase exploration.

| Agent | Owns | Skills |
|---|---|---|
| **Orchestrator** | Scope, route, merge criteria, refuse out-of-policy work | `white-shop-orchestration`, skills-first, graphify |
| **Storefront / design** | `apps/web` except `/admin`; Mini App HIG | `white-shop-storefront-mini`, apple-design |
| **API / accounts** | `apps/api` JWT, checkout, bonuses, PII | JWT / GDPR / rate-limit allowlist |
| **Catalog / parser** | `apps/worker`, offer identity, price lists | `white-shop-parser-identity` |
| **Admin** | `apps/web/src/app/admin/**` | HIG grouped lists; no Mini App card rules |
| **QA** | Tests first; pytest + browser verify | TDD / Playwright when installed |
| **Release / security** | CI, Compose, secrets, prod checklist | `white-shop-release` + Trivy / Actions / gitleaks allowlist |

## Routing

1. One ticket = one specialist (or Orchestrator + QA).
2. Do not mix parser identity work with JWT/PII in the same session.
3. QA must not weaken failing tests to make green.
4. Release prepares a checklist; **human** confirms production deploy.
5. Never load `.vendor/cybersecurity-skills/` or offensive skills.

## Definition of done (every feature)

- graphify orientation used if >1 file touched
- relevant tests green (`make test` or scoped pytest/node)
- UI changes verified in browser when storefront/admin
- no secrets committed; allowlist skills only for security work
