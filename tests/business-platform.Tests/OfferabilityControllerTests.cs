// Implements: WC-065 WC065-03, WC065-06; business-platform.openapi.yaml Founder offerability API
// constitutional_basis: C-002, C-023, C-059, C-076, C-089

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class OfferabilityControllerTests
{
    [Fact]
    public async Task EvaluateRequiresFounderAndBoundTenantContext()
    {
        var fixture = await CreateFixtureAsync();
        fixture.Controller.ControllerContext.HttpContext.User = new ClaimsPrincipal(new ClaimsIdentity(
            [new Claim("participant_id", fixture.ParticipantId.ToString())], "Test"));

        var result = await EvaluateAsync(fixture);

        Assert.IsType<ForbidResult>(result);
    }

    [Fact]
    public async Task EvaluateRejectsInvalidSchemaOrMissingRequiredHeaders()
    {
        var fixture = await CreateFixtureAsync();

        var result = await EvaluateAsync(
            fixture,
            Request() with { SchemaVersion = "2.0" },
            includeCorrelationId: false);

        AssertProblem(result, 400, "OFFERABILITY_REQUEST_INVALID");
    }

    [Fact]
    public async Task EvaluateDoesNotDiscloseUnknownRelationship()
    {
        var fixture = await CreateFixtureAsync();

        var result = await EvaluateAsync(fixture, relationshipId: Guid.NewGuid());

        AssertProblem(result, 404, "OFFERABILITY_NOT_ACCESSIBLE");
    }

    [Fact]
    public async Task EvaluateReturnsEvidencedDecision()
    {
        var fixture = await CreateFixtureAsync();

        var result = Assert.IsType<OkObjectResult>(await EvaluateAsync(fixture));
        var body = JsonSerializer.Serialize(result.Value);

        Assert.Contains("\"disposition\":\"ALLOW\"", body);
        Assert.Contains("\"directContributionPaise\":2000", body);
        Assert.Contains(fixture.RelationshipId.ToString(), body, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task EvaluateMapsChangedIdempotentIntentToConflict()
    {
        var fixture = await CreateFixtureAsync();
        var idempotencyKey = Guid.NewGuid();
        await EvaluateAsync(fixture, idempotencyKey: idempotencyKey);

        var result = await EvaluateAsync(
            fixture,
            Request() with { ProposedPricePaise = 7_001 },
            idempotencyKey: idempotencyKey);

        AssertProblem(result, 409, "OFFERABILITY_IDEMPOTENCY_CONFLICT");
    }

    [Fact]
    public async Task EvaluateMapsConstitutionalDenialToLocked()
    {
        var fixture = await CreateFixtureAsync(
            constitutional: new ConfigurableConstitutionalGateway(
                new ConstitutionalActionDeniedException("denied")));

        var result = await EvaluateAsync(fixture);

        AssertProblem(result, 423, "OFFERABILITY_BLOCKED");
    }

    [Fact]
    public async Task EvaluateMapsInvalidOfferToBadRequest()
    {
        var fixture = await CreateFixtureAsync();

        var result = await EvaluateAsync(fixture, Request() with { OfferingId = "" });

        AssertProblem(result, 400, "OFFERABILITY_REQUEST_INVALID");
    }

    [Fact]
    public async Task EvaluateFailsClosedWhenOwnerCallFails()
    {
        var fixture = await CreateFixtureAsync(
            owner: new FixedOwnerGateway(exception: new InvalidOperationException("owner unavailable")));

        var result = await EvaluateAsync(fixture);

        AssertProblem(result, 503, "OFFERABILITY_UNAVAILABLE");
    }

    private static Task<IActionResult> EvaluateAsync(
        Fixture fixture,
        EvaluateOfferabilityRequest? request = null,
        Guid? idempotencyKey = null,
        Guid? relationshipId = null,
        bool includeCorrelationId = true,
        bool includeIdempotencyKey = true) =>
        fixture.Controller.EvaluateAsync(
            relationshipId ?? fixture.RelationshipId,
            request ?? Request(),
            includeCorrelationId ? Guid.NewGuid() : null,
            includeIdempotencyKey ? idempotencyKey ?? Guid.NewGuid() : null,
            CancellationToken.None);

    private static EvaluateOfferabilityRequest Request() =>
        new("1.0", "dma-starter-v1", "DMA", "STARTER", 7_000);

    private static void AssertProblem(IActionResult result, int status, string code)
    {
        var problem = Assert.IsType<ObjectResult>(result);
        Assert.Equal(status, problem.StatusCode);
        Assert.Contains(code, JsonSerializer.Serialize(problem.Value));
    }

    private static async Task<Fixture> CreateFixtureAsync(
        IOfferabilityOwnerGateway? owner = null,
        ConfigurableConstitutionalGateway? constitutional = null)
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        constitutional ??= new ConfigurableConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory,
            constitutional,
            NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var admitted = await relationships.AdmitAsync(
            tenantId,
            participantId,
            Guid.NewGuid(),
            "DMA",
            Guid.NewGuid(),
            CancellationToken.None);
        var orchestration = new OfferabilityOrchestrationService(
            owner ?? new FixedOwnerGateway(),
            constitutional,
            factory,
            new OfferabilityService());
        var context = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(new ClaimsIdentity(
                [
                    new Claim("participant_id", participantId.ToString()),
                    new Claim("participant_role", "FOUNDER"),
                    new Claim("correlation_id", Guid.NewGuid().ToString()),
                ],
                "Test")),
        };
        context.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId.ToString();
        var controller = new OfferabilityController(relationships, orchestration)
        {
            ControllerContext = new ControllerContext { HttpContext = context },
        };
        return new Fixture(controller, participantId, admitted.Relationship.RelationshipId);
    }

    private sealed record Fixture(
        OfferabilityController Controller,
        Guid ParticipantId,
        Guid RelationshipId);

    private sealed class FixedOwnerGateway(
        OwnerOfferabilityValidation? result = null,
        Exception? exception = null) : IOfferabilityOwnerGateway
    {
        public Task<OwnerOfferabilityValidation?> ValidateAsync(
            OfferabilityEvaluationRequest request,
            CancellationToken cancellationToken)
        {
            if (exception is not null) throw exception;
            return Task.FromResult<OwnerOfferabilityValidation?>(result ?? new OwnerOfferabilityValidation(
                "APPROVED",
                5_000,
                6_250,
                request.ProposedPricePaise,
                2_000,
                "wbe-validation-7",
                DateTimeOffset.UtcNow));
        }
    }

    private sealed class ConfigurableConstitutionalGateway(Exception? evaluationException = null)
        : IRelationshipConstitutionalGateway
    {
        public Task<Guid> AuthorizeAndRecordAsync(
            Guid tenantId,
            Guid relationshipId,
            string professionalType,
            string actionType,
            Guid correlationId,
            object actionParameters,
            CancellationToken cancellationToken)
        {
            if (actionType == "EVALUATE_OFFERABILITY" && evaluationException is not null)
                throw evaluationException;
            return Task.FromResult(Guid.NewGuid());
        }
    }
}