# Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R004, R035
# Constitutional basis: C-035, C-059, C-071, C-079

FROM python:3.12-alpine@sha256:4c47124a8391cb7a9f571164147d154777cf012a4ece5f86097130d7a4478111

ARG SECURITY_REFRESH=local
RUN test -n "$SECURITY_REFRESH" \
    && apk upgrade --no-cache \
    && addgroup -S adapter && adduser -S -G adapter -h /app adapter \
    && pip install --no-cache-dir fastapi==0.135.1 uvicorn==0.34.0

WORKDIR /app
COPY --chown=adapter:adapter runtime_contract/ /app/runtime_contract/
COPY --chown=adapter:adapter fixture_orchard/ /app/fixture_orchard/

USER adapter
EXPOSE 8443
CMD ["uvicorn", "fixture_orchard.service:create_service_app", "--factory", "--host", "0.0.0.0", "--port", "8443", "--no-access-log"]
