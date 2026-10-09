# Implements: architecture/reference/components/dma-employment-conformance-work-component.md §17, §20
# Constitutional basis: C-035, C-059, C-071, C-079

FROM python:3.12-alpine@sha256:4c47124a8391cb7a9f571164147d154777cf012a4ece5f86097130d7a4478111

RUN apk upgrade --no-cache \
    && addgroup -S adapter && adduser -S -G adapter -h /app adapter \
    && pip install --no-cache-dir fastapi==0.135.1 uvicorn==0.34.0

WORKDIR /app
COPY --chown=adapter:adapter agent-adapters/runtime_contract/ /app/runtime_contract/
COPY --chown=adapter:adapter digital-marketing-agent/digital_marketing/ /app/digital_marketing/
COPY --chown=adapter:adapter digital-marketing-agent/contracts/ /app/contracts/

USER adapter
EXPOSE 8443
CMD ["uvicorn", "digital_marketing.service:app", "--host", "0.0.0.0", "--port", "8443", "--no-access-log"]