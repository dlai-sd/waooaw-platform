# AI Runtime — Dockerfile
FROM python:3.12-slim AS deps
WORKDIR /app
RUN pip install --no-cache-dir uv==0.4.0
COPY pyproject.toml .
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime
RUN groupadd -r waooaw && useradd -r -g waooaw waooaw
WORKDIR /app
COPY --from=deps /app/.venv .venv
COPY --chown=waooaw:waooaw . .
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
USER waooaw
EXPOSE 5004
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5004"]
