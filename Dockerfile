FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN addgroup --system tenderpulse \
    && adduser --system --ingroup tenderpulse --home /app tenderpulse

COPY --chown=tenderpulse:tenderpulse pyproject.toml uv.lock ./
COPY --chown=tenderpulse:tenderpulse src ./src
COPY --chown=tenderpulse:tenderpulse migrations ./migrations
COPY --chown=tenderpulse:tenderpulse alembic.ini ./
COPY --chown=tenderpulse:tenderpulse certs ./certs
COPY --chown=tenderpulse:tenderpulse docs ./docs

RUN uv sync --frozen --no-dev --no-editable

USER tenderpulse

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=4s --start-period=15s --retries=5 \
  CMD python -c "import json,urllib.request; r=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)); raise SystemExit(0 if r['status']=='ok' else 1)"

CMD ["uvicorn", "tenderpulse.main:app", "--host", "0.0.0.0", "--port", "8000"]
