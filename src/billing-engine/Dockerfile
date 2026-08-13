FROM python:3.12-slim AS dependencies
WORKDIR /install
COPY src/billing-engine/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/packages -r requirements.txt

FROM python:3.12-slim
RUN groupadd --system waooaw && useradd --system --gid waooaw waooaw
WORKDIR /app
COPY --from=dependencies /install/packages /usr/local
COPY --chown=waooaw:waooaw src/billing-engine/ .
COPY --chown=waooaw:waooaw architecture/reference/proto/constitutional_service.proto ./proto/constitutional_service.proto
USER waooaw
EXPOSE 8140
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8140"]