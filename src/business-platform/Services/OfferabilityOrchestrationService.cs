// Implements: WC-065 WC065-02, WC065-03, WC065-06, FA-047
// constitutional_basis: C-002, C-023, C-059, C-089, C-091

using System.Buffers.Binary;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record OfferabilityEvaluationRequest(
    Guid TenantId,
    Guid RelationshipId,
    int RelationshipStateVersion,
    Guid ActorParticipantId,
    Guid CorrelationId,
    Guid IdempotencyKey,
    string OfferingId,
    string AgentType,
    string BundleTier,
    long ProposedPricePaise);

public sealed record OwnerOfferabilityValidation(
    string Outcome,
    long CostFloorPaise,
    long MinimumCompliantPricePaise,
    long ProposedPricePaise,
    long DirectContributionPaise,
    string ValidationVersion,
    DateTimeOffset ProducedAt);

public interface IOfferabilityOwnerGateway
{
    Task<OwnerOfferabilityValidation?> ValidateAsync(
        OfferabilityEvaluationRequest request, CancellationToken cancellationToken);
}

public sealed class OfferabilityIdempotencyConflictException : Exception;

public sealed class UnconfiguredOfferabilityOwnerGateway : IOfferabilityOwnerGateway
{
    public Task<OwnerOfferabilityValidation?> ValidateAsync(
        OfferabilityEvaluationRequest request, CancellationToken cancellationToken) =>
        Task.FromResult<OwnerOfferabilityValidation?>(null);
}

public sealed class AuthenticatedOfferabilityOwnerGateway : IOfferabilityOwnerGateway, IDisposable
{
    private const string Route = "/internal/v1/relationships/{relationshipId}/offerability-validation";
    private const string Operation = "validateRelationshipOfferability";
    private readonly WorkloadIdentityClient _identity;
    private readonly HttpClient _billingEngine;

    public AuthenticatedOfferabilityOwnerGateway(WorkloadIdentityClient identity, Uri billingEngineBaseAddress)
    {
        _identity = identity;
        _billingEngine = identity.CreateClient(billingEngineBaseAddress, "billing-engine");
    }

    public async Task<OwnerOfferabilityValidation?> ValidateAsync(
        OfferabilityEvaluationRequest request, CancellationToken cancellationToken)
    {
        var body = new SortedDictionary<string, object?>(StringComparer.Ordinal)
        {
            ["agentType"] = request.AgentType,
            ["bundleTier"] = request.BundleTier,
            ["offeringId"] = request.OfferingId,
            ["proposedPricePaise"] = request.ProposedPricePaise,
            ["schemaVersion"] = "1.0",
        };
        var bodyBytes = JsonSerializer.SerializeToUtf8Bytes(body);
        var context = new DelegatedRequestContext(
            request.ActorParticipantId.ToString("D"),
            "FOUNDER",
            request.TenantId.ToString("D"),
            request.RelationshipId.ToString("D"),
            Operation,
            request.OfferingId,
            request.CorrelationId.ToString("D"),
            null,
            new SortedDictionary<string, string>(StringComparer.Ordinal)
            {
                ["agent_type"] = request.AgentType,
                ["bundle_tier"] = request.BundleTier,
                ["offering"] = request.OfferingId,
                ["proposed_price_paise"] = request.ProposedPricePaise.ToString(),
            },
            request.CorrelationId.ToString("D"));
        var envelope = _identity.Sign(
            context,
            _identity.GetAudience("billing-engine"),
            HttpMethod.Post.Method,
            Route,
            Operation,
            1,
            Convert.ToHexStringLower(SHA256.HashData(bodyBytes)),
            DateTimeOffset.UtcNow);
        using var message = new HttpRequestMessage(
            HttpMethod.Post, Route.Replace("{relationshipId}", request.RelationshipId.ToString("D")))
        {
            Content = new ByteArrayContent(bodyBytes),
        };
        message.Content.Headers.ContentType = new("application/json");
        message.Headers.Authorization = new AuthenticationHeaderValue("Bearer", envelope);
        message.Headers.Add("X-Correlation-ID", request.CorrelationId.ToString("D"));
        try
        {
            using var response = await _billingEngine.SendAsync(message, cancellationToken);
            if (!response.IsSuccessStatusCode) return null;
            var result = await response.Content.ReadFromJsonAsync<WbeOfferabilityValidation>(cancellationToken);
            if (result is null
                || result.RelationshipId != request.RelationshipId
                || !string.Equals(result.OfferingId, request.OfferingId, StringComparison.Ordinal)
                || result.ProposedPricePaise != request.ProposedPricePaise)
                return null;
            return new OwnerOfferabilityValidation(
                result.Outcome,
                result.CostFloorPaise,
                result.MinimumCompliantPricePaise,
                result.ProposedPricePaise,
                result.DirectContributionPaise,
                result.ValidationVersion,
                result.ProducedAt);
        }
        catch (Exception exception) when (exception is HttpRequestException or TaskCanceledException or JsonException)
        {
            return null;
        }
    }

