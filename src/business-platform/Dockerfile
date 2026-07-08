# Business Platform — Dockerfile
FROM mcr.microsoft.com/dotnet/sdk:9.0-alpine AS restore
WORKDIR /src
COPY BusinessPlatform.csproj .
RUN dotnet restore --runtime linux-musl-x64

FROM restore AS build
COPY . .
RUN dotnet publish -c Release --runtime linux-musl-x64 --self-contained false --no-restore -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:9.0-alpine AS runtime
RUN addgroup -S waooaw && adduser -S waooaw -G waooaw
WORKDIR /app
COPY --from=build /app/publish .
USER waooaw
EXPOSE 5001
ENTRYPOINT ["dotnet", "BusinessPlatform.dll"]
