using System.Security.Claims;
using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Tests.Conversation;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class ChannelNeutralConversationControllerTests
{
    [Fact]
    public async Task CanonicalContextProfileContributionAndDataRightsUseSharedOwners()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        await context.SeedConversationAsync(("WEB", "start"));
        var controller = CreateController(context);

        var canonical = Assert.IsType<OkObjectResult>(
            await controller.GetCanonicalConversationAsync(
                context.RelationshipId,
                cancellationToken: CancellationToken.None
            )
        );
        var contexts = Assert.IsType<OkObjectResult>(
            await controller.ListContextsAsync(context.RelationshipId, CancellationToken.None)
        );
        var profile = Assert.IsType<OkObjectResult>(
            await controller.GetProfileAsync(context.RelationshipId, CancellationToken.None)
        );
        Assert.Contains("CurrentSequence", JsonSerializer.Serialize(canonical.Value));
        Assert.Contains("ContextKey", JsonSerializer.Serialize(contexts.Value));
        Assert.Contains("ProfileVersion", JsonSerializer.Serialize(profile.Value));

        var contribution = new ConversationContributionRequestV1(
            "1.0",
            "TEXT",
            "continue",
            null,
            new RegisteredContextHintV1("INDUCTION", null),
            "workspace-1",
            null,
            new string('d', 64)
        );
        Assert.IsType<AcceptedResult>(
            await controller.SubmitContributionAsync(
                context.RelationshipId,
                contribution,
                CancellationToken.None
            )
        );
        Assert.IsType<OkObjectResult>(
            await controller.SubmitContributionAsync(
                context.RelationshipId,
                contribution,
                CancellationToken.None
            )
        );
        controller.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString("D");
        Assert.IsType<ConflictObjectResult>(
            await controller.SubmitContributionAsync(
                context.RelationshipId,
                contribution with
                {
                    ContextVersion = "stale",
                },
                CancellationToken.None
            )
        );

        Guid executionId;
        Guid messageId;
        Guid observationId;
        long profileVersion;
        await using (var db = context.Conversations.CreateDbContext())
        {
            var message = db.Messages.OrderByDescending(value => value.Sequence).First();
            messageId = message.MessageId;
            var execution = new ConversationExecution
            {
                TenantId = context.TenantId,
                ConversationId = message.ConversationId,
                RelationshipId = context.RelationshipId,
                MessageId = messageId,
            };
            db.Executions.Add(execution);
            var observation = new ConversationContextObservation
            {
                Environment = context.Options.Environment,
                TenantId = context.TenantId,
                RelationshipId = context.RelationshipId,
                Owner = "CUSTOMER",
                SubjectType = "RELATIONSHIP",
                ObservationType = "PREFERENCE",
                SourceType = "CUSTOMER",
                SourceVersion = "profile:1",
                ValueJson = JsonSerializer.Serialize("original"),
                SourceReference = "test",
                SourceDigest = new string('a', 64),
                Revision = 1,
            };
            db.ContextObservations.Add(observation);
            await db.SaveChangesAsync();
            executionId = execution.ExecutionId;
            observationId = observation.ObservationId;
            profileVersion = db.ContextObservations.Max(value => value.Revision);
        }
        var operation = Assert.IsType<OkObjectResult>(
            await controller.GetOperationAsync(
                context.RelationshipId,
                executionId,
                CancellationToken.None
            )
        );
        var states = Assert.IsType<OkObjectResult>(
            await controller.GetMessageStatesAsync(
                context.RelationshipId,
                messageId,
                CancellationToken.None
            )
        );
        Assert.Contains("operationType", JsonSerializer.Serialize(operation.Value));
        Assert.Contains("Delivery", JsonSerializer.Serialize(states.Value));

        var correction = new ContextCorrectionRequestV1(
            observationId,
            "CORRECT",
            JsonSerializer.SerializeToElement("corrected"),
            "customer correction",
            profileVersion,
            new string('e', 64)
        );
        var correctionResult = Assert.IsType<AcceptedResult>(
            await controller.CorrectProfileAsync(
                context.RelationshipId,
                correction,
                CancellationToken.None
            )
        );
        Assert.Contains("ObservationId", JsonSerializer.Serialize(correctionResult.Value));

        controller.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString("D");
        var dataRight = Assert.IsType<AcceptedResult>(
            await controller.RequestDataRightAsync(
                context.RelationshipId,
                new RequestConversationDataRightV1(
                    "EXPORT",
                    "CONVERSATION",
                    "auth-ref",
                    "customer request",
                    new string('f', 64)
                ),
                CancellationToken.None
            )
        );
        Assert.Contains("OperationId", JsonSerializer.Serialize(dataRight.Value));
        controller.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString("D");
        Assert.IsAssignableFrom<ObjectResult>(
            await controller.RequestDataRightAsync(
                context.RelationshipId,
                new RequestConversationDataRightV1("INVALID", "INVALID", "", null, "bad"),
                CancellationToken.None
            )
        );

        var inaccessibleRelationship = Guid.NewGuid();
        Assert.IsAssignableFrom<ObjectResult>(
            await controller.GetCanonicalConversationAsync(inaccessibleRelationship)
        );
        Assert.IsAssignableFrom<ObjectResult>(
            await controller.ListContextsAsync(inaccessibleRelationship, CancellationToken.None)
        );
        Assert.IsAssignableFrom<ObjectResult>(
            await controller.GetProfileAsync(inaccessibleRelationship, CancellationToken.None)
        );
        Assert.IsAssignableFrom<ObjectResult>(
            await controller.GetMessageStatesAsync(
                context.RelationshipId,
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
        Assert.IsAssignableFrom<ObjectResult>(
            await controller.CorrectProfileAsync(
                context.RelationshipId,
                correction with
                {
                    CorrectionType = "INVALID",
                },
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task BoundaryRejectsMissingAuthorityDisabledFeatureAndInvalidRequests()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var unauthorized = CreateController(context, authorized: false);
        var invalidContribution = InvalidContribution();

        var unauthorizedResults = new IActionResult[]
        {
            await unauthorized.GetCanonicalConversationAsync(context.RelationshipId),
            await unauthorized.GetOperationAsync(
                context.RelationshipId,
                Guid.NewGuid(),
                CancellationToken.None
            ),
            await unauthorized.RequestCancellationAsync(
                context.RelationshipId,
                InvalidCancellation(),
                CancellationToken.None
            ),
            await unauthorized.SubmitCommandAsync(
                context.RelationshipId,
                JsonSerializer.SerializeToElement(new { kind = "UNKNOWN" }),
                CancellationToken.None
            ),
            await unauthorized.SubmitContributionAsync(
                context.RelationshipId,
                invalidContribution,
                CancellationToken.None
            ),
            await unauthorized.ListContextsAsync(context.RelationshipId, CancellationToken.None),
            await unauthorized.GetProfileAsync(context.RelationshipId, CancellationToken.None),
            await unauthorized.CorrectProfileAsync(
                context.RelationshipId,
                new ContextCorrectionRequestV1(Guid.NewGuid(), "INVALID", null, null, 0, "bad"),
                CancellationToken.None
            ),
            await unauthorized.PrepareHandoffAsync(
                context.RelationshipId,
                InvalidPrepare(),
                CancellationToken.None
            ),
            await unauthorized.ActivateHandoffAsync(
                context.RelationshipId,
                Guid.NewGuid(),
                InvalidActivate(),
                CancellationToken.None
            ),
            await unauthorized.RevertHandoffAsync(
                context.RelationshipId,
                Guid.NewGuid(),
                InvalidRevert(),
                CancellationToken.None
            ),
            await unauthorized.GetMessageStatesAsync(
                context.RelationshipId,
                Guid.NewGuid(),
                CancellationToken.None
            ),
            await unauthorized.RequestDataRightAsync(
                context.RelationshipId,
                new RequestConversationDataRightV1("INVALID", "INVALID", "", null, "bad"),
                CancellationToken.None
            ),
        };
        Assert.All(unauthorizedResults, result => Assert.IsAssignableFrom<ObjectResult>(result));
        Assert.All(
            unauthorizedResults.Cast<ObjectResult>(),
            result => Assert.Contains("Code", JsonSerializer.Serialize(result.Value))
        );

        context.Options.Enabled = false;
        var disabled = CreateController(context);
        Assert.IsAssignableFrom<ObjectResult>(
            await disabled.GetCanonicalConversationAsync(context.RelationshipId)
        );
        Assert.IsAssignableFrom<ObjectResult>(
            await disabled.GetOperationAsync(
                context.RelationshipId,
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
        Assert.IsAssignableFrom<ObjectResult>(
            await disabled.SubmitContributionAsync(
                context.RelationshipId,
                invalidContribution,
                CancellationToken.None
            )
        );
        Assert.IsAssignableFrom<ObjectResult>(
            await disabled.ListContextsAsync(context.RelationshipId, CancellationToken.None)
        );
        Assert.IsAssignableFrom<ObjectResult>(
            await disabled.GetProfileAsync(context.RelationshipId, CancellationToken.None)
        );

        context.Options.Enabled = true;
        var invalid = CreateController(context);
        Assert.IsType<BadRequestObjectResult>(
            await invalid.RequestCancellationAsync(
                context.RelationshipId,
                InvalidCancellation(),
                CancellationToken.None
            )
        );
        Assert.IsAssignableFrom<ObjectResult>(
            await invalid.SubmitCommandAsync(
                context.RelationshipId,
                JsonSerializer.SerializeToElement(new { kind = "UNKNOWN" }),
                CancellationToken.None
            )
        );
        Assert.IsType<BadRequestObjectResult>(
            await invalid.SubmitContributionAsync(
                context.RelationshipId,
                invalidContribution,
                CancellationToken.None
            )
        );
        Assert.IsType<BadRequestObjectResult>(
            await invalid.PrepareHandoffAsync(
                context.RelationshipId,
                InvalidPrepare(),
                CancellationToken.None
            )
        );
        Assert.IsAssignableFrom<ObjectResult>(
            await invalid.ActivateHandoffAsync(
                context.RelationshipId,
                Guid.NewGuid(),
                InvalidActivate(),
                CancellationToken.None
            )
        );
        Assert.IsType<BadRequestObjectResult>(
            await invalid.RevertHandoffAsync(
                context.RelationshipId,
                Guid.NewGuid(),
                InvalidRevert(),
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task CancellationAndCommandExposeAcceptedReplayAndOperationStates()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        await context.SeedConversationAsync(("WEB", "start"));
        Guid executionId;
        await using (var db = context.Conversations.CreateDbContext())
        {
            var message = db.Messages.Single();
            var execution = new ConversationExecution
            {
                TenantId = context.TenantId,
                ConversationId = message.ConversationId,
                RelationshipId = context.RelationshipId,
                MessageId = message.MessageId,
            };
            db.Executions.Add(execution);
            await db.SaveChangesAsync();
            executionId = execution.ExecutionId;
        }
        var controller = CreateController(context, coordinator: new CoordinatorStub());
        var cancellation = new CancellationRequestV1(
            executionId,
            "CUSTOMER_REQUEST",
            "workspace-1",
            new string('a', 64)
        );
        Assert.IsType<AcceptedResult>(
            await controller.RequestCancellationAsync(
                context.RelationshipId,
                cancellation,
                CancellationToken.None
            )
        );
        Assert.IsType<OkObjectResult>(
            await controller.RequestCancellationAsync(
                context.RelationshipId,
                cancellation,
                CancellationToken.None
            )
        );
        Assert.IsType<NotFoundObjectResult>(
            await controller.GetOperationAsync(
                context.RelationshipId,
                Guid.NewGuid(),
                CancellationToken.None
            )
        );

        controller.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString("D");
        var command = JsonSerializer.Deserialize<JsonElement>(
            """
            {
              "schemaVersion": "1.0",
              "kind": "CONFIRM_INDUCTION_ITEM",
              "subjectRef": "requirement-1",
              "expectedWorkspaceVersion": "workspace-1",
              "expectedManifestVersion": "manifest-1"
            }
            """
        );
        var commandAccepted = Assert.IsType<AcceptedResult>(
            await controller.SubmitCommandAsync(
                context.RelationshipId,
                command,
                CancellationToken.None
            )
        );
        Assert.IsType<OkObjectResult>(
            await controller.SubmitCommandAsync(
                context.RelationshipId,
                command,
                CancellationToken.None
            )
        );
        var commandId = Assert.IsType<Guid>(
            commandAccepted
                .Value!.GetType()
                .GetProperty("operationId")!
                .GetValue(commandAccepted.Value)
        );
        Assert.IsType<OkObjectResult>(
            await controller.GetOperationAsync(
                context.RelationshipId,
                commandId,
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task HandoffPrepareActivateAndMissingRevertPreserveContinuityBoundary()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        await context.SeedConversationAsync(("WEB", "start"));
        var sourceConversationId = Guid.NewGuid().ToString("D");
        await using (var db = context.Relationships.CreateDbContext())
        {
            db.ChannelBindings.Add(
                new ChannelBinding
                {
                    TenantId = context.TenantId,
                    RelationshipId = context.RelationshipId,
                    ParticipantId = context.ParticipantId,
                    ParticipantRole = "EMPLOYER",
                    Channel = "WEB",
                    ExternalSubjectHash = new string('a', 64),
                    ConversationId = sourceConversationId,
                    AssuranceLevel = "AAL3_FRESH",
                    Status = "ACTIVE",
                }
            );
            await db.SaveChangesAsync();
        }
        var continuity = new ChannelContinuityService(
            context.Relationships,
            new ConversationConstitutionalGatewayStub(),
            Options.Create(
                new ChannelContinuityOptions
                {
                    EnvelopeHmacKey = Convert.ToBase64String(RandomNumberGenerator.GetBytes(32)),
                }
            )
        );
        var source = CreateController(
            context,
            continuity: continuity,
            conversationId: sourceConversationId
        );
        var prepare = Assert.IsType<ObjectResult>(
            await source.PrepareHandoffAsync(
                context.RelationshipId,
                new HandoffPrepareRequestV1(
                    "WEB",
                    "WHATSAPP",
                    1,
                    "workspace-1",
                    new string('b', 64)
                ),
                CancellationToken.None
            )
        );
        Assert.Equal(201, prepare.StatusCode);
        var receipt = Assert.IsType<HandoffReceiptV1>(prepare.Value);
        Assert.Contains("ExpiresAt", JsonSerializer.Serialize(receipt));
        string checkpointDigest;
        await using (var db = context.Relationships.CreateDbContext())
        {
            checkpointDigest = db
                .ContinuityCheckpoints.Single(value => value.CheckpointId == receipt.HandoffId)
                .ContinuityEnvelopeHash;
        }

        var target = CreateController(
            context,
            continuity: continuity,
            channel: "WHATSAPP",
            conversationId: Guid.NewGuid().ToString("D")
        );
        Assert.IsType<OkObjectResult>(
            await target.ActivateHandoffAsync(
                context.RelationshipId,
                receipt.HandoffId,
                new HandoffActivateRequestV1("auth-ref", checkpointDigest, new string('c', 64)),
                CancellationToken.None
            )
        );
        target.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString("D");
        target.Request.Headers["X-Correlation-ID"] = Guid.NewGuid().ToString("D");
        Assert.IsType<NotFoundObjectResult>(
            await target.RevertHandoffAsync(
                context.RelationshipId,
                Guid.NewGuid(),
                new HandoffRevertRequestV1(
                    "WEB",
                    new string('d', 64),
                    "UNKNOWN",
                    "OUTCOME_UNKNOWN",
                    new string('e', 64)
                ),
                CancellationToken.None
            )
        );
    }

    private static ChannelNeutralConversationController CreateController(
        Wc120FitnessContext context,
        bool authorized = true,
        IEmploymentCommandCoordinator? coordinator = null,
        ChannelContinuityService? continuity = null,
        string channel = "WEB",
        string? conversationId = null
    )
    {
        var conversation = new ConversationService(
            context.Conversations,
            context.Relationships,
            new ConversationConstitutionalGatewayStub(),
            new ConversationExecutionGatewayStub(),
            new OperationalMandateResolverStub(),
            new ConversationCursorCodec(
                Options.Create(
                    new ConversationCursorOptions
                    {
                        HmacKey = "wc120-controller-test-key-at-least-32-characters",
                    }
                )
            ),
            context.StopFence,
            context.Profiles,
            Options.Create(context.Options)
        );
        var controller = new ChannelNeutralConversationController(
            conversation,
            context.Profiles,
            null!,
            context.Employment,
            coordinator!,
            context.StopFence,
            continuity!,
            Options.Create(context.Options),
            context.Relationships
        );
        var httpContext = new DefaultHttpContext();
        if (authorized)
        {
            httpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] =
                context.TenantId.ToString("D");
            httpContext.User = new ClaimsPrincipal(
                new ClaimsIdentity(
                    new[]
                    {
                        new Claim("participant_id", context.ParticipantId.ToString("D")),
                        new Claim("authentication_assurance", "AAL3_FRESH"),
                        new Claim(
                            "auth_time",
                            DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString()
                        ),
                        new Claim("authentication_reference", "auth-ref"),
                        new Claim("channel", channel),
                        new Claim(
                            "conversation_id",
                            conversationId ?? Guid.NewGuid().ToString("D")
                        ),
                        new Claim("external_subject_hash", new string('a', 64)),
                    },
                    "test"
                )
            );
        }
        httpContext.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString("D");
        httpContext.Request.Headers["X-Correlation-ID"] = Guid.NewGuid().ToString("D");
        controller.ControllerContext = new ControllerContext { HttpContext = httpContext };
        return controller;
    }

    private static CancellationRequestV1 InvalidCancellation() =>
        new(Guid.NewGuid(), "", "", "bad");

    private static ConversationContributionRequestV1 InvalidContribution() =>
        new("0", "UNKNOWN", null, null, null, "", null, "bad");

    private static HandoffPrepareRequestV1 InvalidPrepare() => new("WEB", "WEB", -1, "", "bad");

    private static HandoffActivateRequestV1 InvalidActivate() => new("", "bad", "bad");

    private static HandoffRevertRequestV1 InvalidRevert() =>
        new("INVALID", "bad", "INVALID", "INVALID", "bad");

    private sealed class CoordinatorStub : IEmploymentCommandCoordinator
    {
        public Task CoordinateAsync(
            EmploymentCommandCoordinationContext context,
            CancellationToken cancellationToken
        ) => Task.CompletedTask;
    }
}
