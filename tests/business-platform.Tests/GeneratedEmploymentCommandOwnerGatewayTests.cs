// Implements: WC-115 R008-R011, R017-R018, R029-R038
// Constitutional basis: C-001, C-023, C-026, C-059, C-063, C-079, ADR-051
// IB: N/A - Founder-assigned WC-115

using System.Diagnostics;
using System.Net;
using System.Text;
using System.Text.Json;
using Waooaw.BusinessPlatform.Services;
using Waooaw.Generated.DomainEmployment.Api;
using Waooaw.Generated.DomainEmployment.Client;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class GeneratedEmploymentCommandOwnerGatewayTests : IDisposable
{
    private readonly string _credentials = Path.Combine(
        Path.GetTempPath(),
        $"waooaw-employment-identity-{Guid.NewGuid():N}"
    );

    [Fact]
    public async Task GeneratedOwnersValidateBoundDomainWbeAndCeInputs()
    {
        Bootstrap();
        using var identity = WorkloadIdentityClient.Load(_credentials);
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var persistence = new OwnerContextPersistence();
        persistence.Context = new EmploymentOwnerContext(
            "plan-1",
            "PLAN_VALIDATION",
            "assessment-context-1",
            new string('a', 64),
            Json(
                """
                {
                  "schemaVersion": "1.0",
                  "manifestVersion": "manifest-1",
                  "requirementSetVersion": "requirements-1",
                  "planVersion": "plan-1",
                  "goalType": "generic",
                  "skillRefs": ["skill-1"],
                  "milestoneTypes": [],
                  "sourceVersion": "source-1"
                }
                """
            )
        );
        using var domain = Client(request =>
        {
            var path = request.RequestUri!.AbsolutePath;
            if (path.Contains("induction-requirements"))
                return """
                    {
                      "schemaVersion":"1.0",
                      "manifestVersion":"manifest-1",
                      "requirementSetVersion":"requirements-1",
                      "requirements":[{
                        "requirementRef":"requirement-1",
                        "label":"Generic requirement",
                        "mandatory":true,
                        "dependencyType":"GENERIC",
                        "affectedSkillRefs":["skill-1"]
                      }],
                      "producedAt":"2026-10-08T00:00:00Z"
                    }
                    """;
            if (path.Contains("material-change-classification"))
                return """
                    {
                      "schemaVersion":"1.0",
                      "classification":"MATERIAL",
                      "reasons":["Protected category changed"],
                      "affectedSkillRefs":["skill-1"],
                      "affectedWorkRefs":["work-1"],
                      "renewedAgreementRequired":true
                    }
                    """;
            if (path.Contains("dependency-isolation"))
                return """
                    {
                      "schemaVersion":"1.0",
                      "isolation":"PROVEN_BOUNDED",
                      "affectedSkillRefs":["skill-1"],
                      "dependentWorkRefs":[],
                      "rationale":"Dependency impact is bounded."
                    }
                    """;
            if (path.Contains("performance-assessments"))
                return """
                    {
                      "schemaVersion":"1.0",
                      "assessmentVersion":"performance-1",
                      "reviewPeriodRef":"review-1",
                      "outcomeLabel":"Bounded outcome",
                      "outcomeState":"MISSED",
                      "attributionBasis":"Evidence-backed review",
                      "attributionConfidence":0.9,
                      "agentPerformanceState":"NOT_MEETING",
                      "missedReviewPeriods":2,
                      "diagnosisRequired":true,
                      "correctiveProposalRequired":true,
                      "evidenceRefs":["evidence-1"],
                      "limitations":[],
                      "producedAt":"2026-10-08T00:00:00Z"
                    }
                    """;
            if (path.Contains("material-change-classification"))
                return """
                    {
                      "schemaVersion":"1.0",
                      "classification":"UNKNOWN",
                      "reasons":["Materiality unavailable"],
                      "affectedSkillRefs":[],
                      "affectedWorkRefs":[],
                      "renewedAgreementRequired":true
                    }
                    """;
            if (path.Contains("dependency-isolation"))
                return """
                    {
                      "schemaVersion":"1.0",
                      "isolation":"UNKNOWN",
                      "affectedSkillRefs":["skill-1"],
                      "dependentWorkRefs":[],
                      "rationale":"Isolation evidence unavailable."
                    }
                    """;
            return """
                {
                  "schemaVersion":"1.0",
                  "assessmentVersion":"assessment-1",
                  "state":"VALID",
                  "unmetDomainConditions":[],
                  "limitations":[],
                  "producedAt":"2026-10-08T00:00:00Z"
                }
                """;
        });
        using var wbe = Client(_ =>
            $$"""
                {
                  "schemaVersion":"1.0",
                  "relationshipId":"{{relationshipId:D}}",
                  "planVersion":"plan-1",
                  "manifestVersion":"manifest-1",
                  "sourceProjectionVersion":"wbe-1",
                  "currencyState":"CURRENT",
                  "skillEligibility":[{
                    "skillRef":"skill-1",
                    "state":"ELIGIBLE",
                    "consequentialWorkFunded":true,
                    "reasonCode":"FUNDED"
                  }],
                  "preservedPathClasses":[
                    "EMERGENCY_STOP",
                    "CONSTITUTIONAL_RIGHTS",
                    "EVIDENCE_READ",
                    "READ_ONLY_REVIEW"
                  ],
                  "producedAt":"2026-10-08T00:00:00Z"
                }
                """
        );
        using var gateway = new GeneratedEmploymentCommandOwnerGateway(
            identity,
            domain,
            wbe,
            new AllowingConstitutionalGateway(),
            persistence
        );
        var workspace = Workspace(tenantId, relationshipId);
        var generatedResult = await new EmploymentDomainSemanticsApi(
            domain,
            new Configuration { BasePath = domain.BaseAddress!.ToString() }
        ).GetInductionRequirementSetAsync(
            relationshipId,
            "manifest-1",
            Guid.NewGuid(),
            CancellationToken.None
        );
        Assert.Equal("requirements-1", generatedResult.RequirementSetVersion);

        var induction = await gateway.ValidateAsync(
            "DOMAIN_ADAPTER",
            Context(
                tenantId,
                relationshipId,
                "CONFIRM_INDUCTION_ITEM",
                Json("""{"subjectRef":"requirement-1"}"""),
                workspace
            ),
            CancellationToken.None
        );
        var planCommand = Json(
            """
            {
              "subjectRef":"plan-1",
              "expectedPlanVersion":"plan-1",
              "expectedWbeSourceVersion":"wbe-1"
            }
            """
        );
        var planContext = Context(
            tenantId,
            relationshipId,
            "ACCEPT_PLAN_VERSION",
            planCommand,
            workspace
        );
        var plan = await gateway.ValidateAsync(
            "DOMAIN_ADAPTER",
            planContext,
            CancellationToken.None
        );
        var eligibility = await gateway.ValidateAsync("WBE", planContext, CancellationToken.None);
        var constitutional = await gateway.ValidateAsync("CE", planContext, CancellationToken.None);
        var invalid = await gateway.ValidateAsync("PR", planContext, CancellationToken.None);

        Assert.Equal("COMPLETED", induction.State);
        Assert.Equal("requirements-1", induction.SourceVersion);
        Assert.Equal("COMPLETED", plan.State);
        Assert.Equal("assessment-1", plan.SourceVersion);
        Assert.Equal("COMPLETED", eligibility.State);
        Assert.Equal("wbe-1", eligibility.SourceVersion);
        Assert.Equal("COMPLETED", constitutional.State);
        Assert.Equal("BLOCKED", invalid.State);

        persistence.Context = new EmploymentOwnerContext(
            "patch-1",
            "CANDIDATE_PATCH_DOMAIN_REQUEST",
            "material-context-1",
            new string('b', 64),
            Json(
                $$"""
                {
                  "operation":"classifyMaterialChange",
                  "request":{
                    "schemaVersion":"1.0",
                    "manifestVersion":"manifest-1",
                    "currentPlanVersion":"plan-1",
                    "candidatePatchRef":"{{Guid.NewGuid():D}}",
                    "protectedCategoryFlags":["OUTCOME"]
                  }
                }
                """
            )
        );
        var material = await gateway.ValidateAsync(
            "DOMAIN_ADAPTER",
            Context(
                tenantId,
                relationshipId,
                "ACKNOWLEDGE_MATERIAL_CHANGE",
                Json("""{"subjectRef":"patch-1"}"""),
                workspace
            ),
            CancellationToken.None
        );
        persistence.Context = new EmploymentOwnerContext(
            "dependency-1",
            "CANDIDATE_PATCH_DOMAIN_REQUEST",
            "dependency-context-1",
            new string('c', 64),
            Json(
                """
                {
                  "operation":"evaluateDependencyIsolation",
                  "request":{
                    "schemaVersion":"1.0",
                    "manifestVersion":"manifest-1",
                    "dependencyRef":"credential-1",
                    "dependencyState":"LOST",
                    "candidateAffectedSkillRefs":["skill-1"]
                  }
                }
                """
            )
        );
        var dependency = await gateway.ValidateAsync(
            "DOMAIN_ADAPTER",
            Context(
                tenantId,
                relationshipId,
                "APPLY_CANDIDATE_PATCH",
                Json("""{"subjectRef":"dependency-1"}"""),
                workspace
            ),
            CancellationToken.None
        );
        var performance = await gateway.ValidateAsync(
            "DOMAIN_ADAPTER",
            Context(
                tenantId,
                relationshipId,
                "REQUEST_REASSESSMENT",
                Json("""{"subjectRef":"review-1"}"""),
                workspace
            ),
            CancellationToken.None
        );

        Assert.Equal("COMPLETED", material.State);
        Assert.Equal("COMPLETED", dependency.State);
        Assert.Equal("COMPLETED", performance.State);
        Assert.Equal("performance-1", performance.SourceVersion);
    }

    [Fact]
    public async Task MissingConfigurationAndOwnerContextFailClosed()
    {
        var context = Context(
            Guid.NewGuid(),
            Guid.NewGuid(),
            "ACCEPT_PLAN_VERSION",
            Json("""{"subjectRef":"plan-1","expectedPlanVersion":"plan-1"}"""),
            Workspace(Guid.NewGuid(), Guid.NewGuid())
        );
        var unavailable = await new UnconfiguredEmploymentCommandOwnerGateway().ValidateAsync(
            "DOMAIN_ADAPTER",
            context,
            CancellationToken.None
        );
        Assert.Equal("UNKNOWN", unavailable.State);

        Bootstrap();
        using var identity = WorkloadIdentityClient.Load(_credentials);
        using var gateway = new GeneratedEmploymentCommandOwnerGateway(
            identity,
            Client(_ => "{}"),
            Client(_ => "{}"),
            new AllowingConstitutionalGateway(),
            new OwnerContextPersistence()
        );
        var missing = await gateway.ValidateAsync(
            "DOMAIN_ADAPTER",
            context,
            CancellationToken.None
        );
        Assert.Equal("UNKNOWN", missing.State);
    }

    [Fact]
    public async Task NonSuccessDomainAssessmentsRemainDistinctAndFailClosed()
    {
        Bootstrap();
        using var identity = WorkloadIdentityClient.Load(_credentials);
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var persistence = new OwnerContextPersistence
        {
            Context = new EmploymentOwnerContext(
                "plan-1",
                "PLAN_VALIDATION",
                "assessment-context-1",
                new string('d', 64),
                Json(
                    """
                    {
                      "schemaVersion":"1.0",
                      "manifestVersion":"manifest-1",
                      "requirementSetVersion":"requirements-1",
                      "planVersion":"plan-1",
                      "goalType":"generic",
                      "skillRefs":["skill-1"],
                      "milestoneTypes":[],
                      "sourceVersion":"source-1"
                    }
                    """
                )
            ),
        };
        using var domain = Client(request =>
        {
            var path = request.RequestUri!.AbsolutePath;
            if (path.Contains("performance-assessments"))
                return """
                    {
                      "schemaVersion":"1.0",
                      "assessmentVersion":"performance-unknown",
                      "reviewPeriodRef":"review-unknown",
                      "outcomeLabel":"Unknown outcome",
                      "outcomeState":"UNKNOWN",
                      "attributionBasis":"Insufficient evidence",
                      "attributionConfidence":0,
                      "agentPerformanceState":"UNKNOWN",
                      "missedReviewPeriods":0,
                      "evidenceRefs":[],
                      "limitations":["Evidence unavailable"],
                      "producedAt":"2026-10-08T00:00:00Z"
                    }
                    """;
            return """
                {
                  "schemaVersion":"1.0",
                  "assessmentVersion":"assessment-invalid",
                  "state":"INVALID",
                  "unmetDomainConditions":["Domain condition failed"],
                  "limitations":[],
                  "producedAt":"2026-10-08T00:00:00Z"
                }
                """;
        });
        using var gateway = new GeneratedEmploymentCommandOwnerGateway(
            identity,
            domain,
            Client(_ => "{}"),
            new AllowingConstitutionalGateway(),
            persistence
        );
        var workspace = Workspace(tenantId, relationshipId);
        var rejected = await gateway.ValidateAsync(
            "DOMAIN_ADAPTER",
            Context(
                tenantId,
                relationshipId,
                "SUBMIT_PLAN_FOR_REVIEW",
                Json("""{"subjectRef":"plan-1","expectedPlanVersion":"plan-1"}"""),
                workspace
            ),
            CancellationToken.None
        );
        var unknown = await gateway.ValidateAsync(
            "DOMAIN_ADAPTER",
            Context(
                tenantId,
                relationshipId,
                "REQUEST_REASSESSMENT",
                Json("""{"subjectRef":"review-unknown"}"""),
                workspace
            ),
            CancellationToken.None
        );
        persistence.Context = new EmploymentOwnerContext(
            "patch-unknown",
            "CANDIDATE_PATCH_DOMAIN_REQUEST",
            "material-unknown",
            new string('e', 64),
            Json(
                $$"""
                {
                  "operation":"classifyMaterialChange",
                  "request":{
                    "schemaVersion":"1.0",
                    "manifestVersion":"manifest-1",
                    "currentPlanVersion":"plan-1",
                    "candidatePatchRef":"{{Guid.NewGuid():D}}",
                    "protectedCategoryFlags":[]
                  }
                }
                """
            )
        );
        var materialUnknown = await gateway.ValidateAsync(
            "DOMAIN_ADAPTER",
            Context(
                tenantId,
                relationshipId,
                "APPLY_CANDIDATE_PATCH",
                Json("""{"subjectRef":"patch-unknown"}"""),
                workspace
            ),
            CancellationToken.None
        );
        persistence.Context = new EmploymentOwnerContext(
            "dependency-unknown",
            "CANDIDATE_PATCH_DOMAIN_REQUEST",
            "dependency-unknown",
            new string('f', 64),
            Json(
                """
                {
                  "operation":"evaluateDependencyIsolation",
                  "request":{
                    "schemaVersion":"1.0",
                    "manifestVersion":"manifest-1",
                    "dependencyRef":"credential-unknown",
                    "dependencyState":"UNKNOWN",
                    "candidateAffectedSkillRefs":["skill-1"]
                  }
                }
                """
            )
        );
        var dependencyUnknown = await gateway.ValidateAsync(
            "DOMAIN_ADAPTER",
            Context(
                tenantId,
                relationshipId,
                "APPLY_CANDIDATE_PATCH",
                Json("""{"subjectRef":"dependency-unknown"}"""),
                workspace
            ),
            CancellationToken.None
        );

        Assert.Equal("REJECTED", rejected.State);
        Assert.Equal("UNKNOWN", unknown.State);
        Assert.Equal("UNKNOWN", materialUnknown.State);
        Assert.Equal("UNKNOWN", dependencyUnknown.State);
    }

    private static EmploymentCommandCoordinationContext Context(
        Guid tenantId,
        Guid relationshipId,
        string kind,
        JsonElement command,
        EmploymentWorkspaceSnapshot workspace
    ) => new(tenantId, relationshipId, Guid.NewGuid(), Guid.NewGuid(), kind, command, workspace);

    private static EmploymentWorkspaceSnapshot Workspace(Guid tenantId, Guid relationshipId) =>
        new(
            tenantId,
            relationshipId,
            "workspace-1",
            "manifest-1",
            Json("""{"agentType":"neutral-professional"}"""),
            new Dictionary<string, JsonElement>(),
            Json("{}"),
            new Dictionary<string, JsonElement>(),
            "plan-1",
            1,
            "wbe-1"
        );

    private static HttpClient Client(Func<HttpRequestMessage, string> response) =>
        new(new StubHandler(response)) { BaseAddress = new Uri("https://owner.test") };

    private void Bootstrap()
    {
        if (Directory.Exists(_credentials))
            return;
        var root = RepositoryPaths.Root();
        var process =
            Process.Start(
                new ProcessStartInfo
                {
                    FileName = "python3",
                    ArgumentList =
                    {
                        Path.Combine(root, "scripts", "bootstrap_workload_identity.py"),
                        "--registry",
                        Path.Combine(root, "infrastructure", "workload-identity", "registry.yaml"),
                        "--environment",
                        "ci",
                        "--output",
                        _credentials,
                    },
                    RedirectStandardError = true,
                    UseShellExecute = false,
                }
            ) ?? throw new InvalidOperationException("Could not bootstrap workload identity.");
        process.WaitForExit();
        Assert.Equal(0, process.ExitCode);
    }

    private static JsonElement Json(string value)
    {
        using var document = JsonDocument.Parse(value);
        return document.RootElement.Clone();
    }

    public void Dispose()
    {
        if (Directory.Exists(_credentials))
            Directory.Delete(_credentials, recursive: true);
    }

    private sealed class StubHandler(Func<HttpRequestMessage, string> response) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        ) =>
            Task.FromResult(
                new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = new StringContent(
                        response(request),
                        Encoding.UTF8,
                        "application/json"
                    ),
                }
            );
    }

    private sealed class AllowingConstitutionalGateway : IRelationshipConstitutionalGateway
    {
        public Task<Guid> AuthorizeAndRecordAsync(
            Guid tenantId,
            Guid relationshipId,
            string professionalType,
            string actionType,
            Guid correlationId,
            object actionParameters,
            CancellationToken cancellationToken
        ) => Task.FromResult(Guid.NewGuid());
    }

    private sealed class OwnerContextPersistence : IConversationalEmploymentPersistence
    {
        public EmploymentOwnerContext? Context { get; set; }

        public EmploymentOwnerContext? LoadOwnerContext(
            Guid tenantId,
            Guid relationshipId,
            string contextRef,
            string contextKind
        ) => Context is { } value && value.ContextRef == contextRef ? value : null;

        public EmploymentWorkspaceSnapshot? LoadWorkspace(Guid tenantId, Guid relationshipId) =>
            throw new NotSupportedException();

        public void AppendWorkspace(EmploymentWorkspaceSnapshot snapshot) =>
            throw new NotSupportedException();

        public EmploymentCommandOutcome? LoadCommand(
            Guid tenantId,
            Guid relationshipId,
            Guid commandId
        ) => throw new NotSupportedException();

        public PersistedEmploymentCommand ReserveCommand(
            Guid tenantId,
            Guid relationshipId,
            Guid actorId,
            Guid idempotencyKey,
            string commandKind,
            string canonicalDigest,
            string expectedWorkspaceVersion,
            string expectedManifestVersion,
            EmploymentCommandOutcome proposed
        ) => throw new NotSupportedException();

        public void AppendCommandOutcome(
            Guid tenantId,
            Guid relationshipId,
            EmploymentCommandOutcome outcome
        ) => throw new NotSupportedException();

        public Guid EraseProjectionContent(
            Guid tenantId,
            Guid relationshipId,
            string authorityRef
        ) => throw new NotSupportedException();

        public void AppendOwnerContext(
            Guid tenantId,
            Guid relationshipId,
            EmploymentOwnerContext context
        ) => Context = context;
    }
}
