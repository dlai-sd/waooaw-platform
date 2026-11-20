// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-04
// Constitutional basis: C-023, C-059, C-063
using Waooaw.BusinessPlatform.Services.Spend;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Spend;

public sealed class SpendAccountResolverTests
{
    private static readonly SpendPurposeMap Purposes = SpendPurposeMap.Parse(
        File.ReadAllText(
            RepositoryPaths.Resolve("src/business-platform/Catalog/Spend/purpose-map.v1.json")
        )
    );
    private static readonly SpendAccountResolver Resolver = new(Purposes);

    private static RelationshipSpendInput Input(
        SpendPurpose purpose,
        string authority = SpendAuthorityKinds.None,
        Guid? relationship = null,
        bool simulation = false
    ) => new(relationship ?? Guid.NewGuid(), authority, purpose, "WEB", simulation);

    [Theory]
    [InlineData(
        SpendPurpose.SafetyFloor,
        SpendAuthorityKinds.None,
        SpendAccountClass.PlatformFloor
    )]
    [InlineData(
        SpendPurpose.SafetyFloor,
        SpendAuthorityKinds.Trial,
        SpendAccountClass.PlatformFloor
    )]
    [InlineData(SpendPurpose.Simulation, SpendAuthorityKinds.Trial, SpendAccountClass.Simulation)]
    [InlineData(
        SpendPurpose.PresalesOrMarketplace,
        SpendAuthorityKinds.AcceptedOffering,
        SpendAccountClass.Acquisition
    )]
    [InlineData(
        SpendPurpose.PlatformSupport,
        SpendAuthorityKinds.Trial,
        SpendAccountClass.Acquisition
    )]
    [InlineData(SpendPurpose.Onboarding, SpendAuthorityKinds.Trial, SpendAccountClass.SetupGrant)]
    [InlineData(SpendPurpose.Onboarding, SpendAuthorityKinds.None, SpendAccountClass.SetupGrant)]
    [InlineData(SpendPurpose.AgentWork, SpendAuthorityKinds.Trial, SpendAccountClass.Trial)]
    [InlineData(
        SpendPurpose.AgentWork,
        SpendAuthorityKinds.AcceptedOffering,
        SpendAccountClass.Subscription
    )]
    public void Resolution_follows_the_account_class_table(
        SpendPurpose purpose,
        string authority,
        SpendAccountClass expected
    ) => Assert.Equal(expected, Resolver.Resolve(Input(purpose, authority)).AccountClass);

    [Fact]
    public void Agent_work_without_a_known_authority_is_refused()
    {
        var refusal = Assert.Throws<SpendRefusedException>(() =>
            Resolver.Resolve(Input(SpendPurpose.AgentWork, SpendAuthorityKinds.None))
        );
        Assert.Equal(SpendRefusalCodes.AuthorityUnavailable, refusal.Code);
        Assert.Equal(403, refusal.StatusCode);
    }

    [Fact]
    public void Pre_relationship_traffic_resolves_to_acquisition_without_a_relationship()
    {
        var decision = Resolver.Resolve(
            new RelationshipSpendInput(
                null,
                SpendAuthorityKinds.None,
                SpendPurpose.AgentWork,
                "WEB",
                false
            )
        );
        Assert.Equal(SpendAccountClass.Acquisition, decision.AccountClass);
        Assert.Null(decision.RelationshipId);

        var marketplace = Resolver.Resolve(Input(SpendPurpose.PresalesOrMarketplace));
        Assert.Null(marketplace.RelationshipId);
    }

    [Theory]
    [InlineData("INDUCTION", "INDUCTION", SpendPurpose.Onboarding)]
    [InlineData("PLANNING", "PLANNING", SpendPurpose.AgentWork)]
    [InlineData("OPERATIONS", "OPERATIONS", SpendPurpose.AgentWork)]
    [InlineData("MARKETPLACE", "BROWSE", SpendPurpose.PresalesOrMarketplace)]
    [InlineData("BILLING", "ANY", SpendPurpose.PlatformSupport)]
    [InlineData("STOP", "ANY", SpendPurpose.SafetyFloor)]
    public void Registered_contexts_map_to_their_purpose(
        string contextKey,
        string phase,
        SpendPurpose expected
    ) => Assert.Equal(expected, Resolver.ResolvePurpose(contextKey, phase));

    [Theory]
    [InlineData(null, "OPERATIONS")]
    [InlineData("", "OPERATIONS")]
    [InlineData("UNREGISTERED", "OPERATIONS")]
    [InlineData("OPERATIONS", "UNKNOWN_PHASE")]
    [InlineData("OPERATIONS", null)]
    public void Unmapped_context_is_refused_before_any_spend(string? contextKey, string? phase)
    {
        var refusal = Assert.Throws<SpendRefusedException>(() =>
            Resolver.ResolvePurpose(contextKey, phase)
        );
        Assert.Equal(SpendRefusalCodes.PurposeUnmapped, refusal.Code);
        Assert.Equal(403, refusal.StatusCode);
    }

