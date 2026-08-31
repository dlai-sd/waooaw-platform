FROM python:3.12.11-slim-bookworm

RUN groupadd --system adapter && useradd --system --gid adapter --home-dir /app adapter \
    && pip install --no-cache-dir fastapi==0.135.1 uvicorn==0.34.0

WORKDIR /app
COPY --chown=adapter:adapter runtime_contract/ /app/runtime_contract/
COPY --chown=adapter:adapter trading/ /app/trading/

USER adapter
EXPOSE 8443
CMD ["uvicorn", "trading.service:app", "--host", "0.0.0.0", "--port", "8443", "--no-access-log"]