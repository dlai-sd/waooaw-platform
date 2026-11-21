using System.Collections.Concurrent;
using Npgsql;

namespace Waooaw.BusinessPlatform.Tests;

/// <summary>
/// Drop-in replacement for a per-test <c>PostgreSqlContainer</c>. A test leases an exclusive, freshly reset
/// cluster from a process-wide pool, so the container start-up cost is paid once per concurrent test class
/// instead of once per test. A lease gets its own database and, when requested, its own superuser role;
/// both are removed when the lease is disposed, so tests keep the isolation of a throwaway container.
/// </summary>
internal sealed class PooledPostgresBuilder(string image)
{
    private string _database = "postgres";
    private string _username = "postgres";
    private string _password = "postgres";

    public PooledPostgresBuilder WithDatabase(string database)
    {
        _database = database;
        return this;
    }

    public PooledPostgresBuilder WithUsername(string username)
    {
        _username = username;
        return this;
    }

    public PooledPostgresBuilder WithPassword(string password)
    {
        _password = password;
        return this;
    }

    public PooledPostgres Build() => new(image, _database, _username, _password);
}

internal sealed class PooledPostgres : IAsyncDisposable
{
    private readonly string _image;
    private readonly string _username;
    private readonly string _password;
    private readonly bool _ownsRole;
    private readonly string _database;
    private PostgresCluster? _cluster;
    private string _connectionString = string.Empty;

    internal PooledPostgres(string image, string database, string username, string password)
    {
        _image = image;
        _username = username;
        _password = password;
        _ownsRole = username != PostgresCluster.AdminUser;
        // The bootstrap database is shared by every lease, so a lease asking for it gets a private one.
        _database = database == "postgres" ? $"lease_{Guid.NewGuid():N}" : database;
    }

    public async Task StartAsync()
    {
        if (_cluster is not null)
            return;
        var cluster = await PostgresCluster.AcquireAsync(_image);
        try
        {
            if (_ownsRole)
                await cluster.ExecuteAsync(
                    $"CREATE ROLE {Quote(_username)} SUPERUSER LOGIN PASSWORD '{_password.Replace("'", "''")}'"
                );
            else if (_password != PostgresCluster.AdminPassword)
                await cluster.ExecuteAsync($"ALTER ROLE {Quote(_username)} PASSWORD '{_password.Replace("'", "''")}'");
            await cluster.ExecuteAsync($"CREATE DATABASE {Quote(_database)} OWNER {Quote(_username)}");
        }
        catch
        {
            await cluster.DiscardAsync();
            throw;
        }
        _cluster = cluster;
        _connectionString = new NpgsqlConnectionStringBuilder
        {
            Host = cluster.Host,
            Port = cluster.Port,
            Database = _database,
            Username = _username,
            Password = _password,
        }.ConnectionString;
    }

    public string GetConnectionString() =>
        _cluster is null
            ? throw new InvalidOperationException("The pooled Postgres lease has not been started.")
            : _connectionString;

    public async ValueTask DisposeAsync()
    {
        var cluster = _cluster;
        _cluster = null;
        if (cluster is not null)
            await cluster.ReleaseAsync();
    }

    private static string Quote(string identifier) => "\"" + identifier.Replace("\"", "\"\"") + "\"";
}

internal sealed class PostgresCluster
{
    public const string AdminUser = "postgres";
    public const string AdminPassword = "postgres";
    private static readonly ConcurrentDictionary<string, ConcurrentBag<PostgresCluster>> Idle = new();
    private readonly string _image;
    private readonly Testcontainers.PostgreSql.PostgreSqlContainer _container;

    private PostgresCluster(string image, Testcontainers.PostgreSql.PostgreSqlContainer container)
    {
        _image = image;
        _container = container;
    }

    public string Host => _container.Hostname;

    public int Port => _container.GetMappedPublicPort(5432);

    public static async Task<PostgresCluster> AcquireAsync(string image)
    {
        if (Idle.GetOrAdd(image, _ => new()).TryTake(out var idle))
            return idle;
        // Tests never need durability, so the data directory lives in memory and fsync is off.
        var container = new Testcontainers.PostgreSql.PostgreSqlBuilder(image)
            .WithTmpfsMount("/var/lib/postgresql/data")
            .WithCommand("-c", "fsync=off", "-c", "synchronous_commit=off", "-c", "full_page_writes=off")
            .Build();
        await container.StartAsync();
        return new PostgresCluster(image, container);
    }

    public async Task ExecuteAsync(string sql)
    {
        await using var connection = await OpenAdminAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    public async Task ReleaseAsync()
    {
        try
        {
            NpgsqlConnection.ClearAllPools();
            await ResetAsync();
        }
        catch
        {
            // A cluster that cannot be proven clean is never reused.
            await DiscardAsync();
            return;
        }
        Idle.GetOrAdd(_image, _ => new()).Add(this);
    }

    public async Task DiscardAsync()
    {
        try
        {
            await _container.DisposeAsync();
        }
        catch
        {
            // The container reaper removes it at process exit.
        }
    }

    private async Task ResetAsync()
    {
        await using var connection = await OpenAdminAsync();
        await RunAsync(
            connection,
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname IS NOT NULL AND pid <> pg_backend_pid()"
        );
        foreach (
            var database in await ListAsync(
                connection,
                "SELECT datname FROM pg_database WHERE datname NOT IN ('postgres', 'template0', 'template1')"
            )
        )
            await RunAsync(connection, $"DROP DATABASE \"{database}\" WITH (FORCE)");
        foreach (
            var role in await ListAsync(
                connection,
                "SELECT rolname FROM pg_roles WHERE rolname NOT LIKE 'pg\\_%' AND rolname <> 'postgres'"
            )
        )
        {
            await RunAsync(connection, $"DROP OWNED BY \"{role}\"");
            await RunAsync(connection, $"DROP ROLE \"{role}\"");
        }
        await RunAsync(connection, $"ALTER ROLE {AdminUser} PASSWORD '{AdminPassword}'");
        var leftovers = await ListAsync(
            connection,
            """
            SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast') AND c.relkind IN ('r', 'v', 'm', 'S', 'f')
            """
        );
        if (leftovers.Count > 0)
            throw new InvalidOperationException("The bootstrap database holds test objects.");
    }

    private async Task<NpgsqlConnection> OpenAdminAsync()
    {
        var connection = new NpgsqlConnection(
            new NpgsqlConnectionStringBuilder
            {
                Host = Host,
                Port = Port,
                Database = "postgres",
                Username = AdminUser,
                Password = AdminPassword,
                Pooling = false,
            }.ConnectionString
        );
        await connection.OpenAsync();
        return connection;
    }

    private static async Task RunAsync(NpgsqlConnection connection, string sql)
    {
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private static async Task<List<string>> ListAsync(NpgsqlConnection connection, string sql)
    {
        var values = new List<string>();
        await using var command = new NpgsqlCommand(sql, connection);
        await using var reader = await command.ExecuteReaderAsync();
        while (await reader.ReadAsync())
            values.Add(reader.GetString(0));
        return values;
    }
}
