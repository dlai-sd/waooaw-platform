// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-01
// Constitutional basis: C-023, C-059, C-063
using System.Text.RegularExpressions;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class EnvironmentSpendOptionsTests
{
    private static readonly EnvironmentSpendOptionsValidator Validator = new();

    [Fact]
    public void Default_ceiling_is_five_hundred_rupees_and_binds_from_configuration()
    {
        var options = new EnvironmentSpendOptions();
        Assert.Equal(500m, options.HardMaximumInr);
        Assert.Equal(50_000, options.EffectiveMaximumPaise(2_000m));

        var configured = new ConfigurationBuilder()
            .AddInMemoryCollection(
                new Dictionary<string, string?>
                {
                    ["EnvironmentSpend:HardMaximumInr"] = "2000",
                    ["EnvironmentSpend:Mode"] = "LEASES",
                }
            )
            .Build()
            .GetSection(EnvironmentSpendOptions.SectionName)
            .Get<EnvironmentSpendOptions>()!;
        Assert.Equal(2000m, configured.HardMaximumInr);
        Assert.True(configured.UsesLeases);
        Assert.Equal(200_000, configured.EffectiveMaximumPaise(5_000m));
        Assert.True(Validator.Validate(null, configured).Succeeded);
    }

    [Theory]
    [InlineData(500, 500, 500)]
    [InlineData(500, 120, 120)]
    [InlineData(2000, 1500, 1500)]
    [InlineData(2000, 5000, 2000)]
    public void Effective_maximum_is_the_lower_of_the_ceiling_and_the_authority(
        decimal ceiling,
        decimal authority,
        decimal expected
    )
    {
        var options = new EnvironmentSpendOptions { HardMaximumInr = ceiling };
        Assert.Equal(expected, options.EffectiveMaximumInr(authority));
        Assert.Equal((long)(expected * 100m), options.EffectiveMaximumPaise(authority));
    }

    [Theory]
    [InlineData("HardMaximumInr", "0")]
    [InlineData("HardMaximumInr", "-1")]
    [InlineData("HardMaximumInr", "100.001")]
    [InlineData("HardMaximumInr", "1000000000000")]
    [InlineData("LeaseSizeInr", "0")]
    [InlineData("LeaseSizeInr", "501")]
    [InlineData("LeaseSizeInr", "1.234")]
    [InlineData("LeaseSeconds", "4")]
    [InlineData("LeaseSeconds", "3601")]
    [InlineData("Mode", "lease")]
    public void Invalid_configuration_fails_validation(string property, string value)
    {
        var options = new ConfigurationBuilder()
            .AddInMemoryCollection(
                new Dictionary<string, string?>
                {
                    [$"{EnvironmentSpendOptions.SectionName}:{property}"] = value,
                }
            )
            .Build()
            .GetSection(EnvironmentSpendOptions.SectionName)
            .Get<EnvironmentSpendOptions>()!;
        var result = Validator.Validate(null, options);
        Assert.True(result.Failed);
        Assert.All(
            result.Failures!,
            failure => Assert.StartsWith("EnvironmentSpend:", failure, StringComparison.Ordinal)
        );
    }

    [Fact]
    public void Lease_size_above_the_ceiling_is_refused()
    {
        var options = new EnvironmentSpendOptions { HardMaximumInr = 20m, LeaseSizeInr = 25m };
        Assert.True(Validator.Validate(null, options).Failed);
    }

    [Fact]
    public void No_hardcoded_five_hundred_rupee_literal_remains_in_business_platform_source()
    {
        var source = Path.Combine(RepositoryPaths.Root(), "src", "business-platform");
        var literal = new Regex(@"\b500m\b", RegexOptions.CultureInvariant);
        var offenders = Directory
            .EnumerateFiles(source, "*.cs", SearchOption.AllDirectories)
            .Where(path =>
                !path.Contains($"{Path.DirectorySeparatorChar}bin{Path.DirectorySeparatorChar}")
                && !path.Contains($"{Path.DirectorySeparatorChar}obj{Path.DirectorySeparatorChar}")
                && !path.Contains(
                    $"{Path.DirectorySeparatorChar}Generated{Path.DirectorySeparatorChar}"
                )
            )
            .Where(path => literal.IsMatch(File.ReadAllText(path)))
            .Select(path => Path.GetRelativePath(source, path))
            .ToArray();
        Assert.Empty(offenders);
    }
}
