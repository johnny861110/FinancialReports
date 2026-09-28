FROM python:3.12-slim

# Mirrors the CI install path (uv + uv.lock) so the image resolves the same
# dependency set the gates run against.
COPY --from=ghcr.io/astral-sh/uv:0.9.10 /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/usr/local

# Dependencies first so source edits do not invalidate the dependency layer.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-dev --extra vector --extra pdf

COPY src/ ./src/
RUN uv sync --frozen --no-dev --extra vector --extra pdf

# Run as a non-root user -- the base image doesn't create one by default and
# this service is exposed on a network port. /app/data is where the
# FR_OUTPUT_DIR bind mount (docker-compose.yml) lands, so it needs to exist
# with the right owner before the mount covers it.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8010/health/live', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "src.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8010"]
