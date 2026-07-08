# Constitutional Engine — Dockerfile
# Based on: architecture/reference/dockerfiles/Dockerfile.dotnet-service
# Port 5002 (gRPC, internal only — never exposed externally)

FROM mcr.microsoft.com/dotnet/sdk:9.0-alpine AS restore
WORKDIR /src
COPY ConstitutionalEngine.csproj .
RUN dotnet restore --runtime linux-musl-x64

FROM restore AS build
COPY . .
RUN dotnet publish -c Release --runtime linux-musl-x64 --self-contained false --no-restore -o /app/publish

# grpc_health_probe for gRPC health checks (required for Azure Container Apps)
FROM alpine:3.19 AS grpc-health-probe
ARG GRPC_HEALTH_PROBE_VERSION=v0.4.28
RUN apk add --no-cache wget && \
    wget -qO /grpc_health_probe \
      "https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${GRPC_HEALTH_PROBE_VERSION}/grpc_health_probe-linux-amd64" && \
    chmod +x /grpc_health_probe

FROM mcr.microsoft.com/dotnet/aspnet:9.0-alpine AS runtime
RUN addgroup -S waooaw && adduser -S waooaw -G waooaw
COPY --from=grpc-health-probe /grpc_health_probe /usr/local/bin/grpc_health_probe
WORKDIR /app
COPY --from=build /app/publish .
USER waooaw
EXPOSE 5002
ENTRYPOINT ["dotnet", "ConstitutionalEngine.dll"]
