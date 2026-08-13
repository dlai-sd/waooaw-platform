FROM python:3.12-slim AS dependencies
WORKDIR /install
COPY src/professional-runtime/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/packages -r requirements.txt

FROM python:3.12-slim
RUN groupadd --system waooaw && useradd --system --gid waooaw waooaw
WORKDIR /app
COPY --from=dependencies /install/packages /usr/local
COPY --chown=waooaw:waooaw src/professional-runtime/ .
USER waooaw
EXPOSE 5003
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5003"]