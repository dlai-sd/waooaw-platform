// Implements: WC-121 Components 01 and 08 controller, authorization, and privacy evidence
// constitutional_basis: C-001, C-005, C-007, C-023, C-026, C-059, C-063

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class CustomerEngagementWorkspaceControllerTests
{
    [Theory]
    [InlineData(EmploymentRelationshipState.Discovered, "TRIAL_OR_HIRE")]
    [InlineData(EmploymentRelationshipState.Interviewing, "TRIAL_OR_HIRE")]
    [InlineData(EmploymentRelationshipState.TrialActive, "TRIAL_OR_HIRE")]
    [InlineData(EmploymentRelationshipState.Configuring, "INDUCTION")]
    [InlineData(EmploymentRelationshipState.ContractPendingAcceptance, "INDUCTION")]
    [InlineData(EmploymentRelationshipState.ContractAcceptedPendingPayment, "INDUCTION")]
    [InlineData(EmploymentRelationshipState.ActivationPending, "INDUCTION")]
    [InlineData(EmploymentRelationshipState.Paused, "PAUSED_RENEWAL_OR_EXIT")]
    [InlineData(EmploymentRelationshipState.StoppedEmergency, "PAUSED_RENEWAL_OR_EXIT")]
    [InlineData(EmploymentRelationshipState.Terminated, "PAUSED_RENEWAL_OR_EXIT")]
    public async Task ProgressMapsEveryLifecycleFamilyWithoutInferringOutcome(
        EmploymentRelationshipState state,
        string expectedStage
    )
    {
        var fixture = await CreateAsync(state: state);

        var result = Assert.IsType<OkObjectResult>(
            await fixture.Controller.GetProgressAsync(
                fixture.RelationshipId,
                CancellationToken.None
            )
        );
        var progress = Assert.IsType<CustomerEngagementProgress>(result.Value);

        Assert.Equal(expectedStage, progress.LifecycleStage);
        Assert.Equal("UNKNOWN", Assert.Single(progress.Items).Truth.Outcome);
    }

    [Fact]
    public async Task PreferencesAndProgressUseParticipantAuthorityAndVersionConflicts()
    {
        var fixture = await CreateAsync();

        var initial = Assert.IsType<OkObjectResult>(
            await fixture.Controller.GetPreferencesAsync(
                fixture.RelationshipId,
                CancellationToken.None
            )
        );
        Assert.Equal(
            0,
            Assert.IsType<RelationshipWorkspacePreferenceState>(initial.Value).PreferenceVersion
        );

        var invalid = Assert.IsType<ObjectResult>(
            await fixture.Controller.ReplacePreferencesAsync(
                fixture.RelationshipId,
                new(-1, "UNSUPPORTED", true),
                CancellationToken.None
            )
        );
        Assert.Equal(StatusCodes.Status400BadRequest, invalid.StatusCode);

        var updated = Assert.IsType<OkObjectResult>(
            await fixture.Controller.ReplacePreferencesAsync(
                fixture.RelationshipId,
                new(0, "OPERATIONS", false),
                CancellationToken.None
            )
        );
        Assert.Equal(
            1,
            Assert.IsType<RelationshipWorkspacePreferenceState>(updated.Value).PreferenceVersion
        );

        var conflict = Assert.IsType<ObjectResult>(
            await fixture.Controller.ReplacePreferencesAsync(
                fixture.RelationshipId,
                new(0, "RIGHTS", true),
                CancellationToken.None
            )
        );
        Assert.Equal(StatusCodes.Status409Conflict, conflict.StatusCode);

        var progress = Assert.IsType<OkObjectResult>(
            await fixture.Controller.GetProgressAsync(
                fixture.RelationshipId,
                CancellationToken.None
            )
        );
        var body = Assert.IsType<CustomerEngagementProgress>(progress.Value);
        Assert.Equal(fixture.RelationshipId, body.RelationshipId);
        Assert.Equal("no-store", fixture.Controller.Response.Headers.CacheControl);
        Assert.Equal($"\"{body.ProjectionVersion}\"", fixture.Controller.Response.Headers.ETag);
    }

    [Fact]
    public async Task InaccessibleRelationshipUsesTheSamePrivacySafeProblem()
    {
        var fixture = await CreateAsync();
        var inaccessibleId = Guid.NewGuid();

        var preferences = Assert.IsType<ObjectResult>(
            await fixture.Controller.GetPreferencesAsync(inaccessibleId, CancellationToken.None)
        );
        var replace = Assert.IsType<ObjectResult>(
            await fixture.Controller.ReplacePreferencesAsync(
                inaccessibleId,
                new(0, "LIFECYCLE", true),
                CancellationToken.None
            )
        );
        var progress = Assert.IsType<ObjectResult>(
            await fixture.Controller.GetProgressAsync(inaccessibleId, CancellationToken.None)
        );
        var focus = Assert.IsType<ObjectResult>(
            await fixture.Controller.ResolveFocusAsync(
                inaccessibleId,
                new("not-a-valid-focus-token"),
                CancellationToken.None
            )
        );

        Assert.All(
            new[] { preferences, replace, progress, focus },
            result => Assert.Equal(StatusCodes.Status404NotFound, result.StatusCode)
        );
    }

    [Fact]
    public async Task FocusResolutionRejectsInvalidTamperedAndChangedAuthority()
    {
        var fixture = await CreateAsync();

        var invalid = Assert.IsType<ObjectResult>(
            await fixture.Controller.ResolveFocusAsync(
                fixture.RelationshipId,
                new(" "),
                CancellationToken.None
            )
        );
        Assert.Equal(StatusCodes.Status400BadRequest, invalid.StatusCode);

        var progressResult = Assert.IsType<OkObjectResult>(
            await fixture.Controller.GetProgressAsync(
                fixture.RelationshipId,
                CancellationToken.None
            )
        );
        var progress = Assert.IsType<CustomerEngagementProgress>(progressResult.Value);
        var focus = Assert.Single(progress.AvailableFocuses);
        var resolved = Assert.IsType<OkObjectResult>(
            await fixture.Controller.ResolveFocusAsync(
                fixture.RelationshipId,
                new(focus.FocusToken),
                CancellationToken.None
            )
        );
        Assert.Equal(
            fixture.RelationshipId,
            Assert.IsType<WorkspaceFocusResolution>(resolved.Value).RelationshipId
        );

        var tampered = Assert.IsType<ObjectResult>(
            await fixture.Controller.ResolveFocusAsync(
                fixture.RelationshipId,
                new($"{focus.FocusToken}tampered"),
                CancellationToken.None
            )
        );
        Assert.Equal(StatusCodes.Status404NotFound, tampered.StatusCode);

        var expiredToken = fixture
            .DataProtectionProvider.CreateProtector("WAOOAW.CustomerEngagementWorkspace.Focus.v1")
            .Protect(
                JsonSerializer.Serialize(
                    new
                    {
                        TokenId = Guid.NewGuid(),
                        fixture.TenantId,
                        fixture.ParticipantId,
                        fixture.RelationshipId,
                        AuthorityVersion = 3,
                        Destination = "OPERATION",
                        SubjectRef = $"relationship:{fixture.RelationshipId:D}",
                        SubjectVersion = "relationship-3",
                        IssuedAt = DateTimeOffset.UtcNow.AddMinutes(-20),
                        ExpiresAt = DateTimeOffset.UtcNow.AddMinutes(-5),
                    }
                )
            );
        var expired = Assert.IsType<ObjectResult>(
            await fixture.Controller.ResolveFocusAsync(
                fixture.RelationshipId,
                new(expiredToken),
                CancellationToken.None
            )
        );
        Assert.Equal(StatusCodes.Status410Gone, expired.StatusCode);

        await using (var db = fixture.Factory.CreateDbContext())
        {
            var relationship = await db.EmploymentRelationships.SingleAsync();
            relationship.StateVersion += 1;
            await db.SaveChangesAsync();
        }
        var changed = Assert.IsType<ObjectResult>(
            await fixture.Controller.ResolveFocusAsync(
                fixture.RelationshipId,
                new(focus.FocusToken),
                CancellationToken.None
            )
        );
        Assert.Equal(StatusCodes.Status409Conflict, changed.StatusCode);
    }

    [Fact]
    public async Task ChannelSessionEndValidatesReplaysAndRejectsDivergentKeys()
    {
        var fixture = await CreateAsync(addChannelBinding: true);

        var invalid = Assert.IsType<ObjectResult>(
            await fixture.Controller.EndChannelSessionAsync(
                fixture.RelationshipId,
                fixture.ChannelSessionId,
                new(0, "WRONG_CONFIRMATION", null),
                CancellationToken.None
            )
        );
        Assert.Equal(StatusCodes.Status400BadRequest, invalid.StatusCode);

        fixture.Controller.Request.Headers["Idempotency-Key"] = "channel-end-controller-0001";
        fixture.Controller.Request.Headers["X-Correlation-ID"] = Guid.NewGuid().ToString();
        var ended = Assert.IsType<OkObjectResult>(
            await fixture.Controller.EndChannelSessionAsync(
                fixture.RelationshipId,
                fixture.ChannelSessionId,
                new(0, "END_CHANNEL_SESSION", "customer requested"),
                CancellationToken.None
            )
        );
        Assert.NotNull(ended.Value);

        var replay = Assert.IsType<OkObjectResult>(
            await fixture.Controller.EndChannelSessionAsync(
                fixture.RelationshipId,
                fixture.ChannelSessionId,
                new(0, "END_CHANNEL_SESSION", "customer requested"),
                CancellationToken.None
            )
        );
        Assert.NotNull(replay.Value);

        var divergent = Assert.IsType<ObjectResult>(
            await fixture.Controller.EndChannelSessionAsync(
                fixture.RelationshipId,
                fixture.ChannelSessionId,
                new(0, "END_CHANNEL_SESSION", "different request"),
                CancellationToken.None
            )
        );
        Assert.Equal(StatusCodes.Status409Conflict, divergent.StatusCode);
        await using var db = fixture.Factory.CreateDbContext();
        Assert.Equal("ENDED", (await db.ChannelBindings.SingleAsync()).Status);
        Assert.Equal(
            EmploymentRelationshipState.Active,
            (await db.EmploymentRelationships.SingleAsync()).State
        );
    }

    [Fact]
    public async Task ChannelSessionEndReturnsVersionAndAccessibilityProblems()
    {
        var fixture = await CreateAsync(addChannelBinding: true);
        fixture.Controller.Request.Headers["Idempotency-Key"] = "channel-end-controller-0002";

        var version = Assert.IsType<ObjectResult>(
            await fixture.Controller.EndChannelSessionAsync(
                fixture.RelationshipId,
                fixture.ChannelSessionId,
                new(1, "END_CHANNEL_SESSION", null),
                CancellationToken.None
            )
        );
        Assert.Equal(StatusCodes.Status409Conflict, version.StatusCode);

        var inaccessible = Assert.IsType<ObjectResult>(
            await fixture.Controller.EndChannelSessionAsync(
                fixture.RelationshipId,
                Guid.NewGuid(),
                new(0, "END_CHANNEL_SESSION", null),
                CancellationToken.None
            )
        );
        Assert.Equal(StatusCodes.Status404NotFound, inaccessible.StatusCode);
    }

    [Fact]
    public async Task AlreadyEndedSessionReplaysWithoutChangingRelationship()
    {
        var fixture = await CreateAsync(addChannelBinding: true, channelStatus: "ENDED");
        fixture.Controller.Request.Headers["Idempotency-Key"] = "channel-end-controller-0003";

        var replay = Assert.IsType<OkObjectResult>(
            await fixture.Controller.EndChannelSessionAsync(
                fixture.RelationshipId,
                fixture.ChannelSessionId,
                new(0, "END_CHANNEL_SESSION", null),
                CancellationToken.None
            )
        );

        Assert.NotNull(replay.Value);
        await using var db = fixture.Factory.CreateDbContext();
        Assert.Equal(
            EmploymentRelationshipState.Active,
            (await db.EmploymentRelationships.SingleAsync()).State
        );
    }

    [Fact]
    public async Task ConstitutionalDenialIsReturnedAsAForbiddenProblem()
    {
        var fixture = await CreateAsync(
            addChannelBinding: true,
            gateway: new DenyingRelationshipConstitutionalGateway()
        );
        fixture.Controller.Request.Headers["Idempotency-Key"] = "channel-end-controller-0004";

        var denied = Assert.IsType<ObjectResult>(
            await fixture.Controller.EndChannelSessionAsync(
                fixture.RelationshipId,
                fixture.ChannelSessionId,
                new(0, "END_CHANNEL_SESSION", null),
                CancellationToken.None
            )
        );

        Assert.Equal(StatusCodes.Status403Forbidden, denied.StatusCode);
    }

    [Fact]
    public async Task MembershipContextTakesPrecedenceOverFallbackClaims()
    {
        var fixture = await CreateAsync(useMembershipContext: true);

        Assert.IsType<OkObjectResult>(
            await fixture.Controller.GetProgressAsync(
                fixture.RelationshipId,
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task MissingAuthorityIsRejectedBeforeOwnerAccess()
    {
        var fixture = await CreateAsync(authorize: false);

        Assert.IsType<UnauthorizedResult>(
            await fixture.Controller.GetPreferencesAsync(
                fixture.RelationshipId,
                CancellationToken.None
            )
        );
        Assert.IsType<UnauthorizedResult>(
            await fixture.Controller.ReplacePreferencesAsync(
                fixture.RelationshipId,
                new(0, "LIFECYCLE", true),
                CancellationToken.None
            )
        );
        Assert.IsType<UnauthorizedResult>(
            await fixture.Controller.GetProgressAsync(
                fixture.RelationshipId,
                CancellationToken.None
            )
        );
        Assert.IsType<UnauthorizedResult>(
            await fixture.Controller.ResolveFocusAsync(
                fixture.RelationshipId,
                new("opaque-token"),
                CancellationToken.None
            )
        );
        Assert.IsType<UnauthorizedResult>(
            await fixture.Controller.EndChannelSessionAsync(
                fixture.RelationshipId,
                fixture.ChannelSessionId,
                new(0, "END_CHANNEL_SESSION", null),
                CancellationToken.None
            )
        );
    }

    private static async Task<Fixture> CreateAsync(
        bool addChannelBinding = false,
        bool authorize = true,
        EmploymentRelationshipState state = EmploymentRelationshipState.Active,
        string channelStatus = "ACTIVE",
        IRelationshipConstitutionalGateway? gateway = null,
        bool useMembershipContext = true
    )
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var dataProtectionProvider = new EphemeralDataProtectionProvider();
        var service = new CustomerEngagementWorkspaceService(
            factory,
            dataProtectionProvider,
            gateway ?? new RecordingRelationshipConstitutionalGateway()
        );
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var channelSessionId = Guid.NewGuid();
        var evidenceId = Guid.NewGuid();
        await using (var db = factory.CreateDbContext())
        {
            db.EmploymentRelationships.Add(
                new EmploymentRelationship
                {
                    TenantId = tenantId,
                    RelationshipId = relationshipId,
                    AgentInstanceId = Guid.NewGuid(),
                    ProfessionalType = "DMA",
                    ProfessionalVersion = "1.0.0",
                    EvaluationIntentId = Guid.NewGuid(),
                    InitiatingParticipantId = participantId,
                    State = state,
                    StateVersion = 3,
                }
            );
            db.RelationshipParticipants.Add(
                new RelationshipParticipant
                {
                    TenantId = tenantId,
                    RelationshipId = relationshipId,
                    ParticipantId = participantId,
                    Role = RelationshipParticipantRole.Employer,
                    BoundEvidenceId = evidenceId,
                }
            );
            db.RelationshipStateHistory.Add(
                new RelationshipStateHistory
                {
                    TenantId = tenantId,
                    RelationshipId = relationshipId,
                    StateVersion = 3,
                    ToState = state,
                    ActorParticipantId = participantId,
                    ActorRole = RelationshipParticipantRole.Employer,
                    CorrelationId = Guid.NewGuid(),
                    EvidenceId = evidenceId,
                }
            );
            if (addChannelBinding)
            {
                db.ChannelBindings.Add(
                    new ChannelBinding
                    {
                        TenantId = tenantId,
                        BindingId = channelSessionId,
                        RelationshipId = relationshipId,
                        ParticipantId = participantId,
                        Channel = "WHATSAPP",
                        ConversationId = Guid.NewGuid().ToString("D"),
                        AssuranceLevel = "OTP",
                        Status = channelStatus,
                    }
                );
            }
            await db.SaveChangesAsync();
        }

        var user = authorize
            ? new ClaimsPrincipal(
                new ClaimsIdentity(
                    [new Claim(ClaimTypes.NameIdentifier, participantId.ToString())],
                    "Test"
                )
            )
            : new ClaimsPrincipal(new ClaimsIdentity());
        var httpContext = new DefaultHttpContext { User = user };
        if (authorize)
        {
            httpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId.ToString();
            if (useMembershipContext)
            {
                httpContext.Items[CustomerMembershipMiddleware.MembershipItem] =
                    new CustomerWorkspaceMembership(
                        participantId,
                        tenantId,
                        Guid.NewGuid(),
                        ["OWNER"]
                    );
            }
        }
        var controller = new CustomerEngagementWorkspaceController(service)
        {
            ControllerContext = new ControllerContext { HttpContext = httpContext },
        };
        return new(
            factory,
            controller,
            dataProtectionProvider,
            tenantId,
            participantId,
            relationshipId,
            channelSessionId
        );
    }

    private sealed record Fixture(
        InMemoryEmploymentRelationshipFactory Factory,
        CustomerEngagementWorkspaceController Controller,
        IDataProtectionProvider DataProtectionProvider,
        Guid TenantId,
        Guid ParticipantId,
        Guid RelationshipId,
        Guid ChannelSessionId
    );

    private sealed class DenyingRelationshipConstitutionalGateway
        : IRelationshipConstitutionalGateway
    {
        public Task<Guid> AuthorizeAndRecordAsync(
            Guid tenantId,
            Guid relationshipId,
            string professionalType,
            string actionType,
            Guid correlationId,
            object actionParameters,
            CancellationToken cancellationToken
        ) => throw new ConstitutionalActionDeniedException("Denied by test policy.");
    }
}
