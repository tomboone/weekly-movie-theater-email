FROM mcr.microsoft.com/playwright/python:v1.64.1-noble

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml .
RUN uv pip install --system --no-cache -r pyproject.toml
# Install the browser build that matches the installed playwright package. The base image only carries
# the browsers for its own tag, so a playwright bump that lands before Microsoft publishes the matching
# image (1.64.0, Oct 2026) otherwise fails at launch with "Executable doesn't exist".
RUN playwright install --with-deps chromium

COPY . .

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
