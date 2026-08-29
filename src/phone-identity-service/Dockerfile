FROM mcr.microsoft.com/dotnet/sdk:9.0-noble AS build
WORKDIR /src
COPY src/phone-identity-service/phone-identity-service.csproj .
RUN dotnet restore phone-identity-service.csproj
COPY src/phone-identity-service/ .
RUN dotnet publish phone-identity-service.csproj -c Release -o /app --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:9.0-noble
WORKDIR /app
COPY --from=build /app .
ENV ASPNETCORE_URLS=http://0.0.0.0:8137
EXPOSE 8137
USER $APP_UID
ENTRYPOINT ["dotnet", "PhoneIdentityService.dll"]
