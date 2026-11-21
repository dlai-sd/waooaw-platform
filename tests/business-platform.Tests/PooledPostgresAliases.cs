// Postgres-backed tests lease a pooled, reset cluster instead of starting a container per test.
// A test that needs a dedicated container (for example init scripts mounted at start-up) names
// Testcontainers.PostgreSql.PostgreSqlBuilder explicitly.
global using PostgreSqlBuilder = Waooaw.BusinessPlatform.Tests.PooledPostgresBuilder;
global using PostgreSqlContainer = Waooaw.BusinessPlatform.Tests.PooledPostgres;
