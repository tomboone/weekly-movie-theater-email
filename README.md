# Weekly Movie Theater Email

A pipeline that checks what movies are showing at your local Regal theater each week, identifies new releases, enriches them with metadata from TMDB, and sends you a formatted HTML email.

Runs as a Docker container with an internal scheduler (Friday 10 AM ET). Runs on `kumadrome`, the home server (a 2011 Mac mini on Ubuntu, on a residential connection; it replaced the Raspberry Pi on 2026-10-17).

## Setup

1. Copy `.env.example` to `.env` and fill in your values
2. `task up` to start the infra and dev container
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
| `KUMA_PUSH_URL` | Optional Uptime Kuma push monitor URL. After every run the app pushes `status=up` with the run time, or `status=down` with the error. Any query string on the URL is replaced. |

## Development

Requires Docker, [go-task](https://taskfile.dev), and [pre-commit](https://pre-commit.com).

Local dev uses the shared `tbc-localdev-infra` stack (Traefik, etc.). The app is accessible at `https://movie-email.localhost`.

```
task up               # Start infra + dev container
task run              # Run the app (in a separate terminal)
task stop             # Stop the dev container
task down             # Remove the dev container
task reset            # Tear down, rebuild, start fresh
task check            # Run all checks (lint, format, typecheck, yaml, tests)
task test             # Run unit tests
task test:integration # Run integration tests (network + Playwright)
task test:all         # Run all tests
task lint             # Ruff check
task lint:fix         # Auto-fix lint issues
task format           # Check code formatting
task format:fix       # Auto-format code
task typecheck        # Run pyright type checker
task shell            # Open a shell in the container
task trigger          # Manually trigger the pipeline
```

### Pre-commit hooks

```
task hooks:install
```

Requires the dev container to be running (`task up`).

## Deployment

The container image is built and pushed to GHCR via GitHub Actions on push to `main` or via `workflow_dispatch`. The image supports both amd64 and arm64.

### Production setup (kumadrome)

1. Clone the repo on the host
2. Copy `.env` with production values
3. `docker compose -f docker-compose.prod.yml up -d`
4. Add a cron job to poll for updates: `*/5 * * * * /path/to/weekly-movie-theater-email/scripts/update.sh`

The container also joins the external Docker network `kuma-push`, which the personal Uptime Kuma stack on the same host creates. Start that stack first, or `up` fails with `network kuma-push declared as external, but could not be found`. Set `KUMA_PUSH_URL=http://uptime-kuma:3001/api/push/<token>` in `.env` (a push monitor with an 8-day heartbeat interval covers the weekly run).

The port is published on `127.0.0.1` only, never the LAN. From a personal-tailnet device, use the Tailscale sidecar (below). From a device off the tailnet, tunnel in: `ssh -L 8000:127.0.0.1:8000 kumadrome`.

Dependabot PRs target `updates/dependencies` for batched merging.

### Tailnet access (Tailscale sidecar)

The `tailscale` service in `docker-compose.prod.yml` is the app's own node on the personal tailnet, `movie-email`, tagged `tag:app`. It serves the app over HTTPS at **https://movie-email.tail1afe5a.ts.net** (`tailscale/serve.json` proxies 443 to `http://app:8000`) and publishes no host port. The node key lives in the `tailscale-state` named volume, so a recreated container rejoins as the same node.

**First start.** The tailnet already has MagicDNS and HTTPS certificates on.

1. In the personal tailnet's admin console, *Settings → Keys → Generate auth key*: **not reusable, not ephemeral**, tagged `tag:app`. An ephemeral node is removed once it goes offline, so after a reboot it would come back as a new node, perhaps `movie-email-1`.
2. If a node named `movie-email` is already listed in *Machines*, remove it first, or the new one comes up as `movie-email-1`.
3. On kumadrome, put the key in `.env` (the prompt keeps it out of shell history; the leading `\n` guards a `.env` with no trailing newline), then start the sidecar:

   ```sh
   cd ~/weekly-movie-theater-email
   git pull
   read -rsp 'Tailscale auth key: ' key && echo
   sed -i '/^TS_AUTHKEY=/d' .env && printf '\nTS_AUTHKEY=%s\n' "$key" >> .env && unset key
   docker compose -f docker-compose.prod.yml config -q
   docker compose -f docker-compose.prod.yml up -d
   docker compose -f docker-compose.prod.yml logs tailscale | tail -20
   ```

4. Blank the key: `sed -i 's/^TS_AUTHKEY=.*/TS_AUTHKEY=/' .env`. `TS_AUTH_ONCE` logs in only while the state volume holds no node key, so the used key is never needed again.
5. From a personal-tailnet device, `curl https://movie-email.tail1afe5a.ts.net/` returns FastAPI's JSON 404 (`{"detail":"Not Found"}`). The first request can take a few seconds while the certificate is issued.

`TS_EXTRA_ARGS` left empty means `--advertise-tags=tag:app`.

**Calling `/trigger` over the tailnet.** From a personal-tailnet device, read the bearer token from kumadrome's `.env`, then post:

```sh
TRIGGER_API_KEY=$(ssh kumadrome "grep '^TRIGGER_API_KEY=' ~/weekly-movie-theater-email/.env | cut -d= -f2-")
curl -X POST -H "Authorization: Bearer $TRIGGER_API_KEY" https://movie-email.tail1afe5a.ts.net/trigger
```

To run for a specific week instead, append the date override to the same URL: `/trigger?date=MM-DD-YYYY`.

**Re-registering if the state volume is lost** (`docker compose down -v`, a volume prune, a new host): the sidecar starts with no node key and, with `TS_AUTHKEY` blank, cannot log in. Remove the old `movie-email` node in *Machines*, then repeat the first-start steps 1, 3 and 4 with a new key.

A 502 shows in `docker compose -f docker-compose.prod.yml logs tailscale` as `proxy error: dial tcp <address>:8000`. If `<address>` is the sidecar's own (`docker compose -f docker-compose.prod.yml exec tailscale hostname -i`), the proxy is dialling itself: a container's own hostname maps to its own address in `/etc/hosts`, which is why the sidecar's `hostname` is `movie-email-tailscale` and must never be `app`.
