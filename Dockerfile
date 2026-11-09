FROM mcr.microsoft.com/playwright/python:v1.64.1-noble

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# The locked runtime dependencies (no dev group), the same versions CI tests, into the system Python.
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-emit-project -o /tmp/requirements.txt \
    && uv pip install --system --no-cache -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt
# Install the browser build that matches the installed playwright package. The base image only carries
# the browsers for its own tag, so a playwright bump that lands before Microsoft publishes the matching
# image (1.64.0, Oct 2026) otherwise fails at launch with "Executable doesn't exist".
RUN playwright install --with-deps chromium

COPY . .

# Run as the base image's unprivileged user (uid 1001). /app/data is the state volume's mount point:
# owning it here gives a new named volume the same owner. A volume created while the image ran as root
# keeps root's ownership and needs a one-time chown (README → Deployment).
RUN mkdir -p /app/data && chown -R pwuser:pwuser /app/data
USER pwuser

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
