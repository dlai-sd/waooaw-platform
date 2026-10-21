# Implements: architecture/reference/components/constitutional-engine.md §Runtime Requirements (for Dockerfile)
# Constitutional basis: C-059 (Implementation Traceability)
FROM mcr.microsoft.com/dotnet/sdk:9.0@sha256:01fabc4758d1d74e39eda700c8463dae6241a61481f973683692ddcb59a5eeb7 AS build
WORKDIR /src
COPY src/constitutional-engine/constitutional-engine.csproj .
RUN dotnet restore --runtime linux-musl-x64
COPY src/constitutional-engine/ .
RUN dotnet publish --configuration Release --runtime linux-musl-x64 \
    --self-contained false --no-restore --output /app/publish

FROM golang:1.26.10-alpine@sha256:9ce231b28998b32e116927c61aa5c406183061d4f3f2d61b292c88e7f6bdf7ca AS health-probe
ARG GRPC_HEALTH_PROBE_COMMIT=b5fef775b4ec749eefb19fb00787089ec9a772d5
ARG GRPC_GO_VERSION=v1.83.2
ARG GOLANG_X_NET_VERSION=v0.60.0
RUN apk add --no-cache git \
    && git clone https://github.com/grpc-ecosystem/grpc-health-probe.git /src/grpc-health-probe \
    && cd /src/grpc-health-probe \
    && git checkout "${GRPC_HEALTH_PROBE_COMMIT}" \
    && go get "google.golang.org/grpc@${GRPC_GO_VERSION}" \
    && go get "golang.org/x/net@${GOLANG_X_NET_VERSION}" \
    && CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /grpc_health_probe .

FROM mcr.microsoft.com/dotnet/aspnet:9.0.21@sha256:4d94cf3204df98d321e8dbf8d6d06e0b34fd136aa75c945abf4390ee07eb30dd
ARG SECURITY_REFRESH=local
RUN test -n "$SECURITY_REFRESH" \
    && apt-get update \
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