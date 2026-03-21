# Weekly Movie Theater Email

A pipeline that checks what movies are showing at your local Regal theater each week, identifies new releases, enriches them with metadata from TMDB, and sends you a formatted HTML email.

Runs on Azure App Service as a Docker container with an internal scheduler (Friday 10 AM ET).

## Setup

1. Copy `.env.example` to `.env` and fill in your values
2. `task build` to build the Docker image
3. `task run` to start the app
4. `task trigger` to manually run the pipeline

### Required API keys

- **TMDB** — [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api) (free, use the Read Access Token)
- **Azure Communication Services** — connection string from your ACS resource

### Environment variables

| Variable | Description |
|---|---|
| `REGAL_CINEMA_ID` | 4-digit theater ID from the Regal website URL |
| `TMDB_API_KEY` | TMDB Read Access Token (starts with `eyJ...`) |
| `ACS_CONNECTION_STRING` | Azure Communication Services connection string |
| `EMAIL_FROM` | ACS verified sender address |
| `EMAIL_TO` | Recipient email address |
| `EXCLUDE_PATTERNS` | Comma-separated title substrings to exclude (default: `Met Opera,NT Live,Bolshoi Ballet,Fathom,MARS:`) |
| `TRIGGER_API_KEY` | Bearer token for the `/trigger` endpoint |
| `SEND_EMPTY_EMAIL` | Send email even when no new movies (default: `false`) |

## Development

Requires Docker and [go-task](https://taskfile.dev).

```
task check        # Run all checks (lint, typecheck, yaml, tests)
task test:unit    # Run unit tests only
task lint:fix     # Auto-fix lint issues
task shell        # Open a shell in the container
```

### Pre-commit hooks

```
task hooks:install
```

## Deployment

Infrastructure is managed with OpenTofu in `infra/`. Deployment is via GitHub Actions — automatically on push to `main` (for app/infra changes) or manually via `workflow_dispatch`.

Dependabot PRs target `updates/dependencies` for batched merging.
