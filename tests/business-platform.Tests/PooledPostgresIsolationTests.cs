using Npgsql;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

// Runs alone, after the parallel collections, so no other class can lease the cluster being asserted on.
[CollectionDefinition("PooledPostgresIsolation", DisableParallelization = true)]
public sealed class PooledPostgresIsolationCollection;

[Collection("PooledPostgresIsolation")]
public sealed class PooledPostgresIsolationTests
{
    private const string Image = "postgres:16-alpine";

    [Fact]
    public async Task A_released_lease_leaves_no_roles_databases_or_objects_for_the_next_lease()
    {
        string firstEndpoint;
        await using (var first = new PostgreSqlBuilder(Image).WithDatabase("waooaw").WithUsername("waooaw").WithPassword("pw").Build())
        {
            await first.StartAsync();
            firstEndpoint = Endpoint(first.GetConnectionString());
            await ExecuteAsync(first.GetConnectionString(), "CREATE ROLE leaked_role LOGIN; CREATE TABLE leaked_table (id int)");
        }

        await using var second = new PostgreSqlBuilder(Image).WithDatabase("waooaw").WithUsername("waooaw").WithPassword("pw").Build();
        await second.StartAsync();

        Assert.Equal(firstEndpoint, Endpoint(second.GetConnectionString()));
        Assert.Equal(0L, await ScalarAsync(second.GetConnectionString(), "SELECT count(*) FROM pg_roles WHERE rolname = 'leaked_role'"));
        Assert.Equal(0L, await ScalarAsync(second.GetConnectionString(), "SELECT count(*) FROM pg_class WHERE relname = 'leaked_table'"));
    }

    [Fact]
    public async Task Concurrent_leases_never_share_a_database()
    {
        await using var one = new PostgreSqlBuilder(Image).Build();
        await using var two = new PostgreSqlBuilder(Image).Build();
        await one.StartAsync();
        await two.StartAsync();

        Assert.NotEqual(Database(one.GetConnectionString()), Database(two.GetConnectionString()));
        Assert.NotEqual(Endpoint(one.GetConnectionString()), Endpoint(two.GetConnectionString()));
    }

    private static string Endpoint(string connectionString)
    {
        var builder = new NpgsqlConnectionStringBuilder(connectionString);
        return $"{builder.Host}:{builder.Port}";
    }

    private static string Database(string connectionString) => new NpgsqlConnectionStringBuilder(connectionString).Database!;

    private static async Task ExecuteAsync(string connectionString, string sql)
    {
        await using var connection = new NpgsqlConnection(connectionString);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private static async Task<object?> ScalarAsync(string connectionString, string sql)
    {
        await using var connection = new NpgsqlConnection(connectionString);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        return await command.ExecuteScalarAsync();
    }
}
