# ============================================================
# Stage 1 — Builder (instala dependências com uv)
# ============================================================
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Copiar arquivos de dependência primeiro (melhor cache de layers)
COPY pyproject.toml uv.lock /app/

# Instalar dependências (cache de deps separado do código)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# ============================================================
# Stage 2 — Runtime (imagem slim, sem uv)
# ============================================================
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

EXPOSE 8080

WORKDIR /src

# Copiar venv do builder
COPY --from=builder /app/.venv /app/.venv

# Copiar código
COPY src /src/