# Project: weekly-movie-theater-email

Python pipeline that scrapes Regal theater showtimes weekly, enriches with TMDB metadata, and sends an HTML email via Azure Communication Services.

## Dev Environment

- **Docker-only** — all commands run inside the container, no local Python/venv
- **uv** for package management (not pip)
- **go-task** for orchestration — see `Taskfile.yml`

### Common commands

```
task build          # Build Docker image
task run            # Start the app
task test           # Run all tests
task test:unit      # Run unit tests only
task check          # Run all checks (ruff, pyright, yamllint, pytest)
task lint           # Ruff check + format
task lint:fix       # Auto-fix ruff issues
task trigger        # curl POST to /trigger (requires TRIGGER_API_KEY in .env)
task trigger -- MM-DD-YYYY  # trigger with date override
task hooks:install  # Set up git pre-commit hooks
```

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
task test:unit    # 26 unit tests, runs in container
task test         # All tests including integration (needs network + Playwright)
```

Tests use respx for mocking httpx. Config tests may be affected by .env file — use `_env_file=None` or monkeypatch to isolate.
