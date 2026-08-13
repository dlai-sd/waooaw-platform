FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src
COPY src/business-platform/business-platform.csproj .
RUN dotnet restore --runtime linux-musl-x64
COPY src/business-platform/ .
RUN dotnet publish --configuration Release --runtime linux-musl-x64 \
    --self-contained false --no-restore --output /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:9.0
RUN apt-get update \
    && apt-get install --yes --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system waooaw \
    && useradd --system --gid waooaw waooaw
WORKDIR /app
COPY --from=build --chown=waooaw:waooaw /app/publish .
USER waooaw
EXPOSE 5001
ENTRYPOINT ["dotnet", "BusinessPlatform.dll"]