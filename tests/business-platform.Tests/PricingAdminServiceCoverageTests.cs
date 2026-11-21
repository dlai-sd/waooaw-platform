// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-03
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-04
// constitutional_basis: C-023, C-059, C-063, C-088, C-089
using System.Text.Json;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class PricingAdminServiceCoverageTests
{
    private const string DraftId = "7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11";
    private const string PackageId = "0b9c1d52-3c41-4e0b-9d2c-0f6a4a5a0a11";

    private static readonly PricingAdminActor Admin = new(
        "admin-1",
        Guid.NewGuid(),
        true,
        false,
        false
    );
    private static readonly PricingAdminActor Founder = new(
        "founder-1",
        Guid.NewGuid(),
        false,
        true,
        true
    );

    private static JsonElement Json(string text) => JsonDocument.Parse(text).RootElement.Clone();

    private static PricingAdminCommand Write(
        string operation,
        string body,
        params (string Name, string Value)[] path
    ) =>
        new(
            operation,
            path.ToDictionary(pair => pair.Name, pair => pair.Value),
            [],
            Json(body),
            Guid.NewGuid(),
            Guid.NewGuid()
        );

    private static PricingAdminCommand Read(
        string operation,
        IReadOnlyList<KeyValuePair<string, string>>? query = null,
        params (string Name, string Value)[] path
    ) =>
        new(
            operation,
            path.ToDictionary(pair => pair.Name, pair => pair.Value),
            query ?? [],
            null,
            null,
            Guid.NewGuid()
        );

    private static RecordingPricingGateway Gateway(int status, string? body, string? etag = null) =>
        new()
        {
            Respond = _ => new PricingGatewayResponse(
                status,
                body is null ? null : Json(body),
                etag
            ),
        };

    private static async Task<PricingAdminProblemException> RefusedAsync(
        PricingAdminService service,
        PricingAdminActor actor,
        PricingAdminCommand command
    ) =>
        await Assert.ThrowsAsync<PricingAdminProblemException>(() =>
            service.ExecuteAsync(actor, command, CancellationToken.None)
        );

    [Fact]
    public async Task An_unknown_operation_is_a_published_not_found_problem()
    {
        var gateway = new RecordingPricingGateway();
        var service = PricingAdminFixtures.Service(gateway);

        var problem = await RefusedAsync(service, Admin, Read("exportEverything"));

        Assert.Equal((404, "PRICING_NOT_FOUND"), (problem.Status, problem.Code));
        Assert.Empty(gateway.Requests);
    }

    [Fact]
    public void The_write_window_slides_per_subject_and_frees_a_slot_after_a_minute()
    {
        var clock = new FixedClock(PricingAdminFixtures.Now);
        var limiter = new PricingAdminWriteLimiter(
            Options.Create(new PricingAdminOptions { WriteLimitPerMinute = 2 }),
            clock
        );

        Assert.True(limiter.TryAcquire("a"));
        clock.Now = clock.Now.AddSeconds(30);
        Assert.True(limiter.TryAcquire("a"));
        Assert.False(limiter.TryAcquire("a"));
        Assert.True(limiter.TryAcquire("b"));

        clock.Now = PricingAdminFixtures.Now.AddSeconds(61);
        Assert.True(limiter.TryAcquire("a"));
        Assert.False(limiter.TryAcquire("a"));

        clock.Now = PricingAdminFixtures.Now.AddSeconds(91);
        Assert.True(limiter.TryAcquire("a"));
    }

    [Theory]
    [InlineData("PRICING_FORBIDDEN", 403, "The role may not perform this pricing operation.")]
    [InlineData(
        "PRICING_STEP_UP_REQUIRED",
        403,
        "This operation needs a fresh step-up authentication."
    )]
    [InlineData(
        "PRICING_DRAFT_INVALID",
        422,
        "The draft breaks pricing rules; see the violations."
    )]
    [InlineData("PRICING_BELOW_FLOOR", 422, "The price is below the cost floor.")]
    [InlineData(
        "PRICING_NEEDS_SECOND_CONFIRMATION",
        409,
        "The change is large and needs a second confirmation."
    )]
    [InlineData(
        "PRICING_ILLEGAL_TRANSITION",
        409,
        "The version is not in a state that allows this step."
    )]
    [InlineData(
        "PRICING_CEILING_ABOVE_MAXIMUM",
        422,
        "The ceiling is above the deploy-time maximum."
    )]
    [InlineData(
        "PRICING_CEILING_BELOW_OPEN_RESERVATIONS",
        409,
        "The ceiling is below what is reserved or settled."
    )]
    [InlineData(
        "PACKAGE_COMPONENT_NOT_AVAILABLE",
        422,
        "A package component is not available for this agent."
    )]
    [InlineData(
        "RECIPE_THREAD_NOT_AUTHORIZED",
        422,
        "A recipe thread is not authorized in the catalogue."
    )]
    [InlineData("PRICING_REQUEST_INVALID", 400, "The request is not valid.")]
    [InlineData("PRICING_NOT_FOUND", 404, "The pricing version does not exist.")]
    [InlineData(
        "PRICING_VERSION_CONFLICT",
        409,
        "The version changed since it was read; reload it."
    )]
    [InlineData(
        "PRICING_IDEMPOTENCY_CONFLICT",
        409,
        "The idempotency key was used with another request."
    )]
    [InlineData("PRICING_RATE_LIMITED", 429, "Too many pricing changes; retry shortly.")]
    [InlineData("PRICING_UNAVAILABLE", 503, "The pricing owner could not complete the request.")]
    public async Task Every_published_owner_code_keeps_its_status_and_gets_its_own_detail(
        string code,
        int status,
        string detail
    )
    {
        var service = PricingAdminFixtures.Service(
            Gateway(status, $$"""{"code":"{{code}}","detail":"owner internals"}""")
        );

        var problem = await RefusedAsync(
            service,
            Admin,
            Read("getPricingDraft", path: [("draftId", DraftId)])
        );

        Assert.Equal((status, code, detail), (problem.Status, problem.Code, problem.Detail));
    }

    [Theory]
    [InlineData(409, """{"code":"NOT_A_PUBLISHED_CODE"}""")]
    [InlineData(500, """{"code":"PRICING_NOT_FOUND"}""")]
    [InlineData(302, """{"code":"PRICING_NOT_FOUND"}""")]
    [InlineData(409, """{"code":7}""")]
    [InlineData(409, """{"title":"no code"}""")]
    [InlineData(409, """["PRICING_NOT_FOUND"]""")]
    [InlineData(409, "\"PRICING_NOT_FOUND\"")]
    [InlineData(409, null)]
    public async Task A_failure_the_owner_did_not_publish_is_reported_as_unavailable(
        int status,
        string? body
    )
    {
        var service = PricingAdminFixtures.Service(Gateway(status, body));

        var problem = await RefusedAsync(
            service,
            Admin,
            Read("getPricingDraft", path: [("draftId", DraftId)])
        );

        Assert.Equal((503, "PRICING_UNAVAILABLE"), (problem.Status, problem.Code));
        Assert.Empty(problem.Extras);
    }

    [Fact]
    public async Task Only_the_published_problem_members_are_carried_over()
    {
        var service = PricingAdminFixtures.Service(
            Gateway(
                422,
                """
                {"code":"PRICING_DRAFT_INVALID","violations":[{"rule":"FLOOR"}],
                 "minimumCompliantPricePaise":900,"componentId":"lead_batch",
                 "stack":"secret internals"}
                """
            )
        );

        var problem = await RefusedAsync(
            service,
            Admin,
            Write("createPricingDraft", """{"schemaVersion":"1.0","kind":"RATE"}""")
        );

        Assert.Equal(
            ["componentId", "minimumCompliantPricePaise", "violations"],
            problem.Extras.Keys.Order().ToArray()
        );
        Assert.Equal(900, problem.Extras["minimumCompliantPricePaise"].GetInt64());
    }

    [Theory]
    [InlineData(
        "createPricingDraft",
        """{"schemaVersion":"1.0","subjectKey":"agent-9"}""",
        "agent-9"
    )]
    [InlineData("createPricingDraft", """{"schemaVersion":"1.0","packageId":"pkg-4"}""", "pkg-4")]
    [InlineData(
        "createPricingDraft",
        """{"schemaVersion":"1.0","subjectKey":"agent-9","packageId":"pkg-4"}""",
        "agent-9"
    )]
    [InlineData("createPricingDraft", """{"schemaVersion":"1.0","subjectKey":5}""", "pricing")]
    [InlineData(
        "lowerPricingCeiling",
        """{"schemaVersion":"1.0","scope":"CUSTOMER","ref":"acct-1","newMaximumPaise":5}""",
        "budget:CUSTOMER|acct-1"
    )]
    [InlineData(
        "lowerPricingCeiling",
        """{"schemaVersion":"1.0","scope":"CUSTOMER","newMaximumPaise":5}""",
        "pricing"
    )]
    [InlineData(
        "closePackageToNewCustomers",
        """{"schemaVersion":"1.0","scope":"CUSTOMER","ref":"acct-1"}""",
        "pricing"
    )]
    public async Task The_signed_subject_reference_names_what_the_call_is_about(
        string operation,
        string body,
        string expected
    )
    {
        var gateway = new RecordingPricingGateway();
        var service = PricingAdminFixtures.Service(gateway);

        await service.ExecuteAsync(Admin, Write(operation, body), CancellationToken.None);

        Assert.Equal(expected, Assert.Single(gateway.Requests).SubjectReference);
    }

    [Fact]
    public async Task The_subject_reference_of_a_path_call_is_its_resource_id_and_a_list_has_none()
    {
        var gateway = new RecordingPricingGateway();
        var service = PricingAdminFixtures.Service(gateway);

        await service.ExecuteAsync(
            Admin,
            Read("getPricingDraft", path: [("draftId", DraftId)]),
            CancellationToken.None
        );
        await service.ExecuteAsync(
            Founder,
            Write(
                "activatePackageForSale",
                """{"schemaVersion":"1.0"}""",
                ("packageId", PackageId)
            ),
            CancellationToken.None
        );
        await service.ExecuteAsync(Admin, Read("listPricingDrafts"), CancellationToken.None);

        Assert.Equal(
            [DraftId, PackageId, "pricing"],
            gateway.Requests.Select(request => request.SubjectReference)
        );
    }

    [Fact]
    public async Task Query_parameters_are_escaped_repeated_and_bounded()
    {
        var gateway = new RecordingPricingGateway();
        var service = PricingAdminFixtures.Service(gateway);

        await service.ExecuteAsync(
            Admin,
            Read(
                "listPricingDrafts",
                [new("kind", "RATE card"), new("state", "A&B"), new("kind", "BUDGET")]
            ),
            CancellationToken.None
        );

        Assert.Equal(
            "kind=RATE%20card&state=A%26B&kind=BUDGET",
            Assert.Single(gateway.Requests).Query
        );
        foreach (
            var invalid in new KeyValuePair<string, string>[]
            {
                new("unknown", "x"),
                new("kind", ""),
                new("kind", new string('x', 301)),
            }
        )
        {
            var problem = await RefusedAsync(service, Admin, Read("listPricingDrafts", [invalid]));
            Assert.Equal("PRICING_REQUEST_INVALID", problem.Code);
        }
        Assert.Single(gateway.Requests);
    }

    [Theory]
    [InlineData("""{"kind":"RATE"}""")]
    [InlineData("""{"schemaVersion":1.0,"kind":"RATE"}""")]
    [InlineData("""{"schemaVersion":"2.0","kind":"RATE"}""")]
    [InlineData("""[1]""")]
    [InlineData("""null""")]
    public async Task A_write_needs_an_object_body_on_schema_version_1_0(string body)
    {
        var gateway = new RecordingPricingGateway();
        var service = PricingAdminFixtures.Service(gateway);

        var problem = await RefusedAsync(service, Admin, Write("createPricingDraft", body));

        Assert.Equal((400, "PRICING_REQUEST_INVALID"), (problem.Status, problem.Code));
        Assert.Empty(gateway.Requests);
    }

    [Fact]
    public async Task A_write_without_a_body_at_all_is_refused()
    {
        var service = PricingAdminFixtures.Service(new RecordingPricingGateway());

        var problem = await RefusedAsync(
            service,
            Admin,
            Write("createPricingDraft", "{}") with
            {
                Body = null,
            }
        );

        Assert.Equal("PRICING_REQUEST_INVALID", problem.Code);
    }

    [Fact]
    public async Task A_package_activation_needs_a_uuid_package_id()
    {
        var service = PricingAdminFixtures.Service(new RecordingPricingGateway());

        var missing = await RefusedAsync(
            service,
            Founder,
            Write("activatePackageForSale", """{"schemaVersion":"1.0"}""")
        );
        var malformed = await RefusedAsync(
            service,
            Founder,
            Write("activatePackageForSale", """{"schemaVersion":"1.0"}""", ("packageId", "p1"))
        );

        Assert.Equal("PRICING_REQUEST_INVALID", missing.Code);
        Assert.Equal("PRICING_REQUEST_INVALID", malformed.Code);
    }
}

