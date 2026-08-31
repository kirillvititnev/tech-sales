# White Shop — project skill allowlist

Only these directories are intentional Cursor project skills.
Agents must not browse `.vendor/cybersecurity-skills/`.

### White Shop (product) — `.cursor/skills/`

- white-shop-orchestration
- white-shop-storefront-mini
- white-shop-parser-identity
- white-shop-release

See `AGENTS.md` for the multi-agent roster.

### Ecosystem (engineering) — `.agents/skills/`

Pinned in root `skills-lock.json`. Refresh with `npx skills update`.

| Skill | Source | Use |
|---|---|---|
| `vercel-react-best-practices` | vercel-labs/agent-skills | React / Next.js performance |
| `test-driven-development` | obra/superpowers | Features & bugfixes before implementation |
| `verification-before-completion` | obra/superpowers | Evidence before "done" / PR claims |
| `playwright-best-practices` | currents-dev/playwright-best-practices-skill | E2E / flaky / POM / CI |
| `webapp-testing` | anthropics/skills | Local browser verify via Playwright |
| `code-review` | mattpocock/skills | Standards + Spec review since a fixed point |

Treat any Playwright "security testing" notes as a **hardening checklist**, not an attack procedure.

### Security allowlist (defensive) — `.cursor/skills/`

- implementing-jwt-signing-and-verification
- implementing-gdpr-data-protection-controls
- implementing-gdpr-data-subject-access-request
- implementing-api-rate-limiting-and-throttling
- performing-security-headers-audit
- securing-github-actions-workflows
- implementing-devsecops-security-scanning
- implementing-secret-scanning-with-gitleaks
- implementing-secrets-scanning-in-ci-cd
- scanning-docker-images-with-trivy
- hardening-docker-containers-for-production

See `.cursor/rules/skills-first.mdc` for when to load each security skill.