    public void Dispose() => _billingEngine.Dispose();

    private sealed record WbeOfferabilityValidation(
        [property: JsonPropertyName("relationshipId")] Guid RelationshipId,
        [property: JsonPropertyName("offeringId")] string OfferingId,
        [property: JsonPropertyName("outcome")] string Outcome,
        [property: JsonPropertyName("costFloorPaise")] long CostFloorPaise,
        [property: JsonPropertyName("minimumCompliantPricePaise")] long MinimumCompliantPricePaise,
        [property: JsonPropertyName("proposedPricePaise")] long ProposedPricePaise,
        [property: JsonPropertyName("directContributionPaise")] long DirectContributionPaise,
        [property: JsonPropertyName("validationVersion")] string ValidationVersion,
        [property: JsonPropertyName("producedAt")] DateTimeOffset ProducedAt);
}

public sealed class OfferabilityOrchestrationService(
    IOfferabilityOwnerGateway owner,
    IRelationshipConstitutionalGateway constitutional,
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
    OfferabilityService policy)
{
    private const string IdempotencyPurpose = "OFFERABILITY_EVALUATION";
    private static readonly TimeSpan OwnerFreshness = TimeSpan.FromMinutes(5);
    private static readonly TimeSpan DecisionLifetime = TimeSpan.FromHours(24);

    public async Task<OfferabilityDecisionRecord> EvaluateAsync(
        OfferabilityEvaluationRequest request, CancellationToken cancellationToken)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(request.OfferingId);
        ArgumentException.ThrowIfNullOrWhiteSpace(request.AgentType);
        ArgumentException.ThrowIfNullOrWhiteSpace(request.BundleTier);
        if (request.ProposedPricePaise <= 0) throw new ArgumentOutOfRangeException(nameof(request.ProposedPricePaise));

        var materialRequestHash = Convert.ToHexStringLower(SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(
            new SortedDictionary<string, object?>(StringComparer.Ordinal)
            {
                ["agent_type"] = request.AgentType,
                ["bundle_tier"] = request.BundleTier,
                ["offering_id"] = request.OfferingId,
                ["proposed_price_paise"] = request.ProposedPricePaise,
                ["relationship_state_version"] = request.RelationshipStateVersion,
            })));
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        long? lockKey = null;
        var connectionOpened = false;
        var lockAcquired = false;
        if (db.Database.ProviderName?.Contains("Npgsql", StringComparison.Ordinal) == true)
        {
            var lockMaterial = Encoding.UTF8.GetBytes(
                $"{request.TenantId:D}:{IdempotencyPurpose}:{request.IdempotencyKey:D}");
            lockKey = BinaryPrimitives.ReadInt64BigEndian(SHA256.HashData(lockMaterial));
            await db.Database.OpenConnectionAsync(cancellationToken);
            connectionOpened = true;
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT pg_advisory_lock({lockKey.Value})",
                cancellationToken);
            lockAcquired = true;
        }
        try
        {
            var reservation = await db.RelationshipIdempotency.SingleOrDefaultAsync(value =>
                value.TenantId == request.TenantId
                && value.Purpose == IdempotencyPurpose
                && value.IdempotencyKey == request.IdempotencyKey.ToString("D"),
                cancellationToken);
            if (reservation is not null
                && (reservation.RelationshipId != request.RelationshipId
                    || reservation.MaterialRequestHash != materialRequestHash))
                throw new OfferabilityIdempotencyConflictException();
            if (reservation is null)
            {
                reservation = new RelationshipIdempotency
                {
                    TenantId = request.TenantId,
                    RelationshipId = request.RelationshipId,
                    Purpose = IdempotencyPurpose,
                    IdempotencyKey = request.IdempotencyKey.ToString("D"),
                    MaterialRequestHash = materialRequestHash,
                };
                db.RelationshipIdempotency.Add(reservation);
                await db.SaveChangesAsync(cancellationToken);
            }
            var existing = await db.OfferabilityDecisions.AsNoTracking()
                .SingleOrDefaultAsync(value =>
                    value.TenantId == request.TenantId
                    && value.RelationshipId == request.RelationshipId
                    && value.IdempotencyKey == request.IdempotencyKey,
                    cancellationToken);
            if (existing is not null)
                return existing.MaterialRequestHash == materialRequestHash
                    ? existing
                    : throw new OfferabilityIdempotencyConflictException();

            var validation = await owner.ValidateAsync(request, cancellationToken);
            var now = DateTimeOffset.UtcNow;
            var isCurrent = validation is not null
                && validation.ProducedAt <= now.AddMinutes(1)
                && validation.ProducedAt >= now.Subtract(OwnerFreshness);
            var ownerVersions = validation is null
                ? new Dictionary<string, string>()
                : new Dictionary<string, string>(StringComparer.Ordinal)
                {
                    ["WBE"] = validation.ValidationVersion,
                    ["RELATIONSHIP"] = request.RelationshipStateVersion.ToString(),
                };
            var decision = policy.Evaluate(new OfferabilityInput(
                request.OfferingId,
                "FA-047-v1",
                request.ProposedPricePaise,
                validation?.CostFloorPaise ?? 0,
                isCurrent,
                false,
                true,
                validation?.Outcome == "APPROVED",
                false,
                ownerVersions));
            var evidenceId = await constitutional.AuthorizeAndRecordAsync(
                request.TenantId,
                request.RelationshipId,
                request.AgentType,
                "EVALUATE_OFFERABILITY",
                request.IdempotencyKey,
                new
                {
                    request.OfferingId,
                    request.BundleTier,
                    request.ProposedPricePaise,
                    decision.Disposition,
                    decision.DirectContributionAmount,
                    decision.PolicyVersion,
                    decision.OwnerVersions,
                    decision.Reasons,
                },
                cancellationToken);
            var record = new OfferabilityDecisionRecord
            {
                TenantId = request.TenantId,
                RelationshipId = request.RelationshipId,
                IdempotencyKey = request.IdempotencyKey,
                MaterialRequestHash = materialRequestHash,
                RelationshipStateVersion = request.RelationshipStateVersion,
                PolicyVersion = decision.PolicyVersion,
                Disposition = decision.Disposition.ToString().ToUpperInvariant(),
                DirectContributionAmount = decision.DirectContributionAmount,
                OwnerVersionsJson = JsonSerializer.Serialize(decision.OwnerVersions),
                ReasonsJson = JsonSerializer.Serialize(decision.Reasons),
                EvidenceId = evidenceId,
                ProducedAt = now,
                ExpiresAt = now.Add(DecisionLifetime),
            };
            db.OfferabilityDecisions.Add(record);
            reservation.Status = "SUCCEEDED";
            reservation.OutcomeReference = record.DecisionId;
            reservation.CompletedAt = now;
            await db.SaveChangesAsync(cancellationToken);
            return record;
        }
        finally
        {
            if (lockAcquired)
            {
                await db.Database.ExecuteSqlInterpolatedAsync(
                    $"SELECT pg_advisory_unlock({lockKey!.Value})",
                    CancellationToken.None);
            }
            if (connectionOpened)
            {
                await db.Database.CloseConnectionAsync();
            }
        }
    }
}