public sealed class PricingAdminCeilingCoverageTests
{
    private const string DraftId = "7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11";
    private static readonly Guid VersionId = Guid.Parse(DraftId);
    private static readonly Guid Evidence = Guid.NewGuid();

    private static readonly PricingAdminActor Founder = new(
        "founder-1",
        Guid.NewGuid(),
        false,
        true,
        true
    );
    private static readonly PricingAdminActor Admin = new(
        "admin-1",
        Guid.NewGuid(),
        true,
        false,
        false
    );

    private static string Ceiling(
        string state,
        string evidence = "",
        string scope = "ENVIRONMENT_CEILING",
        string reference = "demo"
    ) =>
        $$$"""
            {"versionId":"{{{DraftId}}}","kind":"BUDGET","state":"{{{state}}}"{{{evidence}}},
             "body":{"scope":"{{{scope}}}","ref":"{{{reference}}}","maximumPaise":30000}}
            """;

    private static string EvidenceMember(Guid id) => $$$""","evidenceId":"{{{id}}}" """;

    private static RecordingPricingGateway Owner(string draft, string? authorized = null) =>
        new()
        {
            Respond = request => new PricingGatewayResponse(
                200,
                JsonDocument
                    .Parse(
                        request.WbeOperation == "wbeGetPricingDraft" ? draft : authorized ?? draft
                    )
                    .RootElement.Clone(),
                null
            ),
        };

