FROM python:3.12-slim-bookworm AS dependencies
WORKDIR /install
COPY src/ai-runtime/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/packages -r requirements.txt

FROM python:3.12-slim-bookworm
RUN groupadd --system waooaw && useradd --system --gid waooaw waooaw
WORKDIR /app
COPY --from=dependencies /install/packages /usr/local
COPY --chown=waooaw:waooaw src/ai-runtime/ .
USER waooaw
RUN python -c "import main"
EXPOSE 5004
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5004"]