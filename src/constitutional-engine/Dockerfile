# Implements: architecture/reference/components/constitutional-engine.md §Runtime Requirements (for Dockerfile)
# Constitutional basis: C-059 (Implementation Traceability)
FROM mcr.microsoft.com/dotnet/sdk:9.0@sha256:01fabc4758d1d74e39eda700c8463dae6241a61481f973683692ddcb59a5eeb7 AS build
WORKDIR /src
COPY src/constitutional-engine/constitutional-engine.csproj .
RUN dotnet restore --runtime linux-musl-x64
COPY src/constitutional-engine/ .
RUN dotnet publish --configuration Release --runtime linux-musl-x64 \
    --self-contained false --no-restore --output /app/publish

FROM golang:1.26.7-alpine@sha256:28d89ee9cc0ff9fec75c82ca201e6bf7fdf9a679d4b7b24dfa04f2bb766bb468 AS health-probe
ARG GRPC_HEALTH_PROBE_COMMIT=b5fef775b4ec749eefb19fb00787089ec9a772d5
ARG GRPC_GO_VERSION=v1.83.2
RUN apk add --no-cache git \
    && git clone https://github.com/grpc-ecosystem/grpc-health-probe.git /src/grpc-health-probe \
    && cd /src/grpc-health-probe \
    && git checkout "${GRPC_HEALTH_PROBE_COMMIT}" \
    && go get "google.golang.org/grpc@${GRPC_GO_VERSION}" \
    && CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /grpc_health_probe .

FROM mcr.microsoft.com/dotnet/aspnet:9.0@sha256:2680706c9656fafe34876446d694fd25077fd0b5da478f38d56073ac6c21d37e
RUN apt-get update \
    && apt-get upgrade --yes \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system waooaw \
    && useradd --system --gid waooaw waooaw
WORKDIR /app
COPY --from=build --chown=waooaw:waooaw /app/publish .
COPY --from=health-probe /grpc_health_probe /usr/local/bin/grpc_health_probe
USER waooaw
EXPOSE 5002
ENTRYPOINT ["dotnet", "ConstitutionalEngine.dll"]