    private static PricingAdminCommand Authorize(string extra = "") =>
        new(
            "authorizePricingDraft",
            new Dictionary<string, string> { ["draftId"] = DraftId },
            [],
            JsonDocument
                .Parse($$"""{"schemaVersion":"1.0","expectedVersion":"v"{{extra}}}""")
                .RootElement.Clone(),
            Guid.NewGuid(),
            Guid.NewGuid()
        );

    private static PricingAdminCommand Lower(string body) =>
        new(
            "lowerPricingCeiling",
            new Dictionary<string, string>(),
            [],
            JsonDocument.Parse(body).RootElement.Clone(),
            Guid.NewGuid(),
            Guid.NewGuid()
        );

    private static EnvironmentCeilingOutcome Outcome(
        string outcome,
        long? previous = 50_000,
        long? applied = 30_000,
        long? blocking = null
    ) => new(outcome, previous, applied, blocking);

    public static TheoryData<string> DraftsThatAreNotEnvironmentCeilings =>
        new()
        {
            """{"versionId":"7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11","kind":"RATE","state":"SUBMITTED","body":{"scope":"ENVIRONMENT_CEILING","ref":"demo","maximumPaise":1}}""",
            """{"versionId":"7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11","state":"SUBMITTED"}""",
            """{"versionId":"7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11","kind":"BUDGET","state":"SUBMITTED"}""",
            """{"versionId":"7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11","kind":"BUDGET","state":"SUBMITTED","body":[]}""",
            """{"versionId":"7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11","kind":"BUDGET","state":"SUBMITTED","body":{"ref":"demo","maximumPaise":1}}""",
            """{"versionId":"7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11","kind":"BUDGET","state":"SUBMITTED","body":{"scope":"CUSTOMER","ref":"demo","maximumPaise":1}}""",
            """{"versionId":"7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11","kind":"BUDGET","state":"SUBMITTED","body":{"scope":"ENVIRONMENT_CEILING","maximumPaise":1}}""",
            """{"versionId":"7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11","kind":"BUDGET","state":"SUBMITTED","body":{"scope":"ENVIRONMENT_CEILING","ref":"","maximumPaise":1}}""",
            """{"versionId":"7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11","kind":"BUDGET","state":"SUBMITTED","body":{"scope":"ENVIRONMENT_CEILING","ref":"demo"}}""",
            """{"versionId":"7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11","kind":"BUDGET","state":"SUBMITTED","body":{"scope":"ENVIRONMENT_CEILING","ref":"demo","maximumPaise":1.5}}""",
            """{"kind":"BUDGET","state":"SUBMITTED","body":{"scope":"ENVIRONMENT_CEILING","ref":"demo","maximumPaise":1}}""",
            """{"versionId":"not-a-guid","kind":"BUDGET","state":"SUBMITTED","body":{"scope":"ENVIRONMENT_CEILING","ref":"demo","maximumPaise":1}}""",
            """[]""",
        };

