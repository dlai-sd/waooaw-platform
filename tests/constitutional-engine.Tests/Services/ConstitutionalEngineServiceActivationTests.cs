using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata;
using Microsoft.Extensions.DependencyInjection;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.EmergencyStop;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Services;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Services;

public sealed class ConstitutionalEngineServiceActivationTests
{
    [Fact]
    public void GrpcActivatorSelectsRuntimeConstructor()
    {
        var services = new ServiceCollection();
        services.AddLogging();
        services.AddSingleton<EvaluatorRegistry>();
        services.AddSingleton<IClaimEvaluator, C041ToolAuthorizationEvaluator>();
        services.AddDbContextFactory<ConstitutionalDbContext>(options =>
            options.UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
        );
        services.AddDbContextFactory<EmergencyStopDbContext>(options =>
            options.UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
        );
        services.AddDbContextFactory<AuditSinkDbContext>(options =>
            options.UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
        );
        using var provider = services.BuildServiceProvider();
        var factory = ActivatorUtilities.CreateFactory(
            typeof(ConstitutionalEngineService),
            Type.EmptyTypes
        );

        var service = factory(provider, null);

        Assert.IsType<ConstitutionalEngineService>(service);
    }

    [Fact]
    public void AuditSinkModelMatchesDeployedSnakeCaseSchema()
    {
        var options = new DbContextOptionsBuilder<AuditSinkDbContext>()
            .UseNpgsql("Host=unused;Database=unused")
            .Options;
        using var db = new AuditSinkDbContext(options);
        var entity = db.Model.FindEntityType(typeof(AuditSinkEvidenceRecord))!;
        var table = StoreObjectIdentifier.Table("evidence_records", "audit_sink");

        Assert.All(
            entity.GetProperties(),
            property => Assert.Equal(ToSnakeCase(property.Name), property.GetColumnName(table))
        );
    }

    private static string ToSnakeCase(string value) =>
        string.Concat(
                value.Select(
                    (character, index) =>
                        index > 0 && char.IsUpper(character)
                            ? $"_{char.ToLowerInvariant(character)}"
                            : char.ToLowerInvariant(character).ToString()
                )
            );
}