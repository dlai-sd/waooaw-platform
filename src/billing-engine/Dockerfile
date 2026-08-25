# Implements: architecture/reference/agents/platform-it-expert-agent.md Skill 17
# Constitutional basis: C-059 (Implementation Traceability)
FROM python:3.12-slim-bookworm AS dependencies
WORKDIR /install
COPY src/billing-engine/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/packages -r requirements.txt

FROM python:3.12-slim-bookworm
RUN groupadd --system waooaw && useradd --system --gid waooaw waooaw
WORKDIR /app
COPY --from=dependencies /install/packages /usr/local
COPY --chown=waooaw:waooaw src/billing-engine/ .
COPY --chown=waooaw:waooaw architecture/reference/proto/constitutional_service.proto ./proto/constitutional_service.proto
USER waooaw
RUN DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/waooaw \
	REDIS_URL=redis://localhost:6379/0 \
	OPS_AUTH_TOKEN=build-validation \
	RAZORPAY_KEY_ID=build-validation \
	RAZORPAY_KEY_SECRET=build-validation \
	RAZORPAY_WEBHOOK_SECRET=build-validation \
	CONSTITUTIONAL_ENGINE_ADDRESS=localhost:5002 \
	BILLING_CONTRACT_ID=build-validation \
	python -c "import main"
EXPOSE 8140
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8140"]