    [Theory]
    [MemberData(nameof(DraftsThatAreNotEnvironmentCeilings))]
    public async Task A_draft_that_is_not_an_environment_ceiling_is_authorized_without_touching_the_authority(
        string draft
    )
    {
        var ceilings = new FakeCeilingStore();
        var gateway = Owner(draft, """{"state":"EFFECTIVE"}""");
        var service = PricingAdminFixtures.Service(gateway, ceilings);

        var result = await service.ExecuteAsync(Founder, Authorize(), CancellationToken.None);

        Assert.Equal(200, result.Status);
        Assert.Equal(
            ["wbeGetPricingDraft", "wbeAuthorizePricingDraft"],
            gateway.Requests.Select(request => request.WbeOperation)
        );
        Assert.Empty(ceilings.Calls);
    }

    [Fact]
    public async Task An_authorization_without_a_readable_draft_body_is_forwarded()
    {
        var ceilings = new FakeCeilingStore();
        var gateway = new RecordingPricingGateway
        {
            Respond = _ => new PricingGatewayResponse(200, null, null),
        };
        var service = PricingAdminFixtures.Service(gateway, ceilings);

        await service.ExecuteAsync(Founder, Authorize(), CancellationToken.None);

        Assert.Equal(2, gateway.Requests.Count);
        Assert.Empty(ceilings.Calls);
    }

