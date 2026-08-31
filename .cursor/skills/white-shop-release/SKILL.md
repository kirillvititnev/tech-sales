---
name: white-shop-release
description: White Shop release and production gate (CI, Compose, secrets, container scan checklist). Use when changing GitHub Actions, Dockerfiles, deploy docs, or preparing a production release.
---

# Release / security gate

Human confirms production. This agent prepares evidence, does not auto-deploy.

## Checklist

- [ ] CI green on the PR (pytest + web unit tests; add Playwright/Trivy when wired)
- [ ] No secrets in git (`.env`, session files, tunnel creds stay local)
- [ ] Compose: non-root / cap_drop where already set; do not regress
- [ ] Auth/me responses stay `Cache-Control: no-store` if touched
- [ ] Security allowlist skill loaded only if changing Actions / images / secrets scanning
- [ ] Rollback note: previous image/tag or `git revert` path

## Skills (allowlist only)

- `securing-github-actions-workflows`
- `scanning-docker-images-with-trivy`
- `hardening-docker-containers-for-production`
- `implementing-secret-scanning-with-gitleaks` / `implementing-secrets-scanning-in-ci-cd`

Never open `.vendor/cybersecurity-skills/`.
