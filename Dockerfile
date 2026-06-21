FROM python:3.12-alpine AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-install-project --no-dev

COPY . .
RUN uv sync --frozen --no-dev

FROM python:3.12-alpine AS runtime

RUN apk add --no-cache ca-certificates

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY --from=builder /app/main.py .
COPY --from=builder /app/settings.py .
COPY --from=builder /app/interfaces ./interfaces
COPY --from=builder /app/models ./models
COPY --from=builder /app/utils ./utils

CMD ["python", "main.py"]