    [Theory]
    [InlineData(",\"effectiveFrom\":\"not a date\"")]
    [InlineData(",\"effectiveFrom\":\"2020-01-01T00:00:00Z\"")]
    [InlineData(",\"effectiveFrom\":20300101")]
    [InlineData(",\"effectiveFrom\":null")]
    public async Task An_effective_from_that_is_not_in_the_future_does_not_block_the_authorization(
        string effectiveFrom
    )
    {
        var ceilings = new FakeCeilingStore();
        var gateway = Owner(Ceiling("SUBMITTED"), Ceiling("DRAFT"));
        var service = PricingAdminFixtures.Service(gateway, ceilings);

        await service.ExecuteAsync(Founder, Authorize(effectiveFrom), CancellationToken.None);

        Assert.Equal(2, gateway.Requests.Count);
        Assert.Equal([true], ceilings.Calls.Select(call => call.DryRun));
    }

    [Fact]
    public async Task A_future_effective_from_is_refused_before_anything_is_applied()
    {
        var ceilings = new FakeCeilingStore();
        var gateway = Owner(Ceiling("SUBMITTED"));
        var service = PricingAdminFixtures.Service(gateway, ceilings);

        var problem = await Assert.ThrowsAsync<PricingAdminProblemException>(() =>
            service.ExecuteAsync(
                Founder,
                Authorize(",\"effectiveFrom\":\"2030-01-01T00:00:00Z\""),
                CancellationToken.None
            )
        );

        Assert.Equal((400, "PRICING_REQUEST_INVALID"), (problem.Status, problem.Code));
        Assert.Empty(ceilings.Calls);
        Assert.Single(gateway.Requests);
    }

    [Theory]
    [InlineData("")]
    [InlineData(",\"evidenceId\":\"00000000-0000-0000-0000-000000000000\"")]
    [InlineData(",\"evidenceId\":\"not-a-guid\"")]
    [InlineData(",\"evidenceId\":12")]
    public async Task An_effective_ceiling_without_usable_evidence_falls_back_to_its_version_id(
        string evidence
    )
    {
        var ceilings = new FakeCeilingStore();
        var gateway = Owner(Ceiling("EFFECTIVE", evidence));
        var service = PricingAdminFixtures.Service(gateway, ceilings);

        var result = await service.ExecuteAsync(Founder, Authorize(), CancellationToken.None);

        var call = Assert.Single(ceilings.Calls);
        Assert.Equal(
            ("demo", 30_000L, VersionId, false),
            (call.Environment, call.Maximum, call.Evidence, call.DryRun)
        );
        Assert.Equal("EFFECTIVE", result.Body!.Value.GetProperty("state").GetString());
        Assert.Single(gateway.Requests);
    }

