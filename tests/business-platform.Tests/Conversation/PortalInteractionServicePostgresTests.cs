// Implements: work-contracts/WC-096-conversational-customer-portal.md §5
// Implements: work-contracts/WC-105-auth-ui-runtime-defect-repair.md WC105-R015
// constitutional_basis: C-026, C-049, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.Extensions.Options;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class PortalInteractionServicePostgresTests : IAsyncLifetime
{
    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("portal_interactions")
        .WithUsername("test_owner")
        .WithPassword("synthetic-owner-password")
        .Build();

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
        await OwnerAsync("CREATE ROLE business_app; CREATE SCHEMA business;");
        await OwnerAsync(
            await File.ReadAllTextAsync(
                RepositoryPaths.Resolve(
                    "infrastructure/postgres/init/35-wc096-portal-interactions.sql"
                )
            )
        );
    }

    public async Task DisposeAsync() => await _postgres.DisposeAsync();

    [Fact]
    public async Task ListAsync_ConcurrentFirstUseCreatesOneSharedContext()
    {
        var options = new DbContextOptionsBuilder<ConversationStoreDbContext>()
            .UseNpgsql(_postgres.GetConnectionString())
            .Options;
        var service = new PortalInteractionService(
            new PooledDbContextFactory<ConversationStoreDbContext>(options),
            new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) })
            )
        );
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();

        var pages = await Task.WhenAll(
            Enumerable.Range(0, 16).Select(_ =>
                service.ListAsync(tenantId, participantId, null, 40, CancellationToken.None)
            )
        );

        Assert.Single(pages.Select(page => page.ContextId).Distinct());
        Assert.All(pages, page => Assert.Empty(page.Items));
        Assert.Equal(
            1L,
            await OwnerScalarAsync(
                "SELECT count(*) FROM business.portal_interaction_contexts"
            )
        );
    }

    private async Task OwnerAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private async Task<long> OwnerScalarAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        return (long)(await command.ExecuteScalarAsync())!;
    }
}