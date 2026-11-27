// Implements: work-contracts/WC-175-demo-registration-trial-hire-and-founder-defects.md WC175-R023, R025
// constitutional_basis: C-023, C-026, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services.PlatformApprovals;
using Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.PlatformApprovals;

/// <summary>Runs the real migration and the real store: applying twice is safe, decisions persist, history cannot change.</summary>
public sealed class PlatformProfessionalApprovalPostgresTests : IAsyncLifetime
{
    private const string Migration =
        "infrastructure/postgres/init/99zzzzzzzz-wc175-01-platform-professional-approvals.sql";

    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("platform_approvals")
        .WithUsername("test_owner")
        .WithPassword("synthetic-owner-password")
        .Build();

    private string RuntimeConnectionString =>
        new NpgsqlConnectionStringBuilder(_postgres.GetConnectionString())
        {
            Username = "bp_runtime",
            Password = "synthetic-runtime-password",
        }.ConnectionString;

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
        await ExecuteAsync(
            _postgres.GetConnectionString(),
            """
            CREATE ROLE business_app NOLOGIN;
            CREATE ROLE bp_owner NOLOGIN;
            CREATE ROLE bp_runtime LOGIN PASSWORD 'synthetic-runtime-password' IN ROLE business_app;
            GRANT bp_owner TO test_owner;
            CREATE SCHEMA business AUTHORIZATION bp_owner;
            GRANT USAGE ON SCHEMA business TO business_app;
            """
        );
        var sql = await File.ReadAllTextAsync(RepositoryPaths.Resolve(Migration));
        await ExecuteAsync(_postgres.GetConnectionString(), sql);
        await ExecuteAsync(_postgres.GetConnectionString(), sql);
    }

    public async Task DisposeAsync() => await _postgres.DisposeAsync();

    private static async Task ExecuteAsync(string connectionString, string sql)
    {
        await using var connection = new NpgsqlConnection(connectionString);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private PostgresPlatformProfessionalApprovalStore Store() =>
        new(
            new ConversationFitnessDbFactory(
                new DbContextOptionsBuilder<ConversationStoreDbContext>()
                    .UseNpgsql(RuntimeConnectionString)
                    .Options
            )
        );

    private static PlatformProfessionalApproval Approval(
        string state,
        int version,
        string? reason = null
    ) =>
        new(
            "DIGITAL_MARKETING_LOCAL_SERVICE",
            "1.0.0",
            state,
            "sha256:" + new string('a', 64),
            "ca-demo-business-platform--0000001",
            "founder-1",
            new DateTimeOffset(2026, 12, 1, 9, 0, 0, TimeSpan.Zero),
            reason,
            version
        );

    [Fact]
    public async Task ADecisionPersistsAndIsReadBackExactly()
    {
        var store = Store();
        Assert.Null(await store.GetAsync("DIGITAL_MARKETING_LOCAL_SERVICE", "1.0.0", default));

        Assert.True(await store.SaveAsync(Approval("APPROVED", 1), 0, default));
        Assert.True(
            await store.SaveAsync(Approval("SUSPENDED", 2, "Paused for a review"), 1, default)
        );

        var saved = await store.GetAsync("DIGITAL_MARKETING_LOCAL_SERVICE", "1.0.0", default);
        Assert.Equal("SUSPENDED", saved!.State);
        Assert.Equal(2, saved.StateVersion);
        Assert.Equal("Paused for a review", saved.Reason);
        Assert.Equal("founder-1", saved.DecidedBy);
    }

    [Fact]
    public async Task ASecondWriterWithAStaleVersionIsRefusedAndLeavesNoHistory()
    {
        var store = Store();
        await store.SaveAsync(Approval("APPROVED", 1), 0, default);
        await store.SaveAsync(Approval("SUSPENDED", 2, "Paused for a review"), 1, default);

        Assert.False(await store.SaveAsync(Approval("RETIRED", 2, "Replaced"), 1, default));
        Assert.False(await store.SaveAsync(Approval("APPROVED", 1), 0, default));

        Assert.Equal(
            "SUSPENDED",
            (await store.GetAsync("DIGITAL_MARKETING_LOCAL_SERVICE", "1.0.0", default))!.State
        );
    }

    [Fact]
    public async Task TheHistoryKeepsEveryDecisionAndCannotBeChangedOrDeleted()
    {
        var store = Store();
        await store.SaveAsync(Approval("APPROVED", 1), 0, default);
        await store.SaveAsync(Approval("SUSPENDED", 2, "Paused for a review"), 1, default);

        await using var connection = new NpgsqlConnection(RuntimeConnectionString);
        await connection.OpenAsync();
        await using var count = new NpgsqlCommand(
            "SELECT count(*) FROM business.platform_professional_approval_events WHERE professional_type_id = 'DIGITAL_MARKETING_LOCAL_SERVICE'",
            connection
        );
        Assert.True((long)(await count.ExecuteScalarAsync())! >= 2);

        foreach (
            var statement in new[]
            {
                "UPDATE business.platform_professional_approval_events SET reason = 'edited'",
                "DELETE FROM business.platform_professional_approval_events",
            }
        )
        {
            await using var command = new NpgsqlCommand(statement, connection);
            var refused = await Assert.ThrowsAsync<PostgresException>(() =>
                command.ExecuteNonQueryAsync()
            );
            Assert.True(refused.SqlState is "42501" or "P0001");
        }
    }

    [Fact]
    public async Task TheApplicationRoleCannotDeleteAnApproval()
    {
        await Store().SaveAsync(Approval("APPROVED", 1), 0, default);
        await using var connection = new NpgsqlConnection(RuntimeConnectionString);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(
            "DELETE FROM business.platform_professional_approvals",
            connection
        );

        var refused = await Assert.ThrowsAsync<PostgresException>(() =>
            command.ExecuteNonQueryAsync()
        );

        Assert.Equal("42501", refused.SqlState);
    }
}