    [Fact]
    public async Task A_submitted_ceiling_is_checked_then_authorized_then_applied_with_the_owner_evidence()
    {
        var ceilings = new FakeCeilingStore();
        var gateway = Owner(Ceiling("SUBMITTED"), Ceiling("EFFECTIVE", EvidenceMember(Evidence)));
        var service = PricingAdminFixtures.Service(gateway, ceilings);

        await service.ExecuteAsync(Founder, Authorize(), CancellationToken.None);

        Assert.Equal([true, false], ceilings.Calls.Select(call => call.DryRun));
        Assert.Equal(Evidence, ceilings.Calls[1].Evidence);
        Assert.Equal(
            PricingAdminFixtures.Service(gateway).HardMaximumPaise,
            ceilings.Calls[0].Hard
        );
    }

    [Theory]
    [InlineData("AUTHORIZED")]
    [InlineData("DRAFT")]
    public async Task A_submitted_ceiling_the_owner_does_not_make_effective_is_not_applied(
        string ownerState
    )
    {
        var ceilings = new FakeCeilingStore();
        var gateway = Owner(Ceiling("SUBMITTED"), Ceiling(ownerState));
        var service = PricingAdminFixtures.Service(gateway, ceilings);

        await service.ExecuteAsync(Founder, Authorize(), CancellationToken.None);

        Assert.Equal([true], ceilings.Calls.Select(call => call.DryRun));
    }

    [Fact]
    public async Task A_ceiling_in_any_other_state_is_forwarded_untouched()
    {
        var ceilings = new FakeCeilingStore();
        var gateway = Owner(Ceiling("DRAFT"));
        var service = PricingAdminFixtures.Service(gateway, ceilings);

        await service.ExecuteAsync(Founder, Authorize(), CancellationToken.None);

        Assert.Empty(ceilings.Calls);
        Assert.Equal(2, gateway.Requests.Count);
    }

    [Fact]
    public async Task A_missing_authority_is_tolerated_and_the_authorization_still_completes()
    {
        var ceilings = new FakeCeilingStore
        {
            Respond = _ => Outcome(EnvironmentCeilingOutcomes.AuthorityAbsent, null, null),
        };
        var gateway = Owner(Ceiling("SUBMITTED"), Ceiling("EFFECTIVE"));
        var service = PricingAdminFixtures.Service(gateway, ceilings);

        var result = await service.ExecuteAsync(Founder, Authorize(), CancellationToken.None);

        Assert.Equal(200, result.Status);
        Assert.Equal(2, ceilings.Calls.Count);
        Assert.Equal(2, gateway.Requests.Count);
    }

    [Fact]
    public async Task A_below_exposure_refusal_without_an_amount_reports_zero_blocking()
    {
        var ceilings = new FakeCeilingStore
        {
            Respond = _ => Outcome(EnvironmentCeilingOutcomes.BelowExposure, 50_000, null, null),
        };
        var service = PricingAdminFixtures.Service(Owner(Ceiling("SUBMITTED")), ceilings);

        var problem = await Assert.ThrowsAsync<PricingAdminProblemException>(() =>
            service.ExecuteAsync(Founder, Authorize(), CancellationToken.None)
        );

        Assert.Equal(
            (409, "PRICING_CEILING_BELOW_OPEN_RESERVATIONS"),
            (problem.Status, problem.Code)
        );
        Assert.Equal(0, problem.Extras["blockingPaise"].GetInt64());
    }

    [Fact]
    public async Task A_cancelled_authority_update_is_not_reported_as_unavailable()
    {
        var ceilings = new FakeCeilingStore
        {
            Respond = _ => throw new OperationCanceledException(),
        };
        var service = PricingAdminFixtures.Service(Owner(Ceiling("SUBMITTED")), ceilings);

        await Assert.ThrowsAsync<OperationCanceledException>(() =>
            service.ExecuteAsync(Founder, Authorize(), CancellationToken.None)
        );
    }

