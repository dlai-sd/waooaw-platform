// Implements: work-contracts/WC-059-goal005-ae01-contract-payment-activation.md §WC059-05
// constitutional_basis: C-002, C-023, C-026, C-059, C-088

using System.Collections.Concurrent;
using System.Security.Cryptography;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record ActivationRequest(
    Guid TenantId,
    Guid RelationshipId,
    Guid ActorParticipantId,
    Guid AcceptedContractId,
    int ContractVersion,
    Guid ContractAcceptanceId,
    string PaymentReference,
    Guid PaymentEvidenceId,
    Guid AuthoritySnapshotId,
    Guid CorrelationId);

public sealed record ActivationBillingRequest(
    Guid TenantId,
    Guid RelationshipId,
    Guid ActorParticipantId,
    Guid ActivationIntentId,
    Guid AcceptedContractId,
    int ContractVersion,
    Guid ContractAcceptanceId,
    string PaymentReference,
    Guid PaymentEvidenceId,
    Guid CorrelationId);

public sealed record ActivationBillingOutcome(Guid SubscriptionId, string Status);
public sealed record ActivationOutcome(Guid ActivationIntentId, Guid SubscriptionId, Guid EvidenceId, string Status);

public interface IActivationBillingGateway
{
    Task<ActivationBillingOutcome> ActivatePaidSubscriptionAsync(
        ActivationBillingRequest request, CancellationToken cancellationToken);
}

public sealed class ActivationConflictException() : Exception("Canonical activation tuple has divergent material.");
public sealed class ActivationOwnerUnavailableException(string reason, Exception? innerException = null)
    : Exception(reason, innerException);
public sealed class ActivationEligibilityException(string reason) : Exception(reason);