    [Fact]
    public void Commercial_unavailability_is_a_service_unavailable_refusal()
    {
        Assert.Equal(
            503,
            new SpendRefusedException(SpendRefusalCodes.CommercialUnavailable).StatusCode
        );
    }

    [Fact]
    public void Account_follows_the_relationship_not_the_client_supplied_scope()
    {
        var first = Guid.NewGuid();
        var second = Guid.NewGuid();
        var one = Resolver.Resolve(Input(SpendPurpose.AgentWork, SpendAuthorityKinds.Trial, first));
        var two = Resolver.Resolve(
            Input(SpendPurpose.AgentWork, SpendAuthorityKinds.Trial, second)
        );
        Assert.Equal(first, one.RelationshipId);
        Assert.Equal(second, two.RelationshipId);
        Assert.NotEqual(one.RelationshipId, two.RelationshipId);
        Assert.Equal(SpendAccountClass.Trial, one.AccountClass);
        Assert.Equal(SpendAccountClass.Trial, two.AccountClass);
    }

    [Fact]
    public void Trial_to_subscription_conversion_does_not_change_the_pinned_account()
    {
        var relationship = Guid.NewGuid();
        var pinned = new SpendAccountPin(
            Resolver
                .Resolve(Input(SpendPurpose.AgentWork, SpendAuthorityKinds.Trial, relationship))
                .AccountClass
        );
        var afterConversion = Resolver
            .Resolve(
                Input(SpendPurpose.AgentWork, SpendAuthorityKinds.AcceptedOffering, relationship)
            )
            .AccountClass;
        Assert.Equal(SpendAccountClass.Trial, pinned.AccountClass);
        Assert.Equal(SpendAccountClass.Subscription, afterConversion);
        Assert.Equal(
            SpendAccountClass.Trial,
            SpendAccountClasses.Parse(pinned.AccountClass.ToStorage())
        );
    }

    [Fact]
    public void Account_class_storage_names_round_trip_and_unknown_names_are_rejected()
    {
        foreach (var value in Enum.GetValues<SpendAccountClass>())
            Assert.Equal(value, SpendAccountClasses.Parse(value.ToStorage()));
        Assert.Null(SpendAccountClasses.ParseOrNull(null));
        Assert.Throws<ArgumentOutOfRangeException>(() => SpendAccountClasses.Parse("WALLET"));
    }

    [Theory]
    [InlineData("TRIAL", SpendAuthorityKinds.Trial)]
    [InlineData("LIVE", SpendAuthorityKinds.AcceptedOffering)]
    [InlineData("OTHER", SpendAuthorityKinds.None)]
    [InlineData(null, SpendAuthorityKinds.None)]
    public void Engagement_mode_maps_to_the_authority_kind(string? mode, string expected) =>
        Assert.Equal(expected, SpendAuthorityKinds.FromEngagementMode(mode));

    [Fact]
    public void Purpose_map_rejects_duplicates_unknown_purposes_and_wrong_versions()
    {
        const string duplicate =
            """{"schemaVersion":"1.0","entries":[{"contextKey":"A","phase":"*","purpose":"AgentWork"},{"contextKey":"A","phase":"*","purpose":"Onboarding"}]}""";
        const string unknown =
            """{"schemaVersion":"1.0","entries":[{"contextKey":"A","phase":"*","purpose":"Free"}]}""";
        const string numeric =
            """{"schemaVersion":"1.0","entries":[{"contextKey":"A","phase":"*","purpose":"99"}]}""";
        const string version =
            """{"schemaVersion":"2.0","entries":[{"contextKey":"A","phase":"*","purpose":"AgentWork"}]}""";
        foreach (var json in new[] { duplicate, unknown, numeric, version, "{}" })
            Assert.Throws<InvalidOperationException>(() => SpendPurposeMap.Parse(json));
    }

    [Fact]
    public void Purpose_map_prefers_the_exact_phase_over_the_wildcard()
    {
        var map = SpendPurposeMap.Parse(
            """{"schemaVersion":"1.0","entries":[{"contextKey":"A","phase":"*","purpose":"AgentWork"},{"contextKey":"A","phase":"X","purpose":"Onboarding"}]}"""
        );
        Assert.Equal(SpendPurpose.Onboarding, map.Find("A", "X"));
        Assert.Equal(SpendPurpose.AgentWork, map.Find("A", "Y"));
        Assert.Null(map.Find("B", "X"));
    }
}