    [Fact]
    public async Task Lowering_that_the_dry_run_shows_as_a_raise_is_refused_and_nothing_is_forwarded()
    {
        var ceilings = new FakeCeilingStore
        {
            Respond = _ => Outcome(EnvironmentCeilingOutcomes.DryRunOk, 20_000, 30_000),
        };
        var gateway = new RecordingPricingGateway();
        var service = PricingAdminFixtures.Service(gateway, ceilings);

        var problem = await Assert.ThrowsAsync<PricingAdminProblemException>(() =>
            service.ExecuteAsync(
                Admin,
                Lower(
                    """{"schemaVersion":"1.0","scope":"ENVIRONMENT_CEILING","ref":"demo","newMaximumPaise":30000}"""
                ),
                CancellationToken.None
            )
        );

        Assert.Equal((422, "PRICING_CEILING_ABOVE_MAXIMUM"), (problem.Status, problem.Code));
        Assert.Equal([true], ceilings.Calls.Select(call => call.DryRun));
        Assert.Empty(gateway.Requests);
    }

    [Fact]
    public async Task A_real_lowering_is_dry_run_then_applied_with_the_correlation_as_evidence_then_forwarded()
    {
        var ceilings = new FakeCeilingStore
        {
            Respond = _ => Outcome(EnvironmentCeilingOutcomes.DryRunOk, 50_000, 30_000),
        };
        var gateway = new RecordingPricingGateway();
        var service = PricingAdminFixtures.Service(gateway, ceilings);
        var command = Lower(
            """{"schemaVersion":"1.0","scope":"ENVIRONMENT_CEILING","ref":"demo","newMaximumPaise":30000}"""
        );

        await service.ExecuteAsync(Admin, command, CancellationToken.None);

        Assert.Equal([true, false], ceilings.Calls.Select(call => call.DryRun));
        Assert.All(
            ceilings.Calls,
            call => Assert.Equal(command.CorrelationId!.Value, call.Evidence)
        );
        Assert.Equal(
            "budget:ENVIRONMENT_CEILING|demo",
            Assert.Single(gateway.Requests).SubjectReference
        );
    }

    [Fact]
    public async Task A_lowering_whose_dry_run_is_not_ok_is_only_forwarded()
    {
        var ceilings = new FakeCeilingStore
        {
            Respond = _ => Outcome(EnvironmentCeilingOutcomes.AuthorityAbsent, null, null),
        };
        var gateway = new RecordingPricingGateway();
        var service = PricingAdminFixtures.Service(gateway, ceilings);

        await service.ExecuteAsync(
            Admin,
            Lower(
                """{"schemaVersion":"1.0","scope":"ENVIRONMENT_CEILING","ref":"demo","newMaximumPaise":30000}"""
            ),
            CancellationToken.None
        );

        Assert.Single(ceilings.Calls);
        Assert.Single(gateway.Requests);
    }

    [Theory]
    [InlineData("""{"schemaVersion":"1.0","scope":"CUSTOMER","ref":"demo","newMaximumPaise":1}""")]
    [InlineData("""{"schemaVersion":"1.0","scope":"ENVIRONMENT_CEILING","newMaximumPaise":1}""")]
    [InlineData("""{"schemaVersion":"1.0","scope":"ENVIRONMENT_CEILING","ref":"demo"}""")]
    [InlineData(
        """{"schemaVersion":"1.0","scope":"ENVIRONMENT_CEILING","ref":"demo","newMaximumPaise":"1"}"""
    )]
    [InlineData(
        """{"schemaVersion":"1.0","scope":"ENVIRONMENT_CEILING","ref":"demo","newMaximumPaise":1.5}"""
    )]
    public async Task A_lowering_that_does_not_name_an_environment_ceiling_never_touches_the_authority(
        string body
    )
    {
        var ceilings = new FakeCeilingStore();
        var gateway = new RecordingPricingGateway();
        var service = PricingAdminFixtures.Service(gateway, ceilings);

        await service.ExecuteAsync(Admin, Lower(body), CancellationToken.None);

        Assert.Empty(ceilings.Calls);
        Assert.Single(gateway.Requests);
    }
}
