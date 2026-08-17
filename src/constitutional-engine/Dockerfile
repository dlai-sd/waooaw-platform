FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src
COPY src/constitutional-engine/constitutional-engine.csproj .
RUN dotnet restore --runtime linux-musl-x64
COPY src/constitutional-engine/ .
RUN dotnet publish --configuration Release --runtime linux-musl-x64 \
    --self-contained false --no-restore --output /app/publish

FROM alpine:3.20 AS health-probe
ARG GRPC_HEALTH_PROBE_VERSION=v0.4.55
RUN wget -qO /grpc_health_probe \
    "https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${GRPC_HEALTH_PROBE_VERSION}/grpc_health_probe-linux-amd64" \
    && chmod +x /grpc_health_probe

FROM mcr.microsoft.com/dotnet/aspnet:9.0
RUN groupadd --system waooaw && useradd --system --gid waooaw waooaw
WORKDIR /app
COPY --from=build --chown=waooaw:waooaw /app/publish .
COPY --from=health-probe /grpc_health_probe /usr/local/bin/grpc_health_probe
USER waooaw
EXPOSE 5002
ENTRYPOINT ["dotnet", "ConstitutionalEngine.dll"]