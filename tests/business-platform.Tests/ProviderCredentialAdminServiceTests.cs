// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R001, WC148-R003, WC148-R004
// constitutional_basis: C-023, C-059, C-063, C-083, C-084

using FluentAssertions;
using Microsoft.Extensions.Logging;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class ProviderCredentialAdminServiceTests : IAsyncLifetime
{
    private const string Secret = "sk-test-SYNTHETIC-credential-value-0123456789";
    private ProviderRegistryDatabase _db = null!;
    private readonly FakeSecretStore _store = new();
    private readonly FakeTester _tester = new();
    private readonly CapturingLogger _logger = new();
    private ProviderCredentialAdminService _service = null!;

    public async Task InitializeAsync()
    {
        _db = await ProviderRegistryDatabase.CreateAsync();
        _service = new ProviderCredentialAdminService(
            _db.Factory(),
            _store,
            _tester,
            TimeProvider.System,
            _logger
        );
    }

    public async Task DisposeAsync() => await _db.DisposeAsync();

    private Task<Guid> IdAsync(string name) =>
        _db.ScalarAsync<Guid>(
            $"SELECT id FROM business.provider_configs WHERE provider_name = '{name}' AND tenant_id IS NULL"
        );

    private async Task<long> CountAsync(string name, string status) =>
        await _db.ScalarAsync<long>(
            $"SELECT count(*) FROM business.provider_credential_versions v JOIN business.provider_configs p ON p.id = v.provider_config_id WHERE p.provider_name = '{name}' AND v.status = '{status}'"
        );

    private void NothingLeaked(Exception? exception = null)
    {
        _logger.Lines.Should().NotContain(line => line.Contains(Secret));
        _logger.Lines.Should().NotContain(line => line.Contains("synthetic-secret"));
        exception?.ToString().Should().NotContain(Secret);
    }

    [Fact]
    public async Task ListShowsSeededProvidersWithNoCredential()
    {
        var providers = await _service.ListAsync(CancellationToken.None);

        providers
            .Select(p => p.ProviderName)
            .Should()
            .BeEquivalentTo("openai", "anthropic", "google", "sarvam");
        providers
            .Should()
            .OnlyContain(p => p.Credential.Status == "NOT_SET" && p.AuthMethod == "API_KEY");
        providers.Single(p => p.ProviderName == "sarvam").HasTestEndpoint.Should().BeFalse();
        providers.Single(p => p.ProviderName == "openai").HasTestEndpoint.Should().BeTrue();
    }

    [Fact]
    public async Task ConfirmOnPassRecordsAnActiveVersionAndWritesTheVault()
    {
        var openai = await IdAsync("openai");

        var saved = await _service.ConfirmAsync(
            openai,
            Secret,
            false,
            "founder-1",
            CancellationToken.None
        );

        saved.Should().Be(saved with { VersionNo = 1, Status = "ACTIVE" });
        _store.Writes.Should().ContainSingle().Which.Name.Should().Be("provider-openai");
        _store.Writes[0].Value.Should().Be(Secret);
        var summary = (await _service.ListAsync(CancellationToken.None)).Single(p =>
            p.ProviderName == "openai"
        );
        summary.Credential.Status.Should().Be("ACTIVE");
        summary.Credential.ActiveVersionNo.Should().Be(1);
        summary.Credential.LastTestOutcome.Should().Be("PASSED");
        (
            await _db.ScalarAsync<string>(
                "SELECT vault_secret_version FROM business.provider_credential_versions"
            )
        )
            .Should()
            .Be("ver0001");
        (
            await _db.ScalarAsync<string>(
                "SELECT created_by_subject FROM business.provider_credential_versions"
            )
        )
            .Should()
            .Be("founder-1");
        NothingLeaked();
    }

    [Fact]
    public async Task ConfirmOnFailedTestWritesNothing()
    {
        _tester.Result = new(ProviderTestOutcomes.Failed, "HTTP 401", 401);
        var openai = await IdAsync("openai");

        var act = async () =>
            await _service.ConfirmAsync(openai, Secret, true, "founder-1", CancellationToken.None);

        var error = (await act.Should().ThrowAsync<ProviderAdminException>()).Which;
        error.Status.Should().Be(422);
        error.Code.Should().Be("PROVIDER_INVALID");
        error.Extras["testDetail"].Should().Be("HTTP 401");
        _store.Writes.Should().BeEmpty();
        (await _db.ScalarAsync<long>("SELECT count(*) FROM business.provider_credential_versions"))
            .Should()
            .Be(0);
        NothingLeaked(error);
    }

    [Fact]
    public async Task UntestableProviderNeedsAcknowledgement()
    {
        _tester.Result = new(ProviderTestOutcomes.NotTestable, "No test endpoint", null);
        var sarvam = await IdAsync("sarvam");

        var refused = async () =>
            await _service.ConfirmAsync(sarvam, Secret, false, "founder-1", CancellationToken.None);
        await refused.Should().ThrowAsync<ProviderAdminException>().Where(e => e.Status == 422);
        _store.Writes.Should().BeEmpty();

        var saved = await _service.ConfirmAsync(
            sarvam,
            Secret,
            true,
            "founder-1",
            CancellationToken.None
        );

        saved.VersionNo.Should().Be(1);
        _store.Writes.Should().ContainSingle();
        (
            await _db.ScalarAsync<string>(
                "SELECT test_outcome FROM business.provider_credential_versions"
            )
        )
            .Should()
            .Be("NOT_TESTABLE");
    }

    [Fact]
    public async Task ConfirmingAgainSupersedesThePreviousVersionAndKeepsOneActive()
    {
        var openai = await IdAsync("openai");
        var first = await _service.ConfirmAsync(
            openai,
            Secret,
            false,
            "founder-1",
            CancellationToken.None
        );

        var second = await _service.ConfirmAsync(
            openai,
            Secret + "-2",
            false,
            "founder-1",
            CancellationToken.None
        );

        second.VersionNo.Should().Be(2);
        (await CountAsync("openai", "ACTIVE")).Should().Be(1);
        (await CountAsync("openai", "SUPERSEDED")).Should().Be(1);
        (
            await _db.ScalarAsync<Guid>(
                "SELECT active_credential_version_id FROM business.provider_configs WHERE provider_name = 'openai'"
            )
        )
            .Should()
            .Be(second.VersionId)
            .And.NotBe(first.VersionId);
        var versions = await _service.ListVersionsAsync(openai, CancellationToken.None);
        versions
            .Select(v => (v.VersionNo, v.Status))
            .Should()
            .Equal((2, "ACTIVE"), (1, "SUPERSEDED"));
    }

    [Fact]
    public async Task ActivateRollsBackToAnEarlierVersionWithoutTouchingTheVault()
    {
        var openai = await IdAsync("openai");
        var first = await _service.ConfirmAsync(
            openai,
            Secret,
            false,
            "founder-1",
            CancellationToken.None
        );
        await _service.ConfirmAsync(
            openai,
            Secret + "-2",
            false,
            "founder-1",
            CancellationToken.None
        );
        var writes = _store.Writes.Count;

        var rolledBack = await _service.ActivateAsync(
            openai,
            first.VersionId,
            CancellationToken.None
        );

        rolledBack.Should().Be(first with { Status = "ACTIVE" });
        _store.Writes.Should().HaveCount(writes);
        (await CountAsync("openai", "ACTIVE")).Should().Be(1);
        (
            await _db.ScalarAsync<Guid>(
                "SELECT active_credential_version_id FROM business.provider_configs WHERE provider_name = 'openai'"
            )
        )
            .Should()
            .Be(first.VersionId);
        (await _service.ListAsync(CancellationToken.None))
            .Single(p => p.ProviderName == "openai")
            .Credential.ActiveVersionNo.Should()
            .Be(1);
    }

    [Fact]
    public async Task ActivateRejectsAVersionOfAnotherProvider()
    {
        var openai = await IdAsync("openai");
        var google = await IdAsync("google");
        var saved = await _service.ConfirmAsync(
            openai,
            Secret,
            false,
            "founder-1",
            CancellationToken.None
        );

        var act = async () =>
            await _service.ActivateAsync(google, saved.VersionId, CancellationToken.None);

        (await act.Should().ThrowAsync<ProviderAdminException>())
            .Which.Code.Should()
            .Be("PROVIDER_NOT_FOUND");
    }

    [Fact]
    public async Task VaultFailureRecordsNothingAndLeaksNothing()
    {
        var openai = await IdAsync("openai");
        await _service.ConfirmAsync(openai, Secret, false, "founder-1", CancellationToken.None);
        _store.Failure = new ProviderSecretStoreException("Key Vault returned HTTP 403.");

        var act = async () =>
            await _service.ConfirmAsync(
                openai,
                Secret + "-2",
                false,
                "founder-1",
                CancellationToken.None
            );

        var error = (await act.Should().ThrowAsync<ProviderAdminException>()).Which;
        error.Status.Should().Be(503);
        error.Code.Should().Be("PROVIDER_VAULT_UNAVAILABLE");
        (await _db.ScalarAsync<long>("SELECT count(*) FROM business.provider_credential_versions"))
            .Should()
            .Be(1);
        (await CountAsync("openai", "ACTIVE")).Should().Be(1);
        NothingLeaked(error);
    }

    [Fact]
    public async Task DatabaseFailureAfterTheVaultWriteLeavesThePreviousVersionActive()
    {
        var openai = await IdAsync("openai");
        var first = await _service.ConfirmAsync(
            openai,
            Secret,
            false,
            "founder-1",
            CancellationToken.None
        );
        _store.AfterWrite = () =>
            _db.ExecuteAsync(
                "ALTER TABLE business.provider_credential_versions RENAME TO provider_credential_versions_x"
            );

        var act = async () =>
            await _service.ConfirmAsync(
                openai,
                Secret + "-2",
                false,
                "founder-1",
                CancellationToken.None
            );

        var error = (await act.Should().ThrowAsync<ProviderAdminException>()).Which;
        error.Code.Should().Be("PROVIDER_PERSISTENCE_FAILED");
        await _db.ExecuteAsync(
            "ALTER TABLE business.provider_credential_versions_x RENAME TO provider_credential_versions"
        );
        (
            await _db.ScalarAsync<Guid>(
                "SELECT active_credential_version_id FROM business.provider_configs WHERE provider_name = 'openai'"
            )
        )
            .Should()
            .Be(first.VersionId);
        (await CountAsync("openai", "ACTIVE")).Should().Be(1);
        NothingLeaked(error);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("line one\nline two")]
    public async Task InvalidValuesAreRejectedBeforeAnyTestOrWrite(string? value)
    {
        var openai = await IdAsync("openai");

        var confirm = async () =>
            await _service.ConfirmAsync(openai, value, true, "founder-1", CancellationToken.None);
        var test = async () => await _service.TestAsync(openai, value, CancellationToken.None);

        (await confirm.Should().ThrowAsync<ProviderAdminException>()).Which.Status.Should().Be(400);
        (await test.Should().ThrowAsync<ProviderAdminException>()).Which.Status.Should().Be(400);
        _store.Writes.Should().BeEmpty();
        _tester.Calls.Should().Be(0);
    }

    [Fact]
    public async Task ValueLengthIsBoundedAtSixteenKibibytes()
    {
        var openai = await IdAsync("openai");

        var saved = await _service.ConfirmAsync(
            openai,
            new string('a', 16_384),
            false,
            "founder-1",
            CancellationToken.None
        );
        var tooLong = async () =>
            await _service.ConfirmAsync(
                openai,
                new string('a', 16_385),
                false,
                "founder-1",
                CancellationToken.None
            );

        saved.VersionNo.Should().Be(1);
        await tooLong.Should().ThrowAsync<ProviderAdminException>().Where(e => e.Status == 400);
    }

    [Fact]
    public async Task TestNeverWritesAndReturnsTheSanitizedResult()
    {
        _tester.Result = new(ProviderTestOutcomes.Failed, "HTTP 403", 403);
        var openai = await IdAsync("openai");

        var result = await _service.TestAsync(openai, Secret, CancellationToken.None);

        result.Should().Be(new ProviderCredentialTestResult("FAILED", "HTTP 403", 403));
        _store.Writes.Should().BeEmpty();
        (await _db.ScalarAsync<long>("SELECT count(*) FROM business.provider_credential_versions"))
            .Should()
            .Be(0);
        NothingLeaked();
    }

    [Fact]
    public async Task UnknownProviderIsNotFound()
    {
        var act = async () =>
            await _service.TestAsync(Guid.NewGuid(), Secret, CancellationToken.None);

        (await act.Should().ThrowAsync<ProviderAdminException>())
            .Which.Code.Should()
            .Be("PROVIDER_NOT_FOUND");
    }

    [Fact]
    public async Task CreateRegistersAnAgentApiProviderAndRejectsDuplicates()
    {
        var request = new CreateProviderRequest(
            "agent-x",
            "Agent X",
            "AGENT_API",
            "marketing-agent",
            "https://api.agent-x.example/v1/ping",
            "HEADER",
            "X-Agent-Key"
        );

        var created = await _service.CreateAsync(request, CancellationToken.None);
        var duplicate = async () => await _service.CreateAsync(request, CancellationToken.None);

        created
            .Should()
            .Match<ProviderSummary>(p =>
                p.ProviderName == "agent-x"
                && p.AuthMethod == "API_KEY"
                && p.HasTestEndpoint
                && p.Credential.Status == "NOT_SET"
            );
        (await duplicate.Should().ThrowAsync<ProviderAdminException>())
            .Which.Status.Should()
            .Be(409);
        (await _service.ListAsync(CancellationToken.None))
            .Should()
            .Contain(p => p.ProviderName == "agent-x");
    }

    [Theory]
    [InlineData("Bad Name", "PLATFORM_LLM", null, null, null)]
    [InlineData("x", "PLATFORM_LLM", null, null, null)]
    [InlineData("good-name", "OTHER", null, null, null)]
    [InlineData("good-name", "PLATFORM_LLM", "agent-1", null, null)]
    [InlineData("good-name", "PLATFORM_LLM", null, "http://api.example.com/ping", "BEARER")]
    [InlineData("good-name", "PLATFORM_LLM", null, "https://127.0.0.1/ping", "BEARER")]
    [InlineData(
        "good-name",
        "PLATFORM_LLM",
        null,
        "https://user:pw@api.example.com/ping",
        "BEARER"
    )]
    [InlineData("good-name", "PLATFORM_LLM", null, "https://api.example.com/ping", null)]
    [InlineData("good-name", "PLATFORM_LLM", null, "https://api.example.com/ping", "HEADER")]
    public async Task CreateRejectsInvalidRegistrations(
        string name,
        string category,
        string? agentType,
        string? url,
        string? scheme
    )
    {
        var act = async () =>
            await _service.CreateAsync(
                new CreateProviderRequest(name, "Display", category, agentType, url, scheme, null),
                CancellationToken.None
            );

        (await act.Should().ThrowAsync<ProviderAdminException>()).Which.Status.Should().Be(400);
    }

    private sealed class FakeSecretStore : IProviderSecretStore
    {
        public List<(string Name, string Value)> Writes { get; } = [];
        public Exception? Failure { get; set; }
        public Func<Task>? AfterWrite { get; set; }

        public async Task<string> SetSecretAsync(
            string secretName,
            string value,
            CancellationToken ct
        )
        {
            if (Failure is not null)
                throw Failure;
            Writes.Add((secretName, value));
            if (AfterWrite is not null)
                await AfterWrite();
            return $"ver{Writes.Count:D4}";
        }
    }

    private sealed class FakeTester : IProviderCredentialTester
    {
        public ProviderCredentialTestResult Result { get; set; } =
            new(ProviderTestOutcomes.Passed, "HTTP 200", 200);
        public int Calls { get; private set; }

        public Task<ProviderCredentialTestResult> TestAsync(
            ProviderTestTarget target,
            string value,
            CancellationToken ct
        )
        {
            Calls++;
            return Task.FromResult(Result);
        }
    }

    private sealed class CapturingLogger : ILogger<ProviderCredentialAdminService>
    {
        public List<string> Lines { get; } = [];

        public IDisposable? BeginScope<TState>(TState state)
            where TState : notnull => null;

        public bool IsEnabled(LogLevel logLevel) => true;

        public void Log<TState>(
            LogLevel logLevel,
            EventId eventId,
            TState state,
            Exception? exception,
            Func<TState, Exception?, string> formatter
        ) => Lines.Add(formatter(state, exception) + exception);
    }
}
