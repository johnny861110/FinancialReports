FROM python:3.12-slim

# Mirrors the CI install path (uv + uv.lock) so the image resolves the same
# dependency set the gates run against.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/usr/local

# Dependencies first so source edits do not invalidate the dependency layer.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-dev

COPY src/ ./src/
RUN uv sync --frozen --no-dev

EXPOSE 8010

CMD ["uvicorn", "src.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8010"]
