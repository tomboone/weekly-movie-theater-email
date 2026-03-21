# Project: weekly-movie-theater-email

Python pipeline that scrapes Regal theater showtimes weekly, enriches with TMDB metadata, and sends an HTML email via Azure Communication Services.

## Dev Environment

- **Docker-only** — all commands run inside the container, no local Python/venv
- **uv** for package management (not pip)
- **go-task** for orchestration — see `Taskfile.yml`

### Common commands

```
task up             # Start infra + dev container
task run            # Run the app (uvicorn via exec)
task stop           # Stop the dev container
task down           # Remove the dev container
task reset          # Tear down, rebuild, start fresh
task build          # Build Docker image
task test           # Run all tests
task test:unit      # Run unit tests only
task check          # Run all checks (ruff, pyright, yamllint, pytest)
task lint           # Ruff check + format
task lint:fix       # Auto-fix ruff issues
task trigger        # POST to /trigger via Traefik (requires TRIGGER_API_KEY in .env)
task trigger -- MM-DD-YYYY  # trigger with date override
task shell          # Open a shell in the container
task hooks:install  # Install pre-commit hooks
task infra:up       # Start shared localdev infra (traefik, etc.)
task infra:down     # Stop shared localdev infra
task infra:status   # Show infra container status
```

### Local dev architecture

- Container idles with dev deps pre-installed; app runs via `task run`
- All dev tasks use `docker compose exec` on the running container (no new containers)
- Integrated with `tbc-localdev-infra` — Traefik routes `https://movie-email.localhost` to the app
- Pre-commit hooks (via pre-commit framework) also use `exec` — container must be up

## Architecture

```
server.py (FastAPI + APScheduler)
  → main.py (pipeline orchestrator)
    → scraper/regal.py (Playwright + stealth)
    → enrichment/tmdb.py (search + details + US release dates)
    → filters.py (exclude patterns, rerelease detection)
    → email_sender/template.py (HTML render)
    → email_sender/acs.py (Azure Communication Services)
    → state.py (JSON file diff)
```

## Key Design Decisions

- No OMDB, no scores in email — removed entirely
- No "special screenings" section — movies are either new or rerelease
- Rerelease detection uses **US theatrical release date** from TMDB (not generic release_date which is often a festival premiere)
- Display year after title uses **earliest TMDB release_date** (separate from rerelease logic)
- Email shows runtime and MPAA rating beneath title
- `/trigger` endpoint requires Bearer token auth (`TRIGGER_API_KEY`)
- State saved last in pipeline for retry safety
- playwright-stealth **v2** (v1 uses deprecated pkg_resources)

## Infrastructure

- Runs on Raspberry Pi (DietPi) as a Docker container
- GHCR for container images (multi-platform: amd64 + arm64)
- GitHub Actions builds and pushes image on push to main or workflow_dispatch
- CI workflow runs on PRs to main and updates/dependencies
- Dependabot for dependency updates (PRs target updates/dependencies branch)
- Pi polls for new images via `scripts/update.sh` cron job
- `docker-compose.prod.yml` for production, `docker-compose.yml` for local dev
- ACS (Azure Communication Services) for email delivery

## Testing

```
task test:unit    # 33 unit tests, runs in container
task test         # All tests including integration (needs network + Playwright)
```

Tests use respx for mocking httpx. Config tests may be affected by .env file — use `_env_file=None` or monkeypatch to isolate.
