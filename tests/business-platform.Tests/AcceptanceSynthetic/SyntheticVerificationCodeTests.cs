// Implements: work-contracts/WC-175-demo-registration-trial-hire-and-founder-defects.md WC175-R021
// Constitutional basis: C-023, C-059 (Implementation Traceability)

using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Services.AcceptanceSynthetic;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.AcceptanceSynthetic;

public sealed class SyntheticVerificationCodeTests
{
    private const string Issuer = "https://identity.invalid/realms/waooaw";

    private static SyntheticVerificationCode Service(
        FakeSyntheticAcceptanceRegistry registry,
        bool enabled = true,
        string code = AcceptanceSyntheticOptions.DefaultTestVerificationCode
    ) =>
        new(
            registry,
            Options.Create(
                new AcceptanceSyntheticOptions { Enabled = enabled, TestVerificationCode = code }
            )
        );

    [Fact]
    public async Task ASyntheticCustomerGetsTheFixedTestCode()
    {
        var registry = new FakeSyntheticAcceptanceRegistry();
        registry.Actors.Add((Issuer, "synthetic-sub"));

        Assert.Equal(
            "123456",
            await Service(registry).CodeForAsync(Issuer, "synthetic-sub", default)
        );
    }

    [Fact]
    public async Task ACustomerTheRegistryDoesNotHoldNeverGetsATestCode()
    {
        var registry = new FakeSyntheticAcceptanceRegistry();
        registry.Actors.Add((Issuer, "synthetic-sub"));

        Assert.Null(await Service(registry).CodeForAsync(Issuer, "someone-else", default));
        Assert.Null(
            await Service(registry).CodeForAsync("https://other.invalid", "synthetic-sub", default)
        );
    }

    [Fact]
    public async Task WithTheSyntheticFeatureOffNoCustomerGetsATestCodeAndTheRegistryIsNotRead()
    {
        var registry = new FakeSyntheticAcceptanceRegistry();
        registry.Actors.Add((Issuer, "synthetic-sub"));

        Assert.Null(
            await Service(registry, enabled: false).CodeForAsync(Issuer, "synthetic-sub", default)
        );
    }

    [Theory]
    [InlineData("12345")]
    [InlineData("1234567")]
    [InlineData("12a456")]
    [InlineData("")]
    public void ATestCodeThatIsNotSixDigitsIsRefusedAtStartup(string code)
    {
        var result = new AcceptanceSyntheticOptionsValidator(
            new ConfigurationBuilder().Build()
        ).Validate(null, new AcceptanceSyntheticOptions { TestVerificationCode = code });

        Assert.True(result.Failed);
    }

    [Fact]
    public void TheFeatureStillRefusesToStartInProduction()
    {
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(
                new Dictionary<string, string?> { ["IdentityEnvironment:Environment"] = "prod" }
            )
            .Build();

        Assert.True(
            new AcceptanceSyntheticOptionsValidator(configuration)
                .Validate(null, new AcceptanceSyntheticOptions { Enabled = true })
                .Failed
        );
    }
}
