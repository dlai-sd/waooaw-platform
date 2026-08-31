# Implements: architecture/agent-runtime-adapter-contract-v1-execution-plan.md §8 ARA-06
# Constitutional basis: C-035, C-059, C-071, C-079

FROM python:3.12-alpine

RUN apk upgrade --no-cache \
    && addgroup -S adapter && adduser -S -G adapter -h /app adapter \
    && pip install --no-cache-dir fastapi==0.135.1 uvicorn==0.34.0

WORKDIR /app
COPY --chown=adapter:adapter runtime_contract/ /app/runtime_contract/
COPY --chown=adapter:adapter trading/ /app/trading/

USER adapter
EXPOSE 8443
CMD ["uvicorn", "trading.service:app", "--host", "0.0.0.0", "--port", "8443", "--no-access-log"]