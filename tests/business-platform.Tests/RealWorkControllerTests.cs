// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R011 (B6 tenant check, B8 controller tests)
// Constitutional basis: C-001, C-023, C-059, C-063, C-076, ADR-046
// IB: IB-171

using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.RealWork;
using Waooaw.WorkloadIdentity;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class RealWorkIngestControllerTests(OwnerGatewayIdentityFixture fixture)
    : IClassFixture<OwnerGatewayIdentityFixture>,
        IDisposable
{
    private static readonly Guid Tenant = Guid.NewGuid();
    private static readonly Guid Relationship = Guid.NewGuid();
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    private readonly X509Certificate2 _peer = X509Certificate2.CreateFromPem(
        File.ReadAllText(
            Path.Combine(
                fixture.CredentialsPath,
                "workloads",
                "professional-runtime",
                "tls-cert.pem"
            )
        )
    );

    [Fact]
    public async Task ASignedEventForTheSignedTenantAndRelationshipIsIngested()
    {
        var (controller, timeline) = Controller();
        var body = Event(Tenant, Relationship);
        Sign(controller.HttpContext, body, Tenant, Relationship);

        var result = await controller.IngestAsync(body, CancellationToken.None);

        Assert.IsType<OkObjectResult>(result);
        Assert.Single(timeline.Read(Tenant, Relationship).Events);
    }

    [Theory]
    [InlineData("tenant")]
    [InlineData("relationship")]
    public async Task ABodyNamingAnotherTenantOrRelationshipThanTheSignedEnvelopeIsRefusedAndWritesNothing(
        string defect
    )
    {
        var (controller, timeline) = Controller();
        var otherTenant = Guid.NewGuid();
        var otherRelationship = Guid.NewGuid();
        var body =
            defect == "tenant"
                ? Event(otherTenant, Relationship)
                : Event(Tenant, otherRelationship);
        Sign(controller.HttpContext, body, Tenant, Relationship);

        var result = Assert.IsType<ObjectResult>(
            await controller.IngestAsync(body, CancellationToken.None)
        );

        Assert.Equal(403, result.StatusCode);
        Assert.Equal(
            "{\"code\":\"REAL_WORK_AUTHORITY_DENIED\"}",
            JsonSerializer.Serialize(result.Value, Json)
        );
        Assert.Empty(timeline.Read(otherTenant, Relationship).Events);
        Assert.Empty(timeline.Read(Tenant, otherRelationship).Events);
        Assert.Empty(timeline.Read(Tenant, Relationship).Events);
    }

    [Fact]
    public async Task AnUnsignedCallIsDeniedBeforeAnyOwnerIsReached()
    {
        var (controller, timeline) = Controller();
        var body = Event(Tenant, Relationship);

        var result = Assert.IsType<ObjectResult>(
            await controller.IngestAsync(body, CancellationToken.None)
        );

        Assert.Equal(403, result.StatusCode);
        Assert.Empty(timeline.Read(Tenant, Relationship).Events);
    }

    [Fact]
    public async Task AnUnknownTypeOrAnEventWithoutItsPayloadIsAnInvalidRequest()
    {
        var (controller, _) = Controller();
        var body = JsonSerializer.SerializeToElement(
            new
            {
                type = "TIMELINE_EVENT",
                tenantId = Tenant,
                relationshipId = Relationship,
            },
            Json
        );
        Sign(controller.HttpContext, body, Tenant, Relationship);

        var result = Assert.IsType<ObjectResult>(
            await controller.IngestAsync(body, CancellationToken.None)
        );

        Assert.Equal(400, result.StatusCode);
    }

    [Fact]
    public async Task ABlindRetryOfAnUnknownOutcomeIsAConflictTheRuntimeCanRecognise()
    {
        var (controller, timeline) = Controller();
        var workItem = Guid.NewGuid();
        timeline.Ingest(
            Tenant,
            Relationship,
            new TimelineEventInput(
                Guid.NewGuid(),
                workItem,
                "SOCIAL_POST",
                TimelineStates.Executing,
                DateTimeOffset.UtcNow,
                ReasonCode: TimelineReasons.UnknownOutcome,
                ProducesArtifact: true
            )
        );
        var body = Event(Tenant, Relationship, workItem, TimelineStates.Executing, true);
        Sign(controller.HttpContext, body, Tenant, Relationship);

        var result = Assert.IsType<ObjectResult>(
            await controller.IngestAsync(body, CancellationToken.None)
        );

        Assert.Equal(409, result.StatusCode);
        Assert.Equal(
            "{\"code\":\"REAL_WORK_BLIND_RETRY\"}",
            JsonSerializer.Serialize(result.Value, Json)
        );
    }

    private (RealWorkIngestController Controller, RealWorkTimelineService Timeline) Controller()
    {
        var ledger = new InMemoryRealWorkLedger();
        var artifacts = new RealWorkArtifactService(ledger, TimeProvider.System);
        var decisions = new RealWorkDecisionService(
            ledger,
            artifacts,
            Mock.Of<IRelationshipConstitutionalGateway>(),
            TimeProvider.System
        );
        var timeline = new RealWorkTimelineService(ledger, decisions, TimeProvider.System);
        var outcomes = new RealWorkOutcomeService(ledger, timeline, TimeProvider.System);
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(
                new Dictionary<string, string?>
                {
                    ["WAOOAW_WORKLOAD_CREDENTIALS"] = fixture.CredentialsPath,
                }
            )
            .Build();
        var controller = new RealWorkIngestController(
            new InferenceWorkloadValidator(configuration, TimeProvider.System),
            artifacts,
            timeline,
            outcomes,
            NullLogger<RealWorkIngestController>.Instance
        )
        {
            ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() },
        };
        return (controller, timeline);
    }

    private static JsonElement Event(
        Guid tenant,
        Guid relationship,
        Guid? workItem = null,
        string state = TimelineStates.Proposed,
        bool producesArtifact = false
    ) =>
        JsonSerializer.SerializeToElement(
            new
            {
                type = "TIMELINE_EVENT",
                tenantId = tenant,
                relationshipId = relationship,
                @event = new
                {
                    eventId = Guid.NewGuid(),
                    workItemId = workItem ?? Guid.NewGuid(),
                    workItemType = "SOCIAL_POST",
                    state,
                    occurredAt = DateTimeOffset.UtcNow,
                    producesArtifact,
                },
            },
            Json
        );

    private void Sign(HttpContext http, JsonElement body, Guid tenant, Guid relationship)
    {
        using var manifest = JsonDocument.Parse(
            File.ReadAllText(Path.Combine(fixture.CredentialsPath, "manifest.json"))
        );
        var workloads = manifest.RootElement.GetProperty("workloads");
        var source = workloads.GetProperty("professional-runtime");
        var target = workloads.GetProperty("business-platform");
        var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        var envelope = new Dictionary<string, object>
        {
            ["issuer_uri"] = source.GetProperty("identity_uri").GetString()!,
            ["key_id"] = source.GetProperty("delegation_key_id").GetString()!,
            ["target_audience"] = target.GetProperty("audience").GetString()!,
            ["method"] = "POST",
            ["route"] = "/" + RealWorkIngestController.Route,
            ["operation"] = RealWorkIngestController.Operation,
            ["schema_version"] = "1.0",
            ["contract_major"] = 1,
            ["purpose"] = RealWorkIngestController.Purpose,
            ["actor_source"] = RealWorkIngestController.ActorSource,
            ["request_digest"] = Convert.ToHexStringLower(
                SHA256.HashData(
                    Encoding.UTF8.GetBytes(AgentAdmissionCanonicalizer.Canonicalize(body))
                )
            ),
            ["issued_at"] = now,
            ["not_before"] = now,
            ["expires_at"] = now + 60,
            ["tenant_id"] = tenant.ToString("D"),
            ["relationship_id"] = relationship.ToString("D"),
            ["actor_subject"] = "professional-runtime",
            ["effective_role"] = "PROFESSIONAL_RUNTIME",
            ["subject_reference"] = Guid.NewGuid().ToString("D"),
            ["command_id"] = Guid.NewGuid().ToString("D"),
            ["idempotency_key"] = Guid.NewGuid().ToString("D"),
            ["expected_versions"] = new Dictionary<string, string>(),
            ["envelope_id"] = Guid.NewGuid().ToString("D"),
        };
        using var signing = ECDsa.Create();
        signing.ImportFromPem(
            File.ReadAllText(
                Path.Combine(
                    fixture.CredentialsPath,
                    "workloads",
                    "professional-runtime",
                    "delegation-key.pem"
                )
            )
        );
        var payload = JsonSerializer.SerializeToUtf8Bytes(envelope);
        static string Encode(byte[] value) =>
            Convert.ToBase64String(value).TrimEnd('=').Replace('+', '-').Replace('/', '_');
        http.Request.Method = "POST";
        http.Request.Path = "/" + RealWorkIngestController.Route;
        http.Connection.ClientCertificate = _peer;
        http.Request.Headers.Authorization =
            "Bearer "
            + Encode(payload)
            + "."
            + Encode(
                signing.SignData(
                    payload,
                    HashAlgorithmName.SHA256,
                    DSASignatureFormat.Rfc3279DerSequence
                )
            );
    }

    public void Dispose() => _peer.Dispose();
}

