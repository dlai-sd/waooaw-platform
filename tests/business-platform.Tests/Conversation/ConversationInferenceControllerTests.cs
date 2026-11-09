// Implements: WC-134 R006/R008; ADR-046 private generation and recovery boundaries.
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Grpc.Core;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Services;
using Waooaw.WorkloadIdentity;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class ConversationInferenceControllerTests(OwnerGatewayIdentityFixture fixture)
    : IClassFixture<OwnerGatewayIdentityFixture>,
        IDisposable
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    private readonly X509Certificate2 _peer = X509Certificate2.CreateFromPem(
        File.ReadAllText(
            Path.Combine(fixture.CredentialsPath, "workloads", "ai-runtime", "tls-cert.pem")
        )
    );

    [Theory]
    [InlineData("resolve")]
    [InlineData("reserve")]
    [InlineData("reconcile")]
    [InlineData("settle")]
    [InlineData("release")]
    [InlineData("read-content")]
    public async Task ExactSignedCallerAndOriginalRequestReachOnlyTheSelectedOwner(string operation)
    {
        var request = await RequestAsync();
        var caller = Caller(request, operation);
        var owner = new Mock<IConversationInferenceOwner>(MockBehavior.Strict);
        var resolved = JsonSerializer.SerializeToElement(new { state = "RESOLVED" });
        var permit = new ConversationInferencePermitV1(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            10,
            DateTimeOffset.UtcNow.AddSeconds(30),
            resolved
        );
        var permission = new RuntimeReconciliationRequestV1(
            "1.0",
            request.ContributionRef,
            new string('a', 64),
            4,
            caller.ExecutionId,
            DateTimeOffset.UtcNow.AddMinutes(1),
            7
        );
        var body =
            operation == "read-content"
                ? JsonSerializer.SerializeToElement(
                    new ConversationInferenceContentReadRequest(request, permission),
                    Json
                )
                : Body(request, operation);
        owner
            .Setup(value =>
                value.ResolveAsync(
                    caller,
                    It.Is<ConversationInferenceRequest>(value => Matches(value, request)),
                    It.IsAny<CancellationToken>()
                )
            )
            .ReturnsAsync(resolved);
        owner
            .Setup(value =>
                value.ReserveAsync(
                    caller,
                    It.Is<ConversationInferenceRequest>(value => Matches(value, request)),
                    It.IsAny<CancellationToken>()
                )
            )
            .ReturnsAsync(permit);
        owner
            .Setup(value =>
                value.ReconcileAsync(
                    caller,
                    It.Is<ConversationInferenceRequest>(value => Matches(value, request)),
                    It.IsAny<CancellationToken>()
                )
            )
            .ReturnsAsync(new ConversationInferenceReceiptV1("UNKNOWN"));
        owner
            .Setup(value =>
                value.SettleAsync(
                    caller,
                    It.Is<ConversationInferenceRequest>(value => Matches(value, request)),
                    operation == "release",
                    It.IsAny<CancellationToken>()
                )
            )
            .Returns(Task.CompletedTask);
        owner
            .Setup(value =>
                value.ReadContentAsync(
                    caller,
                    It.Is<ConversationInferenceContentReadRequest>(value =>
                        Matches(value.Original, request) && value.Permission == permission
                    ),
                    It.IsAny<CancellationToken>()
                )
            )
            .ReturnsAsync(new ConversationInferenceContentReadV1("ALLOWED"));
        var controller = Controller(owner.Object);
        Sign(controller.HttpContext, body, caller, operation);
        var result = Assert.IsType<OkObjectResult>(await InvokeAsync(controller, operation, body));
        Assert.Single(owner.Invocations);
        Assert.Equal(caller, owner.Invocations[0].Arguments[0]);
        if (operation is "settle" or "release")
            Assert.Equal(
                operation == "release" ? "RELEASED" : "SETTLED",
                Assert.IsType<ConversationInferenceSettlementV1>(result.Value).State
            );
        else if (operation == "reserve")
            Assert.Equal(permit, result.Value);
        else if (operation == "reconcile")
            Assert.Equal(
                "UNKNOWN",
                Assert.IsType<ConversationInferenceReceiptV1>(result.Value).State
            );
        else if (operation == "read-content")
            Assert.Equal(
                "ALLOWED",
                Assert.IsType<ConversationInferenceContentReadV1>(result.Value).State
            );
        else
            Assert.Equal(
                resolved.GetRawText(),
                Assert.IsType<JsonElement>(result.Value).GetRawText()
            );
    }

    public static IEnumerable<object[]> Failures()
    {
        yield return [new ConversationNotAccessibleException(), 403, "INFERENCE_AUTHORITY_DENIED"];
        yield return
        [
            new ConstitutionalActionDeniedException("private authority details"),
            403,
            "INFERENCE_AUTHORITY_DENIED",
        ];
        yield return [new ConversationStateConflictException(), 409, "INFERENCE_BINDING_CONFLICT"];
        yield return
        [
            new OperationalMandateUnavailableException(),
            409,
            "INFERENCE_BINDING_CONFLICT",
        ];
        yield return
        [
            new JsonException("private binding details"),
            409,
            "INFERENCE_BINDING_CONFLICT",
        ];
        yield return [new ConversationStoppedException(), 423, "INFERENCE_STOPPED"];
        yield return
        [
            new WhatsAppCapabilityUnavailableException("MODEL_CONCURRENCY_DENIED"),
            503,
            "INFERENCE_BUSY",
        ];
        yield return
        [
            new WhatsAppCapabilityUnavailableException("MODEL_COST_OVERRUN_HALTED"),
            503,
            "INFERENCE_DEPENDENCY_UNAVAILABLE",
        ];
        yield return
        [
            new ConversationExecutionUnavailableException(),
            503,
            "INFERENCE_DEPENDENCY_UNAVAILABLE",
        ];
        yield return
        [
            new IdentityConstitutionalUnavailableException("private evidence details"),
            503,
            "INFERENCE_DEPENDENCY_UNAVAILABLE",
        ];
        yield return
        [
            new RpcException(new Status(StatusCode.Unavailable, "private transport details")),
            503,
            "INFERENCE_DEPENDENCY_UNAVAILABLE",
        ];
    }

    [Theory]
    [MemberData(nameof(Failures))]
    public async Task OwnerFailuresRemainExplicitAndPrivacySafe(
        Exception error,
        int status,
        string code
    )
    {
        var request = await RequestAsync();
        var body = Body(request, "resolve");
        var owner = new Mock<IConversationInferenceOwner>(MockBehavior.Strict);
        owner
            .Setup(value =>
                value.ResolveAsync(
                    It.IsAny<InferenceCaller>(),
                    It.IsAny<ConversationInferenceRequest>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .ThrowsAsync(error);
        var controller = Controller(owner.Object);
        Sign(controller.HttpContext, body, Caller(request, "resolve"), "resolve");
        var result = Assert.IsAssignableFrom<ObjectResult>(
            await controller.Resolve(body, CancellationToken.None)
        );
        Assert.Equal(status, result.StatusCode);
        Assert.Equal($"{{\"code\":\"{code}\"}}", JsonSerializer.Serialize(result.Value, Json));
        if (code == "INFERENCE_BUSY")
        {
            Assert.Equal("5", controller.Response.Headers.RetryAfter.ToString());
            Assert.Equal("QUEUED", controller.Response.Headers["X-Inference-State"].ToString());
        }
        else
        {
            Assert.Empty(controller.Response.Headers);
        }
        Assert.Single(owner.Invocations);
    }

    [Theory]
    [InlineData("unknown")]
    [InlineData("duplicate")]
    [InlineData("operationalMandate")]
    [InlineData("requestDigest")]
    [InlineData("inputDigest")]
    [InlineData("inputLanguage")]
    [InlineData("null")]
    public async Task MalformedClosedBodiesCannotInvokeTheOwner(string defect)
    {
        var request = await RequestAsync();
        var original = Body(request, "resolve");
        var node = JsonNode.Parse(original.GetRawText())!.AsObject();
        if (defect == "unknown")
            node["unapproved"] = true;
        else if (defect is not ("duplicate" or "null"))
            node.Remove(defect);
        var body = defect switch
        {
            "duplicate" => JsonDocument
                .Parse(
                    "{\"executionId\":\"" + request.ExecutionId + "\"," + original.GetRawText()[1..]
                )
                .RootElement.Clone(),
            "null" => JsonSerializer.SerializeToElement<object?>(null),
            _ => JsonSerializer.SerializeToElement(node),
        };
        var owner = new Mock<IConversationInferenceOwner>(MockBehavior.Strict);
        var controller = Controller(owner.Object);
        Sign(controller.HttpContext, body, Caller(request, "resolve"), "resolve");
        var result = Assert.IsType<ConflictObjectResult>(
            await controller.Resolve(body, CancellationToken.None)
        );
        Assert.Equal(
            "{\"code\":\"INFERENCE_BINDING_CONFLICT\"}",
            JsonSerializer.Serialize(result.Value, Json)
        );
        owner.VerifyNoOtherCalls();
    }

    [Theory]
    [InlineData("certificate")]
    [InlineData("header")]
    [InlineData("digest")]
    [InlineData("purpose")]
    [InlineData("role")]
    [InlineData("replay")]
    public async Task InvalidTransportOrDelegationCannotReachOwner(string defect)
    {
        var request = await RequestAsync();
        var body = Body(request, "resolve");
        var caller = Caller(request, "resolve");
        var owner = new Mock<IConversationInferenceOwner>(MockBehavior.Strict);
        owner
            .Setup(value =>
                value.ResolveAsync(
                    caller,
                    It.Is<ConversationInferenceRequest>(value => Matches(value, request)),
                    It.IsAny<CancellationToken>()
                )
            )
            .ReturnsAsync(body);
        var controller = Controller(owner.Object);
        Sign(
            controller.HttpContext,
            defect == "digest" ? JsonSerializer.SerializeToElement(new { changed = true }) : body,
            defect == "role" ? caller with { Role = "OWNER" } : caller,
            "resolve",
            defect == "purpose" ? "CONVERSATION_CONTENT_RECOVERY" : null
        );
        if (defect == "certificate")
            controller.HttpContext.Connection.ClientCertificate = null;
        if (defect == "header")
            controller.Request.Headers.Authorization = "Bearer malformed";
        if (defect == "replay")
            Assert.IsType<OkObjectResult>(await controller.Resolve(body, CancellationToken.None));
        var result = Assert.IsType<ObjectResult>(
            await controller.Resolve(body, CancellationToken.None)
        );
        Assert.Equal(403, result.StatusCode);
        Assert.Equal(
            "{\"code\":\"INFERENCE_AUTHORITY_DENIED\"}",
            JsonSerializer.Serialize(result.Value, Json)
        );
        Assert.Equal(defect == "replay" ? 1 : 0, owner.Invocations.Count);
    }

    private ConversationInferenceController Controller(IConversationInferenceOwner owner)
    {
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(
                new Dictionary<string, string?>
                {
                    ["WAOOAW_WORKLOAD_CREDENTIALS"] = fixture.CredentialsPath,
                }
            )
            .Build();
        return new(
            new InferenceWorkloadAuthority(
                new InferenceWorkloadValidator(configuration, TimeProvider.System)
            ),
            owner,
            NullLogger<ConversationInferenceController>.Instance
        )
        {
            ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() },
        };
    }

    private static async Task<ConversationInferenceRequest> RequestAsync()
    {
        var source = await OperationalMandateResolverTests.CreateFixtureAsync();
        var mandate = await new OperationalMandateResolver(source.Factory).ResolveAsync(
            source.TenantId,
            source.ParticipantId,
            source.RelationshipId,
            Guid.NewGuid(),
            Guid.NewGuid(),
            "CUSTOMER_PROFILING",
            "Prepare the profile",
            CancellationToken.None
        );
        return new(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            source.RelationshipId,
            new string('a', 64),
            new string('b', 64),
            "en",
            mandate,
            Guid.NewGuid(),
            null,
            1,
            1
        );
    }

    private static InferenceCaller Caller(ConversationInferenceRequest request, string operation) =>
        new(
            request.OperationalMandate.TenantId,
            request.RelationshipRef,
            request.OperationalMandate.ActorId,
            operation == "read-content" ? "OWNER" : "EMPLOYER",
            request.ContributionRef,
            request.ExecutionId,
            Guid.NewGuid()
        );

    private static bool Matches(
        ConversationInferenceRequest actual,
        ConversationInferenceRequest expected
    ) => JsonSerializer.Serialize(actual, Json) == JsonSerializer.Serialize(expected, Json);

    private static JsonElement Body(ConversationInferenceRequest request, string operation) =>
        operation == "read-content"
            ? JsonSerializer.SerializeToElement(
                new ConversationInferenceContentReadRequest(
                    request,
                    new(
                        "1.0",
                        request.ContributionRef,
                        new string('a', 64),
                        4,
                        request.ExecutionId,
                        DateTimeOffset.UtcNow.AddMinutes(1),
                        7
                    )
                ),
                Json
            )
            : JsonSerializer.SerializeToElement(request, Json);

    private void Sign(
        HttpContext http,
        JsonElement body,
        InferenceCaller caller,
        string operation,
        string? purpose = null
    )
    {
        using var manifest = JsonDocument.Parse(
            File.ReadAllText(Path.Combine(fixture.CredentialsPath, "manifest.json"))
        );
        var source = manifest.RootElement.GetProperty("workloads").GetProperty("ai-runtime");
        var target = manifest.RootElement.GetProperty("workloads").GetProperty("business-platform");
        var path = "/internal/v1/conversation-inference/" + operation;
        var name = operation switch
        {
            "read-content" => "readConversationInferenceContent",
            _ => operation + "ConversationInference",
        };
        var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        var envelope = new Dictionary<string, object>
        {
            ["issuer_uri"] = source.GetProperty("identity_uri").GetString()!,
            ["key_id"] = source.GetProperty("delegation_key_id").GetString()!,
            ["target_audience"] = target.GetProperty("audience").GetString()!,
            ["method"] = "POST",
            ["route"] = path,
            ["operation"] = name,
            ["schema_version"] = "1.0",
            ["contract_major"] = 1,
            ["purpose"] =
                purpose
                ?? (
                    operation == "read-content"
                        ? "CONVERSATION_CONTENT_RECOVERY"
                        : "CONVERSATION_INFERENCE_OWNER"
                ),
            ["actor_source"] = "BP_SESSION",
            ["request_digest"] = Convert.ToHexStringLower(
                SHA256.HashData(
                    Encoding.UTF8.GetBytes(AgentAdmissionCanonicalizer.Canonicalize(body))
                )
            ),
            ["issued_at"] = now,
            ["not_before"] = now,
            ["expires_at"] = now + 60,
            ["tenant_id"] = caller.TenantId.ToString("D"),
            ["relationship_id"] = caller.RelationshipId.ToString("D"),
            ["actor_subject"] = caller.ActorId.ToString("D"),
            ["effective_role"] = caller.Role,
            ["subject_reference"] = caller.ContributionId.ToString("D"),
            ["command_id"] = caller.ExecutionId.ToString("D"),
            ["idempotency_key"] = caller.IdempotencyKey.ToString("D"),
            ["expected_versions"] = new Dictionary<string, string>(),
            ["envelope_id"] = Guid.NewGuid().ToString("D"),
        };
        using var signing = ECDsa.Create();
        signing.ImportFromPem(
            File.ReadAllText(
                Path.Combine(
                    fixture.CredentialsPath,
                    "workloads",
                    "ai-runtime",
                    "delegation-key.pem"
                )
            )
        );
        var payload = JsonSerializer.SerializeToUtf8Bytes(envelope);
        static string Encode(byte[] value) =>
            Convert.ToBase64String(value).TrimEnd('=').Replace('+', '-').Replace('/', '_');
        http.Request.Method = "POST";
        http.Request.Path = path;
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

    private static Task<IActionResult> InvokeAsync(
        ConversationInferenceController controller,
        string operation,
        JsonElement body
    ) =>
        operation switch
        {
            "resolve" => controller.Resolve(body, CancellationToken.None),
            "reserve" => controller.Reserve(body, CancellationToken.None),
            "reconcile" => controller.Reconcile(body, CancellationToken.None),
            "settle" => controller.Settle(body, CancellationToken.None),
            "release" => controller.Release(body, CancellationToken.None),
            "read-content" => controller.ReadContent(body, CancellationToken.None),
            _ => throw new ArgumentOutOfRangeException(nameof(operation)),
        };

    public void Dispose() => _peer.Dispose();
}
