# White Shop — project skill allowlist

Only these directories are intentional Cursor project skills.
Agents must not browse `.vendor/cybersecurity-skills/`.

### White Shop (product)

- white-shop-orchestration
- white-shop-storefront-mini
- white-shop-parser-identity
- white-shop-release

See `AGENTS.md` for the multi-agent roster.

### Security allowlist (defensive)

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