public sealed class RealWorkControllerTests
{
    private static RealWorkController Controller(bool gateEnabled, string? tenantItem)
    {
        var gate = new Mock<IEmploymentProtocolGate>();
        gate.Setup(value => value.Snapshot())
            .Returns(new EmploymentProtocolGateSnapshot("gate", gateEnabled, 1));
        var ledger = new InMemoryRealWorkLedger();
        var artifacts = new RealWorkArtifactService(ledger, TimeProvider.System);
        var decisions = new RealWorkDecisionService(
            ledger,
            artifacts,
            Mock.Of<IRelationshipConstitutionalGateway>(),
            TimeProvider.System
        );
        var timeline = new RealWorkTimelineService(ledger, decisions, TimeProvider.System);
        var controller = new RealWorkController(
            null!,
            gate.Object,
            null!,
            artifacts,
            decisions,
            timeline,
            new RealWorkOutcomeService(ledger, timeline, TimeProvider.System)
        )
        {
            ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() },
        };
        if (tenantItem is not null)
            controller.HttpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantItem;
        return controller;
    }

    [Fact]
    public async Task EveryReadAnswersTheSameNotAccessibleCodeWhenTheProtocolIsOff()
    {
        var controller = Controller(false, Guid.NewGuid().ToString());
        var relationship = Guid.NewGuid();

        foreach (
            var result in new[]
            {
                await controller.ListArtifactsAsync(relationship, null, CancellationToken.None),
                await controller.GetArtifactAsync(
                    relationship,
                    Guid.NewGuid(),
                    CancellationToken.None
                ),
                await controller.GetTimelineAsync(relationship, CancellationToken.None),
                await controller.GetOutcomesAsync(relationship, CancellationToken.None),
                await controller.GetOutcomeTraceAsync(
                    relationship,
                    "claim",
                    CancellationToken.None
                ),
            }
        )
        {
            var refused = Assert.IsType<ObjectResult>(result);
            Assert.Equal(404, refused.StatusCode);
            Assert.Equal(
                "{\"code\":\"EMPLOYMENT_NOT_ACCESSIBLE\"}",
                JsonSerializer.Serialize(refused.Value)
            );
        }
        Assert.Equal("no-store", controller.Response.Headers.CacheControl.ToString());
    }

    [Theory]
    [InlineData(null)]
    [InlineData("not-a-guid")]
    public async Task ARequestWithoutAResolvedTenantIsNotAccessible(string? tenant)
    {
        var controller = Controller(true, tenant);

        var result = Assert.IsType<ObjectResult>(
            await controller.GetTimelineAsync(Guid.NewGuid(), CancellationToken.None)
        );

        Assert.Equal(404, result.StatusCode);
    }
}
