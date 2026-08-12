// Implements: work-contracts/WC-062-wc034-f6-voice-interaction.md WC062-01, WC062-05
// constitutional_basis: C-001, C-005, C-023, C-026, C-042, C-049, C-059, C-063, C-076

using System.Security.Claims;
using System.Text;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Voice;

public sealed class VoiceContributionsControllerTests
{
    [Fact]
    public async Task AllPublicOperationsPreserveStatusAndAuthorityContracts()
    {
        var context = await CreateAsync();
        var createKey = Guid.NewGuid();
        var createRequest = new CreateVoiceContributionSessionRequestV1("1.0.0", "en-IN");
        var created = Assert.IsType<ObjectResult>(await context.Controller.CreateAsync(
            context.RelationshipId, createKey, createRequest, CancellationToken.None));
        Assert.Equal(StatusCodes.Status201Created, created.StatusCode);
        var session = Assert.IsType<VoiceContributionSessionV1>(created.Value);
        Assert.IsType<OkObjectResult>(await context.Controller.CreateAsync(
            context.RelationshipId, createKey, createRequest, CancellationToken.None));
        Assert.IsType<OkObjectResult>(await context.Controller.GetAsync(
            context.RelationshipId, session.SessionId, CancellationToken.None));

        var uploadKey = Guid.NewGuid();
        var audio = FormFile("audio/webm");
        var uploaded = Assert.IsAssignableFrom<ObjectResult>(await context.Controller.UploadAsync(
            context.RelationshipId, session.SessionId, uploadKey, audio, CancellationToken.None));
        Assert.Equal(StatusCodes.Status202Accepted, uploaded.StatusCode);
        Assert.IsType<OkObjectResult>(await context.Controller.UploadAsync(
            context.RelationshipId, session.SessionId, uploadKey, FormFile("audio/webm"), CancellationToken.None));
        Assert.IsType<OkObjectResult>(await context.Controller.GetTranscriptAsync(
            context.RelationshipId, session.SessionId, CancellationToken.None));
        Assert.IsType<OkObjectResult>(await context.Controller.CorrectAsync(
            context.RelationshipId, session.SessionId, Guid.NewGuid(),
            new VoiceCorrectionRequestV1("1.0.0", 1, "corrected"), CancellationToken.None));
        var sent = Assert.IsType<OkObjectResult>(await context.Controller.SendAsync(
            context.RelationshipId, session.SessionId, Guid.NewGuid(),
            new SendVoiceContributionRequestV1("1.0.0", 2, true), CancellationToken.None));
        var contributionId = Assert.IsType<VoiceContributionOutcomeV1>(sent.Value).ContributionId!.Value;
        var erased = Assert.IsAssignableFrom<ObjectResult>(await context.Controller.EraseAsync(
            context.RelationshipId, contributionId, Guid.NewGuid(),
            new VoicePayloadErasureRequestV1("1.0.0", "AUDIO_AND_TRANSCRIPT"), CancellationToken.None));
        Assert.Equal(StatusCodes.Status202Accepted, erased.StatusCode);

        var cancellable = Assert.IsType<VoiceContributionSessionV1>((await context.Controller.CreateAsync(
            context.RelationshipId, Guid.NewGuid(), createRequest, CancellationToken.None) as ObjectResult)!.Value);
        Assert.IsType<OkObjectResult>(await context.Controller.CancelAsync(
            context.RelationshipId, cancellable.SessionId, Guid.NewGuid(),
            new CancelVoiceContributionRequestV1("1.0.0"), CancellationToken.None));
    }

    [Fact]
    public async Task MissingTenantOrParticipantAuthorityIsForbidden()
    {
        var context = await CreateAsync();
        context.Controller.HttpContext.Items.Clear();
        Assert.IsType<ForbidResult>(await context.Controller.GetAsync(
            context.RelationshipId, Guid.NewGuid(), CancellationToken.None));

        context.Controller.HttpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = context.TenantId.ToString();
        context.Controller.HttpContext.User = new ClaimsPrincipal();
        Assert.IsType<ForbidResult>(await context.Controller.GetAsync(
            context.RelationshipId, Guid.NewGuid(), CancellationToken.None));
    }

    [Fact]
    public async Task ServiceFailuresMapToPrivacySafeProblems()
    {
        var context = await CreateAsync();
        await AssertProblemAsync(400, "invalid_request", context.Controller.CreateAsync(
            context.RelationshipId, Guid.NewGuid(),
            new CreateVoiceContributionSessionRequestV1("2.0.0", "en-IN"), CancellationToken.None));
        await AssertProblemAsync(404, "not_authorized", context.Controller.GetAsync(
            context.RelationshipId, Guid.NewGuid(), CancellationToken.None));

        var created = Assert.IsType<VoiceContributionSessionV1>((await context.Controller.CreateAsync(
            context.RelationshipId, Guid.NewGuid(),
            new CreateVoiceContributionSessionRequestV1("1.0.0", "en-IN"), CancellationToken.None) as ObjectResult)!.Value);
        await AssertProblemAsync(409, "conflict", context.Controller.SendAsync(
            context.RelationshipId, created.SessionId, Guid.NewGuid(),
            new SendVoiceContributionRequestV1("1.0.0", 1, true), CancellationToken.None));
    }

    private static async Task AssertProblemAsync(int status, string title, Task<IActionResult> action)
    {
        var result = Assert.IsType<ObjectResult>(await action);
        Assert.Equal(status, result.StatusCode);
        Assert.Equal(title, Assert.IsType<ProblemDetails>(result.Value).Title);
    }

    private static FormFile FormFile(string contentType)
    {
        var stream = new MemoryStream(Encoding.UTF8.GetBytes("bounded-audio"));
        return new FormFile(stream, 0, stream.Length, "audio", "voice.webm")
        {
            Headers = new HeaderDictionary(),
            ContentType = contentType,
        };
    }

    private static async Task<ControllerContext> CreateAsync()
    {
        var voiceFactory = new InMemoryVoiceFactory(Guid.NewGuid().ToString("N"));
        var relationshipFactory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        await using (var db = relationshipFactory.CreateDbContext())
        {
            db.EmploymentRelationships.Add(new EmploymentRelationship
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ProfessionalType = "DMA",
                EvaluationIntentId = Guid.NewGuid(),
                InitiatingParticipantId = participantId,
                State = EmploymentRelationshipState.Active,
            });
            db.RelationshipParticipants.Add(new RelationshipParticipant
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ParticipantId = participantId,
                Role = RelationshipParticipantRole.Employer,
                BoundEvidenceId = Guid.NewGuid(),
            });
            await db.SaveChangesAsync();
        }
        var service = new VoiceContributionService(
            voiceFactory, relationshipFactory, new RecordingRelationshipConstitutionalGateway(),
            new VoiceMediaGatewayStub(), new VoiceTranscriptionGatewayStub(), new TestVoiceContentProtector());
        var controller = new VoiceContributionsController(service)
        {
            ControllerContext = new Microsoft.AspNetCore.Mvc.ControllerContext { HttpContext = new DefaultHttpContext() },
        };
        controller.HttpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId.ToString();
        controller.HttpContext.User = new ClaimsPrincipal(new ClaimsIdentity(
            [new Claim("participant_id", participantId.ToString())], "test"));
        return new(controller, tenantId, participantId, relationshipId);
    }

    private sealed record ControllerContext(
        VoiceContributionsController Controller, Guid TenantId, Guid ParticipantId, Guid RelationshipId);
}