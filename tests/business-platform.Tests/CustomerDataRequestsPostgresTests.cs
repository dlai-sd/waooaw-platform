// Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R006
// Constitutional basis: C-023, C-026, C-059, C-063, C-078

using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Services.CustomerDataRequests;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

/// <summary>The customer data request table and its store against the real migration, as the non-owner application role.</summary>
public sealed class CustomerDataRequestsPostgresTests : IAsyncLifetime
{
    private const string Migration =
        "infrastructure/postgres/init/99zzzzzzzz-wc176-01-customer-data-requests.sql";
    private static readonly DateTimeOffset Now = new(2026, 12, 1, 9, 0, 0, TimeSpan.Zero);

    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("data_requests")
        .WithUsername("test_owner")
        .WithPassword("owner-password")
        .Build();

    private PostgresCustomerDataRequests _store = null!;
    private string _appConnection = null!;

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
        await ExecuteAsync(
            "CREATE ROLE bp_owner; CREATE ROLE business_app LOGIN PASSWORD 'app-password'; "
                + "CREATE SCHEMA business AUTHORIZATION bp_owner; GRANT USAGE ON SCHEMA business TO business_app;"
        );
        await ExecuteAsync(await File.ReadAllTextAsync(RepositoryPaths.Resolve(Migration)));
        // Replaying the migration changes nothing (it runs on every deployment).
        await ExecuteAsync(await File.ReadAllTextAsync(RepositoryPaths.Resolve(Migration)));
        _appConnection = new NpgsqlConnectionStringBuilder(_postgres.GetConnectionString())
        {
            Username = "business_app",
            Password = "app-password",
        }.ConnectionString;
        var clock = new Moq.Mock<TimeProvider>();
        clock.Setup(value => value.GetUtcNow()).Returns(Now);
        _store = new PostgresCustomerDataRequests(_appConnection, clock.Object);
    }

    public async Task DisposeAsync() => await _postgres.DisposeAsync();

    private async Task ExecuteAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    [Fact]
    public async Task ARequestIsRecordedOncePerKindAndReplaysReturnTheSameRow()
    {
        var tenant = Guid.NewGuid();
        var key = Guid.NewGuid();

        var (first, created) = await _store.RequestAsync(tenant, "hash", "EXPORT", key, default);
        var (replay, replayCreated) = await _store.RequestAsync(
            tenant,
            "hash",
            "EXPORT",
            key,
            default
        );
        var (otherKey, otherCreated) = await _store.RequestAsync(
            tenant,
            "hash",
            "EXPORT",
            Guid.NewGuid(),
            default
        );
        var (erasure, erasureCreated) = await _store.RequestAsync(
            tenant,
            "hash",
            "ERASURE",
            Guid.NewGuid(),
            default
        );

        Assert.True(created);
        Assert.False(replayCreated);
        Assert.False(otherCreated);
        Assert.True(erasureCreated);
        Assert.Equal(first.RequestId, replay.RequestId);
        Assert.Equal(first.RequestId, otherKey.RequestId);
        Assert.NotEqual(first.RequestId, erasure.RequestId);
        Assert.Equal("RECEIVED", first.State);
        await Assert.ThrowsAsync<ArgumentException>(() =>
            _store.RequestAsync(tenant, "hash", "DELETE", Guid.NewGuid(), default)
        );
    }

    [Fact]
    public async Task ACustomerSeesOnlyTheirOwnRequestsAndTheApplicationRoleSeesNothingWithoutATenant()
    {
        var mine = Guid.NewGuid();
        var theirs = Guid.NewGuid();
        await _store.RequestAsync(mine, "hash", "EXPORT", Guid.NewGuid(), default);
        await _store.RequestAsync(theirs, "hash", "EXPORT", Guid.NewGuid(), default);

        var listed = await _store.ListForCustomerAsync(mine, default);

        Assert.Equal(mine, Assert.Single(listed).TenantId);
        await using var connection = new NpgsqlConnection(_appConnection);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(
            "SELECT count(*) FROM business.customer_data_requests",
            connection
        );
        Assert.Equal(0L, await command.ExecuteScalarAsync());
    }

    [Fact]
    public async Task TheOperatorClosesAnOpenRequestOnceAndTheCustomerSeesTheNote()
    {
        var tenant = Guid.NewGuid();
        var (request, _) = await _store.RequestAsync(
            tenant,
            "hash",
            "ERASURE",
            Guid.NewGuid(),
            default
        );

        Assert.Contains(
            await _store.ListOpenForOperatorAsync(100, default),
            value => value.RequestId == request.RequestId
        );
        var closed = await _store.ResolveAsync(
            request.RequestId,
            completed: false,
            "founder-1",
            "Needs your sign-off first",
            default
        );
        var again = await _store.ResolveAsync(
            request.RequestId,
            completed: true,
            "founder-1",
            "twice",
            default
        );

        Assert.Equal("DECLINED", closed!.State);
        Assert.NotNull(closed.ResolvedAt);
        Assert.Null(again);
        Assert.DoesNotContain(
            await _store.ListOpenForOperatorAsync(100, default),
            value => value.RequestId == request.RequestId
        );
        var seen = Assert.Single(await _store.ListForCustomerAsync(tenant, default));
        Assert.Equal("Needs your sign-off first", seen.ResolutionNote);
        // A closed request frees the slot, so a new one of the same kind can be asked for.
        var (next, nextCreated) = await _store.RequestAsync(
            tenant,
            "hash",
            "ERASURE",
            Guid.NewGuid(),
            default
        );
        Assert.True(nextCreated);
        Assert.NotEqual(request.RequestId, next.RequestId);
    }
}
