// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R007, WC149-R008, WC149-R009
// constitutional_basis: C-023, C-059, C-063, C-083, C-084

using System.Text.Json;
using FluentAssertions;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.Extensions.Logging;
using Npgsql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class ProviderConnectionServiceFixture : IAsyncLifetime
{
    internal ProviderRegistryDatabase Database { get; private set; } = null!;
    public string AppConnectionString { get; private set; } = null!;

    public async Task InitializeAsync()
    {
        Database = await ProviderRegistryDatabase.CreateAsync();
        await Database.ExecuteAsync(
            "ALTER ROLE business_app LOGIN PASSWORD 'synthetic-app-password'; GRANT USAGE ON SCHEMA business TO business_app;"
        );
        AppConnectionString = new NpgsqlConnectionStringBuilder(Database.ConnectionString)
        {
            Username = "business_app",
            Password = "synthetic-app-password",
        }.ConnectionString;
    }

    public async Task DisposeAsync() => await Database.DisposeAsync();
}

public sealed class ProviderConnectionServiceTests(ProviderConnectionServiceFixture fixture)
    : IClassFixture<ProviderConnectionServiceFixture>
{
    private const string AppSecret = "synthetic-app-secret-value";
    private const string PageToken = "synthetic-page-token-value";
    private const string UserToken = "synthetic-user-token-value";

    private readonly Guid _tenant = Guid.NewGuid();
    private readonly Guid _actor = Guid.NewGuid();
    private readonly FakeVault _vault = new();
    private readonly FakeGraph _graph = new();
    private readonly FakeClock _clock = new();
    private readonly CapturingLogger _logger = new();

    private ProviderConnectionService Service(bool configured = true)
    {
        var options = new MetaConnectionOptions
        {
            RedirectUri = configured ? "https://app.waooaw.test/api/provider-connections/meta/callback" : "",
        };
        _vault.Secrets["provider-meta-ref"] = $$"""{"appId":"1234567890","appSecret":"{{AppSecret}}"}""";
        return new ProviderConnectionService(
            new PooledDbContextFactory<CustomerConnectionsDbContext>(
                new DbContextOptionsBuilder<CustomerConnectionsDbContext>()
                    .UseNpgsql(fixture.AppConnectionString)
                    .Options
            ),
            _vault,
            new FakeResolver(),
            _graph,
            options,
            _clock,
            _logger
        );
    }

    private static string StateOf(ProviderConnectionStart start) =>
        System.Web.HttpUtility.ParseQueryString(new Uri(start.AuthorizationUrl).Query)["state"]!;

    private async Task<ProviderConnectionSummary> ConnectAsync(
        ProviderConnectionService service,
        Guid? tenant = null,
        Guid? actor = null
    )
    {
        var start = await service.StartMetaAsync(tenant ?? _tenant, actor ?? _actor, default);
        return await service.CompleteMetaAsync(
            tenant ?? _tenant,
            actor ?? _actor,
            new("auth-code-1", StateOf(start)),
            default
        );
    }

    [Fact]
    public async Task StartBuildsAFacebookDialogUrlAndStoresOnlyTheStateDigest()
    {
        var start = await Service().StartMetaAsync(_tenant, _actor, default);

        var url = new Uri(start.AuthorizationUrl);
        url.Host.Should().Be("www.facebook.com");
        url.Scheme.Should().Be("https");
        start.AuthorizationUrl.Should().Contain("pages_manage_posts").And.NotContain(AppSecret);
        start.ExpiresAt.Should().Be(_clock.GetUtcNow() + TimeSpan.FromMinutes(10));
        var stored = await fixture.Database.ScalarAsync<string>(
            $"SELECT string_agg(state_hash, ',') FROM business.provider_connection_states WHERE tenant_id = '{_tenant}'"
        );
        stored.Should().NotContain(StateOf(start)).And.MatchRegex("^[0-9a-f]{64}$");
    }

    [Fact]
    public async Task StartIsUnavailableWithoutARedirectUri()
    {
        var failure = await Assert.ThrowsAsync<ProviderConnectionException>(() =>
            Service(configured: false).StartMetaAsync(_tenant, _actor, default)
        );

        failure.Status.Should().Be(503);
        failure.Code.Should().Be("CONNECTION_PROVIDER_NOT_CONFIGURED");
    }

    [Fact]
    public async Task CallbackStoresThePageTokenOnlyInTheVaultAndReturnsNoSecrets()
    {
        var service = Service();
        var summary = await ConnectAsync(service);

        summary.Status.Should().Be("CONNECTED");
        summary.AccountId.Should().Be("987654321");
        summary.AccountName.Should().Be("Synthetic Page");
        summary.Scopes.Should().BeEquivalentTo(MetaConnectionOptions.Scopes);
        _vault.Secrets[$"customer-connection-{summary.Id}"].Should().Be(PageToken);
        _graph.ExchangedCodes.Should().Equal("auth-code-1");
        _graph.ExtendedTokens.Should().Equal(UserToken + "-short");

        var output = JsonSerializer.Serialize(summary) + _logger.Text;
        output.Should().NotContain(PageToken).And.NotContain(UserToken).And.NotContain(AppSecret);
        var row = await fixture.Database.ScalarAsync<string>(
            $"SELECT row_to_json(c)::text FROM business.customer_provider_connections c WHERE id = '{summary.Id}'"
        );
        row.Should().NotContain(PageToken).And.NotContain(AppSecret);
    }

    [Fact]
    public async Task AStateCanBeUsedOnlyOnce()
    {
        var service = Service();
        var start = await service.StartMetaAsync(_tenant, _actor, default);
        var request = new ProviderConnectionCallbackRequest("auth-code-1", StateOf(start));
        await service.CompleteMetaAsync(_tenant, _actor, request, default);

        var replay = await Assert.ThrowsAsync<ProviderConnectionException>(() =>
            service.CompleteMetaAsync(_tenant, _actor, request, default)
        );

        replay.Code.Should().Be("CONNECTION_STATE_INVALID");
        _graph.ExchangedCodes.Should().HaveCount(1);
    }

    [Fact]
    public async Task AnExpiredStateIsRefusedBeforeGraphIsCalled()
    {
        var service = Service();
        var start = await service.StartMetaAsync(_tenant, _actor, default);
        _clock.Advance(TimeSpan.FromMinutes(10) + TimeSpan.FromSeconds(1));

        var failure = await Assert.ThrowsAsync<ProviderConnectionException>(() =>
            service.CompleteMetaAsync(
                _tenant,
                _actor,
                new("auth-code-1", StateOf(start)),
                default
            )
        );

        failure.Code.Should().Be("CONNECTION_STATE_INVALID");
        _graph.ExchangedCodes.Should().BeEmpty();
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task AStateIsBoundToItsTenantAndActor(bool otherTenant)
    {
        var service = Service();
        var start = await service.StartMetaAsync(_tenant, _actor, default);

        var failure = await Assert.ThrowsAsync<ProviderConnectionException>(() =>
            service.CompleteMetaAsync(
                otherTenant ? Guid.NewGuid() : _tenant,
                otherTenant ? _actor : Guid.NewGuid(),
                new("auth-code-1", StateOf(start)),
                default
            )
        );

        failure.Code.Should().Be("CONNECTION_STATE_INVALID");
        _graph.ExchangedCodes.Should().BeEmpty();
    }

    [Theory]
    [InlineData("short", "auth-code-1")]
    [InlineData("", "")]
    public async Task MalformedCallbackBodiesAreRefusedWithoutTouchingState(string state, string code)
    {
        var failure = await Assert.ThrowsAsync<ProviderConnectionException>(() =>
            Service().CompleteMetaAsync(_tenant, _actor, new(code, state), default)
        );

        failure.Code.Should().Be("CONNECTION_INVALID");
    }

    [Fact]
    public async Task ReconnectingTheSamePageKeepsTheConnectionAndAddsASecretVersion()
    {
        var service = Service();
        var first = await ConnectAsync(service);
        var versionBefore = await fixture.Database.ScalarAsync<string>(
            $"SELECT secret_version FROM business.customer_provider_connections WHERE id = '{first.Id}'"
        );

        var second = await ConnectAsync(service);

        second.Id.Should().Be(first.Id);
        (await service.ListAsync(_tenant, default)).Should().ContainSingle();
        var versionAfter = await fixture.Database.ScalarAsync<string>(
            $"SELECT secret_version FROM business.customer_provider_connections WHERE id = '{first.Id}'"
        );
        versionAfter.Should().NotBe(versionBefore);
    }

    [Fact]
    public async Task ListShowsOnlyTheCallersTenant()
    {
        var service = Service();
        var mine = await ConnectAsync(service);
        await ConnectAsync(service, Guid.NewGuid());

        var listed = await service.ListAsync(_tenant, default);

        listed.Should().ContainSingle().Which.Id.Should().Be(mine.Id);
        (await service.ListAsync(Guid.NewGuid(), default)).Should().BeEmpty();
    }

    [Fact]
    public async Task RevokeDeletesTheSecretIsIdempotentAndIsInvisibleToOtherTenants()
    {
        var service = Service();
        var connection = await ConnectAsync(service);

        var other = await Assert.ThrowsAsync<ProviderConnectionException>(() =>
            service.RevokeAsync(Guid.NewGuid(), _actor, connection.Id, default)
        );
        other.Status.Should().Be(404);
        _vault.Secrets.Should().ContainKey($"customer-connection-{connection.Id}");

        await service.RevokeAsync(_tenant, _actor, connection.Id, default);
        await service.RevokeAsync(_tenant, _actor, connection.Id, default);

        _vault.Secrets.Should().NotContainKey($"customer-connection-{connection.Id}");
        _vault.Deleted.Should().ContainSingle();
        (await service.ListAsync(_tenant, default)).Single().Status.Should().Be("REVOKED");
        var revoked = await Assert.ThrowsAsync<ProviderConnectionException>(() =>
            service.PublishAsync(_tenant, _actor, connection.Id, Publish("hello"), default)
        );
        revoked.Code.Should().Be("CONNECTION_REVOKED");
    }

    [Fact]
    public async Task PublishReadsTheTokenFromTheVaultAtCallTimeAndPostsToThePage()
    {
        var service = Service();
        var connection = await ConnectAsync(service);
        _vault.Reads.Clear();

        var result = await service.PublishAsync(
            _tenant,
            _actor,
            connection.Id,
            Publish("Hello from WAOOAW"),
            default
        );

        result.ProviderPostId.Should().Be("987654321_555");
        _graph.Published.Should().ContainSingle().Which.Should().Be(("987654321", PageToken, "Hello from WAOOAW"));
        _vault.Reads.Should().Contain($"customer-connection-{connection.Id}");
        (JsonSerializer.Serialize(result) + _logger.Text)
            .Should()
            .NotContain(PageToken)
            .And.NotContain(AppSecret);
    }

    [Theory]
    [InlineData(null, "hello", "CONNECTION_APPROVAL_REQUIRED")]
    [InlineData(false, "hello", "CONNECTION_APPROVAL_REQUIRED")]
    [InlineData(true, "", "CONNECTION_INVALID")]
    [InlineData(true, "   ", "CONNECTION_INVALID")]
    [InlineData(true, null, "CONNECTION_INVALID")]
    public async Task PublishNeedsLiteralApprovalAndAUsableMessage(
        bool? approved,
        string? message,
        string code
    )
    {
        var service = Service();
        var connection = await ConnectAsync(service);

        var failure = await Assert.ThrowsAsync<ProviderConnectionException>(() =>
            service.PublishAsync(
                _tenant,
                _actor,
                connection.Id,
                new(message, approved, null),
                default
            )
        );

        failure.Status.Should().Be(400);
        failure.Code.Should().Be(code);
        _graph.Published.Should().BeEmpty();
    }

    [Fact]
    public async Task PublishAcceptsTheLimitAndRefusesOneCharacterMore()
    {
        var service = Service();
        var connection = await ConnectAsync(service);

        await service.PublishAsync(_tenant, _actor, connection.Id, Publish(new string('a', 2000)), default);
        var failure = await Assert.ThrowsAsync<ProviderConnectionException>(() =>
            service.PublishAsync(_tenant, _actor, connection.Id, Publish(new string('a', 2001)), default)
        );

        failure.Code.Should().Be("CONNECTION_INVALID");
        _graph.Published.Should().HaveCount(1);
    }

    [Fact]
    public async Task AGraphAuthErrorMarksTheConnectionNeedsRepairAndStopsFurtherPublishing()
    {
        var service = Service();
        var connection = await ConnectAsync(service);
        _graph.PublishFailure = MetaGraphFailure.AuthRejected;

        var failure = await Assert.ThrowsAsync<ProviderConnectionException>(() =>
            service.PublishAsync(_tenant, _actor, connection.Id, Publish("hello"), default)
        );

        failure.Status.Should().Be(409);
        failure.Code.Should().Be("CONNECTION_NEEDS_REPAIR");
        (await service.ListAsync(_tenant, default)).Single().Status.Should().Be("NEEDS_REPAIR");
        _graph.PublishFailure = null;
        var again = await Assert.ThrowsAsync<ProviderConnectionException>(() =>
            service.PublishAsync(_tenant, _actor, connection.Id, Publish("hello"), default)
        );
        again.Code.Should().Be("CONNECTION_NEEDS_REPAIR");
        _graph.Published.Should().BeEmpty();
        failure.Message.Should().NotContain(PageToken);
    }

    [Fact]
    public async Task ReconnectingARepairNeededPageRestoresIt()
    {
        var service = Service();
        var connection = await ConnectAsync(service);
        _graph.PublishFailure = MetaGraphFailure.AuthRejected;
        await Assert.ThrowsAsync<ProviderConnectionException>(() =>
            service.PublishAsync(_tenant, _actor, connection.Id, Publish("hello"), default)
        );
        _graph.PublishFailure = null;

        var repaired = await ConnectAsync(service);

        repaired.Id.Should().Be(connection.Id);
        repaired.Status.Should().Be("CONNECTED");
    }

    [Fact]
    public async Task AMissingVaultSecretMeansTheConnectionNeedsRepair()
    {
        var service = Service();
        var connection = await ConnectAsync(service);
        _vault.Secrets.Remove($"customer-connection-{connection.Id}");

        var failure = await Assert.ThrowsAsync<ProviderConnectionException>(() =>
            service.PublishAsync(_tenant, _actor, connection.Id, Publish("hello"), default)
        );

        failure.Code.Should().Be("CONNECTION_NEEDS_REPAIR");
        _graph.Published.Should().BeEmpty();
    }

    [Theory]
    [InlineData(MetaGraphFailure.Rejected, 502, "CONNECTION_PUBLISH_REJECTED")]
    [InlineData(MetaGraphFailure.Unavailable, 503, "CONNECTION_PROVIDER_UNAVAILABLE")]
    public async Task OtherGraphFailuresAreMappedWithoutChangingTheConnection(
        MetaGraphFailure graphFailure,
        int status,
        string code
    )
    {
        var service = Service();
        var connection = await ConnectAsync(service);
        _graph.PublishFailure = graphFailure;

        var failure = await Assert.ThrowsAsync<ProviderConnectionException>(() =>
            service.PublishAsync(_tenant, _actor, connection.Id, Publish("hello"), default)
        );

        failure.Status.Should().Be(status);
        failure.Code.Should().Be(code);
        (await service.ListAsync(_tenant, default)).Single().Status.Should().Be("CONNECTED");
    }

    [Fact]
    public async Task APublishRequestForAnotherTenantsConnectionIsNotFound()
    {
        var service = Service();
        var connection = await ConnectAsync(service);

        var failure = await Assert.ThrowsAsync<ProviderConnectionException>(() =>
            service.PublishAsync(Guid.NewGuid(), _actor, connection.Id, Publish("hello"), default)
        );

        failure.Status.Should().Be(404);
        _graph.Published.Should().BeEmpty();
    }

    [Fact]
    public async Task TooManyLiveStatesForOneActorAreRefused()
    {
        var service = Service();
        for (var i = 0; i < 10; i++)
            await service.StartMetaAsync(_tenant, _actor, default);

        var failure = await Assert.ThrowsAsync<ProviderConnectionException>(() =>
            service.StartMetaAsync(_tenant, _actor, default)
        );

        failure.Status.Should().Be(429);
        await service.StartMetaAsync(_tenant, Guid.NewGuid(), default);
    }

    [Fact]
    public async Task TheDatabaseHidesOtherTenantsRowsFromTheApplicationRole()
    {
        var connection = await ConnectAsync(Service());
        await using var db = new NpgsqlConnection(fixture.AppConnectionString);
        await db.OpenAsync();

        async Task<long> CountAsync(string tenant)
        {
            await using var transaction = await db.BeginTransactionAsync();
            await using var set = new NpgsqlCommand(
                "SELECT set_config('app.current_tenant_id', @tenant, true)",
                db,
                transaction
            );
            set.Parameters.AddWithValue("tenant", tenant);
            await set.ExecuteNonQueryAsync();
            await using var count = new NpgsqlCommand(
                "SELECT count(*) FROM business.customer_provider_connections",
                db,
                transaction
            );
            return (long)(await count.ExecuteScalarAsync())!;
        }

        (await CountAsync(_tenant.ToString())).Should().Be(1);
        (await CountAsync(Guid.NewGuid().ToString())).Should().Be(0);
        (await CountAsync("")).Should().Be(0);
        connection.Id.Should().NotBeEmpty();
    }

    [Fact]
    public async Task TheApplicationRoleCannotRewriteTheSecretNameOrDeleteConnections()
    {
        var connection = await ConnectAsync(Service());
        await using var db = new NpgsqlConnection(fixture.AppConnectionString);
        await db.OpenAsync();

        foreach (
            var sql in new[]
            {
                $"UPDATE business.customer_provider_connections SET secret_name = 'customer-connection-{Guid.NewGuid()}' WHERE id = '{connection.Id}'",
                "DELETE FROM business.customer_provider_connections",
            }
        )
        {
            await using var command = new NpgsqlCommand(sql, db);
            var failure = await Assert.ThrowsAsync<PostgresException>(() =>
                command.ExecuteNonQueryAsync()
            );
            failure.SqlState.Should().Be(PostgresErrorCodes.InsufficientPrivilege);
        }
    }

    private static ProviderConnectionPublishRequest Publish(string message) =>
        new(message, true, "approved by the owner");

    private sealed class FakeResolver : IProviderCredentialResolver
    {
        public Task<ResolvedProviderCredential?> ResolveAsync(string providerName, CancellationToken ct) =>
            Task.FromResult<ResolvedProviderCredential?>(
                providerName == "meta"
                    ? new("meta", "provider-meta-ref", "v1", "bearer")
                    : null
            );
    }

    private sealed class FakeVault : ISecretVault
    {
        private int _counter;

        public Dictionary<string, string> Secrets { get; } = [];
        public List<string> Deleted { get; } = [];
        public List<string> Reads { get; } = [];

        public Task<string> SetSecretAsync(string secretName, string value, CancellationToken ct)
        {
            Secrets[secretName] = value;
            return Task.FromResult($"version{++_counter:D8}");
        }

        public Task<string?> GetSecretAsync(string secretName, string? version, CancellationToken ct)
        {
            Reads.Add(secretName);
            return Task.FromResult(Secrets.GetValueOrDefault(secretName));
        }

        public Task DeleteSecretAsync(string secretName, CancellationToken ct)
        {
            Deleted.Add(secretName);
            Secrets.Remove(secretName);
            return Task.CompletedTask;
        }
    }

    private sealed class FakeGraph : IMetaGraphClient
    {
        public List<string> ExchangedCodes { get; } = [];
        public List<string> ExtendedTokens { get; } = [];
        public List<(string PageId, string Token, string Message)> Published { get; } = [];
        public MetaGraphFailure? PublishFailure { get; set; }

        public Task<string> ExchangeCodeAsync(
            string appId,
            string appSecret,
            string redirectUri,
            string code,
            CancellationToken ct
        )
        {
            ExchangedCodes.Add(code);
            return Task.FromResult(UserToken + "-short");
        }

        public Task<string> ExtendUserTokenAsync(
            string appId,
            string appSecret,
            string userToken,
            CancellationToken ct
        )
        {
            ExtendedTokens.Add(userToken);
            return Task.FromResult(UserToken);
        }

        public Task<IReadOnlyList<MetaPage>> ListPagesAsync(string userToken, CancellationToken ct) =>
            Task.FromResult<IReadOnlyList<MetaPage>>([new("987654321", "Synthetic Page", PageToken)]);

        public Task<string> PublishAsync(
            string pageId,
            string pageToken,
            string message,
            CancellationToken ct
        )
        {
            if (PublishFailure is { } failure)
                throw new MetaGraphException(failure);
            Published.Add((pageId, pageToken, message));
            return Task.FromResult("987654321_555");
        }
    }

    private sealed class FakeClock : TimeProvider
    {
        private DateTimeOffset _now = DateTimeOffset.UtcNow;

        public override DateTimeOffset GetUtcNow() => _now;

        public void Advance(TimeSpan by) => _now += by;
    }

    private sealed class CapturingLogger : ILogger<ProviderConnectionService>
    {
        private readonly List<string> _lines = [];

        public string Text => string.Join('\n', _lines);

        public IDisposable? BeginScope<TState>(TState state)
            where TState : notnull => null;

        public bool IsEnabled(LogLevel logLevel) => true;

        public void Log<TState>(
            LogLevel logLevel,
            EventId eventId,
            TState state,
            Exception? exception,
            Func<TState, Exception?, string> formatter
        ) => _lines.Add(formatter(state, exception) + exception);
    }
}