public sealed class ActivationOrchestrationService(
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
    EmploymentRelationshipService relationships,
    IRelationshipConstitutionalGateway constitutionalGateway,
    IActivationBillingGateway billingGateway,
    IOfferabilityGuard offerabilityGuard)
{
    private static readonly ConcurrentDictionary<string, CanonicalTupleLock> CanonicalTupleLocks = new();

    public async Task<ActivationOutcome> ActivateAsync(
        ActivationRequest request, CancellationToken cancellationToken)
    {
        var tupleKey = $"{request.TenantId:D}|{request.RelationshipId:D}|{request.AcceptedContractId:D}|{request.PaymentReference}";
        var tupleLock = AcquireTupleLockReference(tupleKey);
        await tupleLock.Gate.WaitAsync(cancellationToken);
        try
        {
            return await ActivateCanonicalTupleAsync(request, cancellationToken);
        }
        finally
        {
            tupleLock.Gate.Release();
            ReleaseTupleLockReference(tupleKey, tupleLock);
        }
    }

    public async Task<ActivationOutcome?> PrepareDispatchAsync(
        ActivationRequest request, CancellationToken cancellationToken)
    {
        var materialHash = HashMaterial(request);
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var existing = await FindIntentAsync(db, request, cancellationToken);
        if (existing is null)
        {
            await ValidateEligibilityAsync(request, cancellationToken);
            existing = await LoadOrCreateIntentAsync(request, materialHash, cancellationToken);
        }

        if (!CryptographicOperations.FixedTimeEquals(
                Convert.FromHexString(existing.MaterialRequestHash), Convert.FromHexString(materialHash)))
        {
            await RecordConflictAsync(existing, materialHash, cancellationToken);
            throw new ActivationConflictException();
        }

        return existing.Status == "SUCCEEDED" ? ToOutcome(existing) : null;
    }

    private static CanonicalTupleLock AcquireTupleLockReference(string tupleKey)
    {
        while (true)
        {
            var tupleLock = CanonicalTupleLocks.GetOrAdd(tupleKey, static _ => new());
            lock (tupleLock)
            {
                if (CanonicalTupleLocks.TryGetValue(tupleKey, out var current)
                    && ReferenceEquals(current, tupleLock))
                {
                    tupleLock.References++;
                    return tupleLock;
                }
            }
        }
    }

    private static void ReleaseTupleLockReference(string tupleKey, CanonicalTupleLock tupleLock)
    {
        lock (tupleLock)
        {
            tupleLock.References--;
            if (tupleLock.References == 0)
                CanonicalTupleLocks.TryRemove(new KeyValuePair<string, CanonicalTupleLock>(tupleKey, tupleLock));
        }
    }

    private sealed class CanonicalTupleLock
    {
        public SemaphoreSlim Gate { get; } = new(1, 1);
        public int References { get; set; }
    }

    private async Task<ActivationOutcome> ActivateCanonicalTupleAsync(
        ActivationRequest request, CancellationToken cancellationToken)
    {
        var materialHash = HashMaterial(request);
        var intent = await LoadOrCreateIntentAsync(request, materialHash, cancellationToken);
        if (!string.Equals(intent.MaterialRequestHash, materialHash, StringComparison.Ordinal))
        {
            await RecordConflictAsync(intent, materialHash, cancellationToken);
            throw new ActivationConflictException();
        }
        if (intent.Status == "SUCCEEDED") return ToOutcome(intent);
        if (intent.Status == "CONFLICT") throw new ActivationConflictException();

        var professionalType = await ValidateEligibilityAsync(request, cancellationToken);
        await EnterActivationPendingAsync(request, cancellationToken);

        ActivationBillingOutcome billingOutcome;
        try
        {
            billingOutcome = await billingGateway.ActivatePaidSubscriptionAsync(
                new ActivationBillingRequest(
                    request.TenantId,
                    request.RelationshipId,
                    request.ActorParticipantId,
                    intent.ActivationIntentId,
                    request.AcceptedContractId,
                    request.ContractVersion,
                    request.ContractAcceptanceId,
                    request.PaymentReference,
                    request.PaymentEvidenceId,
                    request.CorrelationId),
                cancellationToken);
            if (billingOutcome.Status != "ACTIVE" || billingOutcome.SubscriptionId == Guid.Empty)
                throw new ActivationOwnerUnavailableException("WBE paid activation outcome is not active.");
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            await MarkRetryableAsync(intent.ActivationIntentId, cancellationToken);
            throw exception is ActivationOwnerUnavailableException
                ? exception
                : new ActivationOwnerUnavailableException("WBE paid activation outcome is unresolved.", exception);
        }

        Guid evidenceId;
        try
        {
            evidenceId = await constitutionalGateway.AuthorizeAndRecordAsync(
                request.TenantId,
                request.RelationshipId,
                professionalType,
                "ACTIVATE_PAID_EMPLOYMENT_RELATIONSHIP",
                request.CorrelationId,
                new
                {
                    activation_intent_id = intent.ActivationIntentId,
                    accepted_contract_id = request.AcceptedContractId,
                    contract_acceptance_id = request.ContractAcceptanceId,
                    payment_reference = request.PaymentReference,
                    payment_evidence_id = request.PaymentEvidenceId,
                    subscription_id = billingOutcome.SubscriptionId,
                    authority_snapshot_id = request.AuthoritySnapshotId,
                },
                cancellationToken);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            await MarkRetryableAsync(intent.ActivationIntentId, cancellationToken);
            throw new ActivationOwnerUnavailableException("Constitutional activation evidence is unresolved.", exception);
        }

        return await CompleteAsync(request, intent.ActivationIntentId, billingOutcome.SubscriptionId, evidenceId, cancellationToken);
    }

    private async Task<ActivationIntent> LoadOrCreateIntentAsync(
        ActivationRequest request, string materialHash, CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var existing = await FindIntentAsync(db, request, cancellationToken);
        if (existing is not null) return existing;
        var intent = new ActivationIntent
        {
            TenantId = request.TenantId,
            RelationshipId = request.RelationshipId,
            AcceptedContractId = request.AcceptedContractId,
            ContractAcceptanceId = request.ContractAcceptanceId,
            PaymentReference = request.PaymentReference,
            CorrelationId = request.CorrelationId,
            MaterialRequestHash = materialHash,
        };
        db.ActivationIntents.Add(intent);
        try
        {
            await db.SaveChangesAsync(cancellationToken);
            return intent;
        }
        catch (DbUpdateException)
        {
            await using var replayDb = await dbFactory.CreateDbContextAsync(cancellationToken);
            var replay = await FindIntentAsync(replayDb, request, cancellationToken);
            if (replay is null) throw;
            return replay;
        }
    }

    private async Task<string> ValidateEligibilityAsync(ActivationRequest request, CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await db.EmploymentRelationships.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == request.TenantId && value.RelationshipId == request.RelationshipId,
            cancellationToken) ?? throw new ActivationEligibilityException("Relationship not found.");
        if (relationship.AcceptedContractId != request.AcceptedContractId
            || relationship.AuthoritySnapshotId != request.AuthoritySnapshotId
            || relationship.State is not (EmploymentRelationshipState.ContractAcceptedPendingPayment
                or EmploymentRelationshipState.ActivationPending))
            throw new ActivationEligibilityException("Relationship is not eligible for paid activation.");
        var accepted = await db.ContractAcceptances.AsNoTracking().AnyAsync(
            value => value.TenantId == request.TenantId
                && value.RelationshipId == request.RelationshipId
                && value.ContractId == request.AcceptedContractId
                && value.AcceptanceId == request.ContractAcceptanceId
                && value.AuthoritySnapshotId == request.AuthoritySnapshotId,
            cancellationToken);
        if (!accepted) throw new ActivationEligibilityException("Exact contract acceptance is not eligible.");
        await offerabilityGuard.RequireEligibleAsync(request.TenantId, request.RelationshipId, cancellationToken);
        return relationship.ProfessionalType;
    }

    private async Task EnterActivationPendingAsync(ActivationRequest request, CancellationToken cancellationToken)
    {
        var relationship = await relationships.GetAsync(request.TenantId, request.RelationshipId, cancellationToken);
        if (relationship?.State == EmploymentRelationshipState.ActivationPending) return;
        if (relationship?.State != EmploymentRelationshipState.ContractAcceptedPendingPayment)
            throw new ActivationEligibilityException("Relationship cannot enter activation pending.");
        await relationships.TransitionAsync(
            request.TenantId,
            request.RelationshipId,
            request.ActorParticipantId,
            RelationshipParticipantRole.Employer,
            EmploymentRelationshipState.ActivationPending,
            request.CorrelationId,
            false,
            cancellationToken);
    }

    private async Task<ActivationOutcome> CompleteAsync(
        ActivationRequest request, Guid intentId, Guid subscriptionId, Guid evidenceId,
        CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var intent = await db.ActivationIntents.SingleAsync(value => value.ActivationIntentId == intentId, cancellationToken);
        if (intent.Status == "SUCCEEDED") return ToOutcome(intent);
        var relationship = await db.EmploymentRelationships.SingleAsync(
            value => value.TenantId == request.TenantId && value.RelationshipId == request.RelationshipId,
            cancellationToken);
        if (relationship.State != EmploymentRelationshipState.ActivationPending)
            throw new ActivationEligibilityException("Relationship left activation pending before completion.");
        var now = DateTimeOffset.UtcNow;
        relationship.State = EmploymentRelationshipState.Active;
        relationship.StateVersion += 1;
        relationship.ActivationId = intentId;
        relationship.UpdatedAt = now;
        db.RelationshipStateHistory.Add(new RelationshipStateHistory
        {
            TenantId = request.TenantId,
            RelationshipId = request.RelationshipId,
            StateVersion = relationship.StateVersion,
            FromState = EmploymentRelationshipState.ActivationPending,
            ToState = EmploymentRelationshipState.Active,
            ActorParticipantId = request.ActorParticipantId,
            ActorRole = RelationshipParticipantRole.Employer,
            AuthoritySnapshotId = request.AuthoritySnapshotId,
            CorrelationId = request.CorrelationId,
            EvidenceId = evidenceId,
            OccurredAt = now,
        });
        intent.Status = "SUCCEEDED";
        intent.OutcomeSubscriptionId = subscriptionId;
        intent.OutcomeEvidenceId = evidenceId;
        intent.OutcomeJson = JsonSerializer.Serialize(new { subscription_id = subscriptionId, relationship_state = "ACTIVE" });
        intent.CompletedAt = now;
        intent.UpdatedAt = now;
        await db.SaveChangesAsync(cancellationToken);
        return ToOutcome(intent);
    }

    private async Task MarkRetryableAsync(Guid intentId, CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var intent = await db.ActivationIntents.SingleAsync(value => value.ActivationIntentId == intentId, cancellationToken);
        if (intent.Status is "SUCCEEDED" or "CONFLICT") return;
        intent.Status = "FAILED_RETRYABLE";
        intent.UpdatedAt = DateTimeOffset.UtcNow;
        await db.SaveChangesAsync(cancellationToken);
    }

    private async Task RecordConflictAsync(
        ActivationIntent intent, string conflictingHash, CancellationToken cancellationToken)
    {
        if (intent.Status is "SUCCEEDED" or "CONFLICT") return;
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var stored = await db.ActivationIntents.SingleAsync(
            value => value.ActivationIntentId == intent.ActivationIntentId, cancellationToken);
        stored.Status = "CONFLICT";
        stored.ConflictingRequestHash = conflictingHash;
        stored.CompletedAt = DateTimeOffset.UtcNow;
        await db.SaveChangesAsync(cancellationToken);
    }

    private static Task<ActivationIntent?> FindIntentAsync(
        EmploymentRelationshipDbContext db, ActivationRequest request, CancellationToken cancellationToken) =>
        db.ActivationIntents.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == request.TenantId
                && value.RelationshipId == request.RelationshipId
                && value.AcceptedContractId == request.AcceptedContractId
                && value.PaymentReference == request.PaymentReference,
            cancellationToken);

    internal static string HashMaterial(ActivationRequest request) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(string.Join("|",
            request.TenantId.ToString("D"), request.RelationshipId.ToString("D"),
            request.ActorParticipantId.ToString("D"), request.AcceptedContractId.ToString("D"),
            request.ContractVersion,
            request.ContractAcceptanceId.ToString("D"), request.PaymentReference,
            request.PaymentEvidenceId.ToString("D"), request.AuthoritySnapshotId.ToString("D"),
            request.CorrelationId.ToString("D")))));

    private static ActivationOutcome ToOutcome(ActivationIntent intent) => new(
        intent.ActivationIntentId,
        intent.OutcomeSubscriptionId ?? throw new ActivationOwnerUnavailableException("Stored subscription outcome is absent."),
        intent.OutcomeEvidenceId ?? throw new ActivationOwnerUnavailableException("Stored evidence outcome is absent."),
        intent.Status);
}

public sealed class UnconfiguredActivationBillingGateway : IActivationBillingGateway
{
    public Task<ActivationBillingOutcome> ActivatePaidSubscriptionAsync(
        ActivationBillingRequest request, CancellationToken cancellationToken) =>
        throw new ActivationOwnerUnavailableException("Authenticated WBE paid activation is not configured.");
}