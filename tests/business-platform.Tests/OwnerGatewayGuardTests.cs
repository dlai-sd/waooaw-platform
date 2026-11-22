// Implements: ADR-046 sections 5.1 and 12.2 D4, D9; workload-identity-cloud-issuance-contract.md section 8
// constitutional_basis: C-023, C-059, C-063, C-083, C-084

using FluentAssertions;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public interface IGuardedOwner
{
    string Name();
    Task<int> CountAsync();
    Task RunAsync();
}

public sealed class OwnerGatewayGuardTests : IDisposable
{
    private readonly TestPki _pki = new();
    private readonly TestClock _clock;
    private readonly WorkloadIdentityClient _identity;

    public OwnerGatewayGuardTests()
    {
        _clock = new TestClock(_pki.Now);
        _identity = WorkloadIdentityClient.CreateReloadable(
            new WorkloadCredentialSettings("business-platform", TestPki.TrustDomain),
            _clock
        );
    }

    [Fact]
    public void WithoutACredentialEveryCallGoesToTheUnavailableGatewayAndTheRealOneIsUntouched()
    {
        var real = new Owner("real");
        var guarded = OwnerGatewayGuard<IGuardedOwner>.Create(
            real,
            new Owner("unavailable"),
            _identity
        );

        guarded.Name().Should().Be("unavailable");
        real.Calls.Should().Be(0);
    }

    [Fact]
    public async Task WithACredentialTheRealGatewayAnswersAndTheGuardFollowsExpiry()
    {
        Load();
        var guarded = OwnerGatewayGuard<IGuardedOwner>.Create(
            new Owner("real"),
            new Owner("unavailable"),
            _identity
        );

        guarded.Name().Should().Be("real");
        (await guarded.CountAsync()).Should().Be(7);
        _clock.Advance(TimeSpan.FromHours(25));

        guarded.Name().Should().Be("unavailable");
        (await guarded.CountAsync()).Should().Be(-1);
    }

    [Fact]
    public async Task CredentialLossDuringACallFallsBackSynchronouslyAndAsynchronously()
    {
        Load();
        var real = new Owner("real")
        {
            Failure = () => new WorkloadCredentialsUnavailableException(),
        };
        var guarded = OwnerGatewayGuard<IGuardedOwner>.Create(
            real,
            new Owner("unavailable"),
            _identity
        );

        guarded.Name().Should().Be("unavailable");
        (await guarded.CountAsync()).Should().Be(-1);
        await guarded.RunAsync();
        real.Async = true;
        (await guarded.CountAsync()).Should().Be(-1);
        await guarded.RunAsync();
    }

    [Fact]
    public async Task OtherFailuresPropagateUnchangedAndAreNotMaskedAsUnavailable()
    {
        Load();
        var real = new Owner("real") { Failure = () => new InvalidOperationException("boom") };
        var guarded = OwnerGatewayGuard<IGuardedOwner>.Create(
            real,
            new Owner("unavailable"),
            _identity
        );

        guarded
            .Invoking(value => value.Name())
            .Should()
            .Throw<InvalidOperationException>()
            .WithMessage("boom");
        real.Async = true;
        await guarded
            .Invoking(value => value.CountAsync())
            .Should()
            .ThrowAsync<InvalidOperationException>();
        await guarded
            .Invoking(value => value.RunAsync())
            .Should()
            .ThrowAsync<InvalidOperationException>();
    }

    [Fact]
    public async Task PricingGatewayWithoutACredentialReportsTheOwnerUnavailable()
    {
        var guarded = OwnerGatewayGuard<IPricingAdminGateway>.Create(
            new AuthenticatedPricingAdminGateway(_identity, new Uri("https://billing.test")),
            new UnconfiguredPricingAdminGateway(),
            _identity
        );

        await guarded
            .Invoking(value => value.SendAsync(PricingRequest(), CancellationToken.None))
            .Should()
            .ThrowAsync<PricingAdminOwnerUnavailableException>();
    }

    [Fact]
    public async Task AuthenticatedPricingGatewayMapsAMissingCredentialToTheOwnerUnavailable()
    {
        using var gateway = new AuthenticatedPricingAdminGateway(
            _identity,
            new Uri("https://billing.test")
        );

        var failure = await gateway
            .Invoking(value => value.SendAsync(PricingRequest(), CancellationToken.None))
            .Should()
            .ThrowAsync<PricingAdminOwnerUnavailableException>();

        failure.Which.InnerException.Should().BeOfType<WorkloadCredentialsUnavailableException>();
    }

    private static PricingGatewayRequest PricingRequest() =>
        new(
            "list_prices",
            "GET",
            "/internal/v1/pricing",
            "/internal/v1/pricing",
            null,
            [],
            "actor",
            "FOUNDER",
            false,
            Guid.NewGuid(),
            "pricing",
            Guid.NewGuid(),
            null
        );

    private void Load()
    {
        var issued = _pki.Create();
        _identity.Apply(issued.Bundle, issued.Trust).Outcome.Should().Be("loaded");
    }

    public void Dispose()
    {
        _identity.Dispose();
        _pki.Dispose();
    }

    private sealed class Owner(string name) : IGuardedOwner
    {
        public int Calls { get; private set; }
        public bool Async { get; set; }
        public Func<Exception>? Failure { get; set; }

        public string Name()
        {
            Calls++;
            if (Failure is not null && !Async)
                throw Failure();
            return name;
        }

        public Task<int> CountAsync()
        {
            Calls++;
            if (Failure is not null)
                return Async ? Task.FromException<int>(Failure()) : throw Failure();
            return Task.FromResult(name == "real" ? 7 : -1);
        }

        public Task RunAsync()
        {
            Calls++;
            if (Failure is not null)
                return Async ? Task.FromException(Failure()) : throw Failure();
            return Task.CompletedTask;
        }
    }
}
