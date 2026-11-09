using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

/// <summary>Original generation identity and optional immutable reservation usage.</summary>
public sealed record ConversationInferenceRequest(
    Guid ExecutionId,
    Guid ConversationId,
    Guid ContributionRef,
    Guid RelationshipRef,
    string RequestDigest,
    string InputDigest,
    string InputLanguage,
    OperationalMandateV1 OperationalMandate,
    Guid? ReservationId = null,
    Guid? CommercialReservationId = null,
    long? InputTokens = null,
    long? OutputTokens = null,
    ConversationInferenceBatchV1? Batch = null
);

public sealed record ConversationInferenceBatchSourceV1(
    string SchemaVersion,
    Guid MessageId,
    Guid ExecutionId,
    long Sequence,
    Guid WorkItemId,
    int WorkItemRevision,
    Guid WorkItemInvocationId,
    Guid IdempotencyKey,
    Guid EvidenceId,
    string Text,
    string Language,
    OperationalMandateV1 OperationalMandate
);

public sealed record ConversationInferenceBatchV1(
    Guid BatchId,
    string SourceListDigest,
    IReadOnlyList<ConversationInferenceBatchSourceV1> Sources
);

/// <summary>Evidence-backed bounded permit; never permission to replay an unknown attempt.</summary>
public sealed record ConversationInferencePermitV1(
    Guid ReservationId,
    Guid CommercialReservationId,
    Guid EvidenceId,
    decimal MaximumCostPaise,
    DateTimeOffset ExpiresAt,
    JsonElement Binding
);

/// <summary>Known terminal financial outcome, independent of professional content release.</summary>
public sealed record ConversationInferenceSettlementV1(string State);

/// <summary>Read-only financial receipt; never a dispatch permit or professional result.</summary>
public sealed record ConversationInferenceReceiptV1(
    string State,
    Guid? ReservationId = null,
    Guid? CommercialReservationId = null,
    Guid? EvidenceId = null,
    decimal? MaximumCostPaise = null,
    DateTimeOffset? ExpiresAt = null
);

/// <summary>Original generation source and separately issued current content-read authority.</summary>
public sealed record ConversationInferenceContentReadRequest(
    ConversationInferenceRequest Original,
    RuntimeReconciliationRequestV1 Permission
);

/// <summary>Current read permission only; never a generation or financial permit.</summary>
public sealed record ConversationInferenceContentReadV1(string State);

public interface IConversationInferenceOwner
{
    Task<JsonElement> ResolveAsync(
        InferenceCaller caller,
        ConversationInferenceRequest request,
        CancellationToken ct
    );
    Task<ConversationInferencePermitV1> ReserveAsync(
        InferenceCaller caller,
        ConversationInferenceRequest request,
        CancellationToken ct
    );
    Task SettleAsync(
        InferenceCaller caller,
        ConversationInferenceRequest request,
        bool release,
        CancellationToken ct
    );
    Task<ConversationInferenceReceiptV1> ReconcileAsync(
        InferenceCaller caller,
        ConversationInferenceRequest request,
        CancellationToken ct
    );
    Task<ConversationInferenceContentReadV1> ReadContentAsync(
        InferenceCaller caller,
        ConversationInferenceContentReadRequest request,
        CancellationToken ct
    );
}

public sealed class ConversationInferenceOwner(
    IDbContextFactory<ConversationStoreDbContext> conversations,
    IDbContextFactory<EmploymentRelationshipDbContext> relationships,
    ConversationRuntimeEventIngestion ingestion,
    IdentityService identity,
    ConversationRuntimeIdentityAuthority runtimeIdentity,
    ConversationInferenceEvidence constitutional,
    IWhatsAppCapabilityGate capability,
    IConfiguration configuration,
    TimeProvider clock,
    IAuthenticatedOfferingUsageGateway? offeringUsage = null,
    ConversationEnvironmentSpendOwner? environmentSpend = null
) : IConversationInferenceOwner
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    private readonly IAuthenticatedOfferingUsageGateway _offeringUsage =
        offeringUsage ?? new UnconfiguredOfferingUsageGateway();
    private readonly ConversationEnvironmentSpendOwner _environmentSpend =
        environmentSpend ?? new ConversationEnvironmentSpendOwner();

    public Task<JsonElement> ResolveAsync(
        InferenceCaller caller,
        ConversationInferenceRequest request,
        CancellationToken ct
    ) =>
        WithSourceAsync(
            caller,
            request,
            async (db, binding, _) =>
            {
                var activation = capability.RequireActive(clock.GetUtcNow());
                var resolved = await WithResumeContextAsync(db, binding, caller, request, ct);
                await SetTenantAsync(db, activation.TenantId, ct);
                var digest = Convert.ToHexStringLower(
                    SHA256.HashData(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(activation)))
                );
                if (
                    await db
                        .Database.SqlQuery<int>(
                            $"""
                            SELECT 1 AS "Value" FROM business.conversation_model_reservations
                            WHERE tenant_id={activation.TenantId} AND customer_tenant_id={caller.TenantId}
                                AND execution_id={request.ExecutionId} AND (authority_digest <> {digest} OR state='RELEASED')
                            """
                        )
                        .AnyAsync(ct)
                )
                    throw new ConversationNotAccessibleException();
                return resolved;
            },
            ct
        );

    public async Task<ConversationInferencePermitV1> ReserveAsync(
        InferenceCaller caller,
        ConversationInferenceRequest request,
        CancellationToken ct
    )
    {
        var (binding, resolved) = await WithSourceAsync(
            caller,
            request,
            async (db, row, _) => (row, await WithResumeContextAsync(db, row, caller, request, ct)),
            ct
        );
        var inputRate = binding.Content.GetProperty("inputPaisePerMillion").GetInt64();
        var outputRate = binding.Content.GetProperty("outputPaisePerMillion").GetInt64();
        if (inputRate is < 0 or > 1000000000 || outputRate is < 0 or > 1000000000)
            throw new ConversationStateConflictException();
        var cost = Cost(inputRate, outputRate, 8192, 2048);
        var prior = await ReconcileAsync(caller, request, ct);
        if (prior.State == "RESERVED")
            return new ConversationInferencePermitV1(
                prior.ReservationId ?? throw new ConversationStateConflictException(),
                prior.CommercialReservationId ?? throw new ConversationStateConflictException(),
                prior.EvidenceId ?? throw new ConversationStateConflictException(),
                prior.MaximumCostPaise ?? throw new ConversationStateConflictException(),
                prior.ExpiresAt ?? throw new ConversationStateConflictException(),
                resolved
            );
        if (prior.State != "UNRESOLVED")
            throw new ConversationStateConflictException();
        var reservationAuthority = capability.RequireActive(clock.GetUtcNow());
        var existingEvidence = await ExistingCoordinatorEvidenceAsync(caller, request, ct);
        var evidence =
            existingEvidence
            ?? await constitutional.RecordAsync(
                caller,
                request,
                "CONVERSATION_MODEL_RESERVATION",
                request.ExecutionId,
                new
                {
                    relationship_id = caller.RelationshipId.ToString("D"),
                    request.ExecutionId,
                    request.RequestDigest,
                    request.OperationalMandate,
                    bindingId = binding.BindingId,
                    bindingDigest = binding.Digest,
                    maximumCostPaise = cost,
                    maximumInputTokens = 8192,
                    maximumOutputTokens = 2048,
                    environment = reservationAuthority.Environment,
                    environmentMaximumPaise = Math.Min(500m, reservationAuthority.MaximumSpendInr)
                        * 100m,
                    contextDigest = resolved
                        .GetProperty("conversationContext")
                        .GetProperty("digest")
                        .GetString(),
                },
                ct
            );
        if (evidence == Guid.Empty)
            throw new IdentityConstitutionalUnavailableException(
                "Model reservation evidence is unavailable."
            );
        var offeringIdentity = OfferingIdentity(caller, request, evidence);
        await using (var intentDb = await conversations.CreateDbContextAsync(ct))
        {
            await using var intentTransaction = await intentDb.Database.BeginTransactionAsync(ct);
            await SetTenantAsync(intentDb, caller.TenantId, ct);
            await intentDb.Database.ExecuteSqlInterpolatedAsync(
                $"""
                INSERT INTO business.conversation_inference_spend_coordinators
                    (tenant_id,relationship_id,execution_id,request_digest,owner_evidence_id,component_id,
                     invocation_id,wbe_state,operational_state,provider_dispatch_state,
                     created_at,updated_at)
                VALUES ({caller.TenantId},{caller.RelationshipId},{request.ExecutionId},
                    {request.RequestDigest},{evidence},{offeringIdentity.ComponentId},
                    {offeringIdentity.InvocationId},'PENDING','PENDING','NOT_DISPATCHED',
                    {clock.GetUtcNow()},{clock.GetUtcNow()})
                ON CONFLICT (tenant_id,execution_id) DO NOTHING
                """,
                ct
            );
            if (
                !await intentDb
                    .Database.SqlQuery<int>(
                        $"""
                        SELECT 1 AS "Value"
                        FROM business.conversation_inference_spend_coordinators
                        WHERE tenant_id={caller.TenantId}
                          AND relationship_id={caller.RelationshipId}
                          AND execution_id={request.ExecutionId}
                          AND request_digest={request.RequestDigest}
                          AND owner_evidence_id={evidence}
                          AND component_id={offeringIdentity.ComponentId}
                          AND invocation_id={offeringIdentity.InvocationId}
                        """
                    )
                    .AnyAsync(ct)
            )
                throw new ConversationStateConflictException();
            await intentTransaction.CommitAsync(ct);
        }
        var commercial = await _offeringUsage.ReserveAsync(offeringIdentity, 8192 + 2048, ct);
        await using (var commercialDb = await conversations.CreateDbContextAsync(ct))
        {
            await using var commercialTransaction =
                await commercialDb.Database.BeginTransactionAsync(ct);
            await SetTenantAsync(commercialDb, caller.TenantId, ct);
            await commercialDb.Database.ExecuteSqlInterpolatedAsync(
                $"""
                UPDATE business.conversation_inference_spend_coordinators
                SET wbe_reservation_id={commercial.ReservationId},wbe_state='RESERVED',
                    updated_at={clock.GetUtcNow()}
                WHERE tenant_id={caller.TenantId} AND execution_id={request.ExecutionId}
                    AND relationship_id={caller.RelationshipId}
                    AND request_digest={request.RequestDigest}
                """,
                ct
            );
            await commercialTransaction.CommitAsync(ct);
        }
        try
        {
            return await WithSourceAsync<ConversationInferencePermitV1>(
                caller,
                request,
                async (db, current, source) =>
                {
                    if (current.BindingId != binding.BindingId || current.Digest != binding.Digest)
                        throw new ConversationStateConflictException();
                    var currentResolved = await WithResumeContextAsync(
                        db,
                        current,
                        caller,
                        request,
                        ct
                    );
                    if (
                        AgentAdmissionCanonicalizer.Digest(currentResolved)
                        != AgentAdmissionCanonicalizer.Digest(resolved)
                    )
                        throw new ConversationStateConflictException();
                    if (
                        await db
                            .Database.SqlQuery<int>(
                                $"""
                                SELECT 1 AS "Value" FROM business.conversation_model_budget_receipts
                                WHERE tenant_id={caller.TenantId} AND execution_id={request.ExecutionId}
                                """
                            )
                            .AnyAsync(ct)
                    )
                        throw new ConversationStateConflictException();
                    var authority = capability.RequireActive(clock.GetUtcNow());
                    if (authority != reservationAuthority)
                        throw new WhatsAppCapabilityUnavailableException(
                            "ACTIVATION_RECORD_CHANGED"
                        );
                    await SetTenantAsync(db, authority.TenantId, ct);
                    var now = clock.GetUtcNow();
                    if (capability.RequireActive(now) != authority)
                        throw new WhatsAppCapabilityUnavailableException(
                            "ACTIVATION_RECORD_CHANGED"
                        );
                    var day = DateOnly.FromDateTime(now.UtcDateTime);
                    var existing = await db
                        .Database.SqlQuery<ReservationRow>(
                            $"""
                            SELECT reservation_id AS "ReservationId", request_digest AS "RequestDigest", evidence_id AS "EvidenceId",
                                reserved_paise AS "ReservedPaise", expires_at AS "ExpiresAt", state AS "State",
                                actual_paise AS "ActualPaise", input_tokens AS "InputTokens", output_tokens AS "OutputTokens",
                                input_rate_paise AS "InputRate", output_rate_paise AS "OutputRate",
                                environment AS "Environment",settlement_evidence_id AS "SettlementEvidenceId"
                            FROM business.conversation_model_reservations
                            WHERE tenant_id={authority.TenantId} AND customer_tenant_id={caller.TenantId} AND execution_id={request.ExecutionId}
                            """
                        )
                        .SingleOrDefaultAsync(ct);
                    if (existing is not null)
                        throw new ConversationStateConflictException();
                    if (
                        await db
                            .Database.SqlQuery<int>(
                                $"SELECT 1 AS \"Value\" FROM business.conversation_model_reservations WHERE tenant_id={authority.TenantId} AND overrun"
                            )
                            .AnyAsync(ct)
                    )
                        throw new WhatsAppCapabilityUnavailableException(
                            "MODEL_COST_OVERRUN_HALTED"
                        );
                    if (cost > checked((long)(Math.Min(500m, authority.MaximumSpendInr) * 100m)))
                        throw new WhatsAppCapabilityUnavailableException(
                            "COMBINED_DAILY_COST_EXHAUSTED"
                        );
                    var reservation = Guid.NewGuid();
                    var expires = new[]
                    {
                        now.AddSeconds(30),
                        request.OperationalMandate.Deadline,
                        current.Content.GetProperty("expiresAt").GetDateTimeOffset(),
                        authority.ExpiresAt,
                    }.Min();
                    if (expires <= now)
                        throw new ConversationNotAccessibleException();
                    var activationDigest = WhatsAppGuestTrafficEventIdentity.Activation(
                        authority.ActivationReference
                    );
                    var authorityDigest = Convert.ToHexStringLower(
                        SHA256.HashData(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(authority)))
                    );
                    var rateDigest = current.Content.GetProperty("rateDigest").GetString()!;
                    var mandateDigest = AgentAdmissionCanonicalizer.Digest(
                        JsonSerializer.SerializeToElement(request.OperationalMandate, Json)
                    );
                    await _environmentSpend.ReserveAsync(
                        db,
                        authority.Environment,
                        "MODEL",
                        request.ExecutionId,
                        caller.TenantId,
                        activationDigest,
                        request.RequestDigest,
                        reservation,
                        checked((long)cost),
                        checked((long)(Math.Min(500m, authority.MaximumSpendInr) * 100m)),
                        now,
                        ct
                    );
                    await db.Database.ExecuteSqlInterpolatedAsync(
                        $"""
                        INSERT INTO business.conversation_model_reservations
                            (reservation_id,tenant_id,environment,activation_digest,authority_digest,cost_day,
                            customer_tenant_id,relationship_id,execution_id,actor_id,idempotency_key,mandate_digest,request_digest,binding_id,binding_digest,rate_digest,
                            evidence_id,reserved_paise,input_rate_paise,output_rate_paise,state,reserved_at,expires_at)
                        VALUES ({reservation},{authority.TenantId},{authority.Environment},{activationDigest},{authorityDigest},{day},
                            {caller.TenantId},{caller.RelationshipId},{request.ExecutionId},{caller.ActorId},{caller.IdempotencyKey},{mandateDigest},{request.RequestDigest},{current.BindingId},
                            {current.Digest},{rateDigest},{evidence},{cost},{inputRate},{outputRate},'RESERVED',{now},{expires})
                        """,
                        ct
                    );
                    await SetTenantAsync(db, caller.TenantId, ct);
                    await db.Database.ExecuteSqlInterpolatedAsync(
                        $"""
                        INSERT INTO business.conversation_model_budget_receipts
                            (tenant_id,execution_id,reservation_id,budget_tenant_id)
                        VALUES ({caller.TenantId},{request.ExecutionId},{reservation},{authority.TenantId})
                        """,
                        ct
                    );
                    await db.Database.ExecuteSqlInterpolatedAsync(
                        $"""
                        UPDATE business.conversation_inference_spend_coordinators
                        SET operational_reservation_id={reservation},operational_state='RESERVED',
                            updated_at={clock.GetUtcNow()}
                        WHERE tenant_id={caller.TenantId} AND execution_id={request.ExecutionId}
                        """,
                        ct
                    );
                    return new ConversationInferencePermitV1(
                        reservation,
                        commercial.ReservationId,
                        evidence,
                        cost,
                        expires,
                        currentResolved
                    );
                },
                ct
            );
        }
        catch
        {
            var releaseEvidence = await constitutional.RecordAsync(
                caller,
                request,
                "CONVERSATION_MODEL_PRE_DISPATCH_RELEASE",
                commercial.ReservationId,
                new
                {
                    request.ExecutionId,
                    request.RequestDigest,
                    commercial.ReservationId,
                    providerDispatch = false,
                },
                ct
            );
            if (releaseEvidence != Guid.Empty)
            {
                await _offeringUsage.ReleaseAsync(
                    offeringIdentity,
                    commercial.ReservationId,
                    releaseEvidence,
                    ct
                );
                await using var releaseDb = await conversations.CreateDbContextAsync(ct);
                await using var releaseTransaction = await releaseDb.Database.BeginTransactionAsync(
                    ct
                );
                await SetTenantAsync(releaseDb, caller.TenantId, ct);
                await releaseDb.Database.ExecuteSqlInterpolatedAsync(
                    $"""
                    UPDATE business.conversation_inference_spend_coordinators
                    SET wbe_state='RELEASED',operational_state=
                        CASE WHEN operational_reservation_id IS NULL THEN 'RELEASED'
                             ELSE operational_state END,
                        updated_at={clock.GetUtcNow()}
                    WHERE tenant_id={caller.TenantId} AND execution_id={request.ExecutionId}
                    """,
                    ct
                );
                await releaseTransaction.CommitAsync(ct);
            }
            throw;
        }
    }

    public async Task SettleAsync(
        InferenceCaller caller,
        ConversationInferenceRequest request,
        bool release,
        CancellationToken ct
    )
    {
        RequireOriginalIdentity(caller, request);
        if (
            request.ReservationId is not { } reservation
            || request.CommercialReservationId is not { } commercialReservation
            || !release
                && (request.InputTokens is null or < 0 || request.OutputTokens is null or < 0)
            || release && (request.InputTokens is not null || request.OutputTokens is not null)
        )
            throw new ConversationStateConflictException();
        // Financial settlement is not a content-release authority and remains possible after Stop/expiry.
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await SetTenantAsync(db, caller.TenantId, ct);
        var coordinator =
            await db
                .Database.SqlQuery<CoordinatorRow>(
                    $"""
                    SELECT wbe_reservation_id AS "WbeReservationId",
                        operational_reservation_id AS "OperationalReservationId",
                        wbe_state AS "WbeState",operational_state AS "OperationalState"
                    FROM business.conversation_inference_spend_coordinators
                    WHERE tenant_id={caller.TenantId} AND execution_id={request.ExecutionId}
                    FOR UPDATE
                    """
                )
                .SingleOrDefaultAsync(ct)
            ?? throw new ConversationNotAccessibleException();
        if (
            coordinator.WbeReservationId != commercialReservation
            || coordinator.OperationalReservationId != reservation
        )
            throw new ConversationStateConflictException();
        var budgetTenant = await OriginalBudgetTenantAsync(
            db,
            caller.TenantId,
            request.ExecutionId,
            reservation,
            ct
        );
        await SetTenantAsync(db, budgetTenant, ct);
        var lockKey = WhatsAppGuestTrafficEventIdentity.LockKey(budgetTenant);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_advisory_xact_lock(hashtextextended({lockKey},0))",
            ct
        );
        var row = await ReadReservationAsync(db, caller, request, budgetTenant, reservation, ct);
        var actual = release
            ? 0
            : Cost(
                row.InputRate,
                row.OutputRate,
                request.InputTokens!.Value,
                request.OutputTokens!.Value
            );
        if (row.State != "RESERVED")
        {
            if (
                row.State != (release ? "RELEASED" : "SETTLED")
                || row.ActualPaise != actual
                || !release
                    && (
                        row.InputTokens != request.InputTokens
                        || row.OutputTokens != request.OutputTokens
                    )
            )
                throw new ConversationStateConflictException();
            var replayEvidence =
                row.SettlementEvidenceId ?? throw new ConversationStateConflictException();
            var replayIdentity = OfferingIdentity(caller, request, row.EvidenceId);
            if (release)
                await _offeringUsage.ReleaseAsync(
                    replayIdentity,
                    commercialReservation,
                    replayEvidence,
                    ct
                );
            else
                await _offeringUsage.SettleAsync(
                    replayIdentity,
                    commercialReservation,
                    checked(request.InputTokens!.Value + request.OutputTokens!.Value),
                    replayEvidence,
                    ct
                );
            return;
        }
        var evidence = await constitutional.RecordAsync(
            caller,
            request,
            release ? "CONVERSATION_MODEL_PRE_DISPATCH_RELEASE" : "CONVERSATION_MODEL_USAGE",
            reservation,
            new
            {
                request.ExecutionId,
                request.RequestDigest,
                reservation,
                request.InputTokens,
                request.OutputTokens,
                release,
            },
            ct
        );
        if (evidence == Guid.Empty)
            throw new IdentityConstitutionalUnavailableException(
                "Model usage evidence is unavailable."
            );
        var state = release ? "RELEASED" : "SETTLED";
        var overrun =
            !release
            && (
                actual > row.ReservedPaise
                || request.InputTokens > 8192
                || request.OutputTokens > 2048
            );
        await _environmentSpend.SettleAsync(
            db,
            row.Environment,
            "MODEL",
            request.ExecutionId,
            reservation,
            checked((long)actual),
            release,
            evidence,
            clock.GetUtcNow(),
            ct
        );
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            UPDATE business.conversation_model_reservations SET actual_paise={actual},input_tokens={request.InputTokens},
                output_tokens={request.OutputTokens},state={state},overrun={overrun},settlement_evidence_id={evidence},
                settled_at={clock.GetUtcNow()} WHERE reservation_id={reservation} AND tenant_id={budgetTenant}
            """,
            ct
        );
        await SetTenantAsync(db, caller.TenantId, ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            UPDATE business.conversation_inference_spend_coordinators
            SET operational_state={state},updated_at={clock.GetUtcNow()}
            WHERE tenant_id={caller.TenantId} AND execution_id={request.ExecutionId}
            """,
            ct
        );
        await transaction.CommitAsync(ct);
        var offeringIdentity = OfferingIdentity(caller, request, row.EvidenceId);
        var offeringReceipt = release
            ? await _offeringUsage.ReleaseAsync(
                offeringIdentity,
                commercialReservation,
                evidence,
                ct
            )
            : await _offeringUsage.SettleAsync(
                offeringIdentity,
                commercialReservation,
                checked(request.InputTokens!.Value + request.OutputTokens!.Value),
                evidence,
                ct
            );
        await using var completion = await conversations.CreateDbContextAsync(ct);
        await using var completionTransaction = await completion.Database.BeginTransactionAsync(ct);
        await SetTenantAsync(completion, caller.TenantId, ct);
        await completion.Database.ExecuteSqlInterpolatedAsync(
            $"""
            UPDATE business.conversation_inference_spend_coordinators
            SET wbe_state={offeringReceipt.State},updated_at={clock.GetUtcNow()}
            WHERE tenant_id={caller.TenantId} AND execution_id={request.ExecutionId}
            """,
            ct
        );
        await completionTransaction.CommitAsync(ct);
    }

    public async Task<ConversationInferenceReceiptV1> ReconcileAsync(
        InferenceCaller caller,
        ConversationInferenceRequest request,
        CancellationToken ct
    )
    {
        RequireOriginalIdentity(caller, request);
        if (request.InputTokens is not null || request.OutputTokens is not null)
            throw new ConversationStateConflictException();
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await SetTenantAsync(db, caller.TenantId, ct);
        var receipt = await db
            .Database.SqlQuery<BudgetReceiptRow>(
                $"""
                SELECT budget_tenant_id AS "BudgetTenantId", reservation_id AS "ReservationId"
                FROM business.conversation_model_budget_receipts
                WHERE tenant_id={caller.TenantId} AND execution_id={request.ExecutionId}
                """
            )
            .SingleOrDefaultAsync(ct);
        if (receipt is null)
            return new("UNRESOLVED");
        if (request.ReservationId is { } supplied && supplied != receipt.ReservationId)
            throw new ConversationNotAccessibleException();
        await SetTenantAsync(db, receipt.BudgetTenantId, ct);
        var row = await ReadReservationAsync(
            db,
            caller,
            request,
            receipt.BudgetTenantId,
            receipt.ReservationId,
            ct
        );
        await SetTenantAsync(db, caller.TenantId, ct);
        var commercial = await db
            .Database.SqlQuery<Guid?>(
                $"""
                SELECT wbe_reservation_id AS "Value"
                FROM business.conversation_inference_spend_coordinators
                WHERE tenant_id={caller.TenantId} AND execution_id={request.ExecutionId}
                """
            )
            .SingleOrDefaultAsync(ct);
        if (commercial is not { } commercialId)
            return new("UNRESOLVED");
        if (
            request.CommercialReservationId is { } suppliedCommercial
            && suppliedCommercial != commercialId
        )
            throw new ConversationNotAccessibleException();
        var offeringIdentity = OfferingIdentity(caller, request, row.EvidenceId);
        var commercialReceipt = await _offeringUsage.ReconcileAsync(
            offeringIdentity,
            commercialId,
            ct
        );
        if (commercialReceipt is null || commercialReceipt.ReservationId != commercialId)
            return new("UNRESOLVED");
        if (row.State == "SETTLED" && commercialReceipt.State == "RESERVED")
        {
            commercialReceipt = await _offeringUsage.SettleAsync(
                offeringIdentity,
                commercialId,
                checked((row.InputTokens ?? 0) + (row.OutputTokens ?? 0)),
                row.SettlementEvidenceId ?? throw new ConversationStateConflictException(),
                ct
            );
        }
        else if (row.State == "RELEASED" && commercialReceipt.State == "RESERVED")
        {
            commercialReceipt = await _offeringUsage.ReleaseAsync(
                offeringIdentity,
                commercialId,
                row.SettlementEvidenceId ?? throw new ConversationStateConflictException(),
                ct
            );
        }
        if (commercialReceipt.State != row.State)
            return new("UNRESOLVED");
        await SetTenantAsync(db, caller.TenantId, ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            UPDATE business.conversation_inference_spend_coordinators
            SET wbe_state={commercialReceipt.State},updated_at={clock.GetUtcNow()}
            WHERE tenant_id={caller.TenantId} AND execution_id={request.ExecutionId}
            """,
            ct
        );
        await transaction.CommitAsync(ct);
        return new(
            row.State,
            row.ReservationId,
            commercialId,
            row.EvidenceId,
            row.ReservedPaise,
            row.ExpiresAt
        );
    }

    private static async Task<ReservationRow> ReadReservationAsync(
        ConversationStoreDbContext db,
        InferenceCaller caller,
        ConversationInferenceRequest request,
        Guid budgetTenant,
        Guid reservation,
        CancellationToken ct
    ) =>
        await db
            .Database.SqlQuery<ReservationRow>(
                $"""
                SELECT reservation_id AS "ReservationId", request_digest AS "RequestDigest", evidence_id AS "EvidenceId",
                    reserved_paise AS "ReservedPaise", expires_at AS "ExpiresAt", state AS "State",
                    actual_paise AS "ActualPaise", input_tokens AS "InputTokens", output_tokens AS "OutputTokens",
                    input_rate_paise AS "InputRate", output_rate_paise AS "OutputRate",
                    environment AS "Environment",settlement_evidence_id AS "SettlementEvidenceId"
                FROM business.conversation_model_reservations
                WHERE tenant_id={budgetTenant} AND customer_tenant_id={caller.TenantId} AND relationship_id={caller.RelationshipId}
                    AND execution_id={request.ExecutionId} AND reservation_id={reservation} AND request_digest={request.RequestDigest}
                    AND actor_id={caller.ActorId} AND idempotency_key={caller.IdempotencyKey}
                    AND mandate_digest={AgentAdmissionCanonicalizer.Digest(
                    JsonSerializer.SerializeToElement(request.OperationalMandate, Json)
                )}
                FOR UPDATE
                """
            )
            .SingleOrDefaultAsync(ct)
        ?? throw new ConversationNotAccessibleException();

    public async Task<ConversationInferenceContentReadV1> ReadContentAsync(
        InferenceCaller caller,
        ConversationInferenceContentReadRequest request,
        CancellationToken ct
    )
    {
        var original = request.Original;
        var read = request.Permission;
        if (
            read.SchemaVersion != "1.0"
            || caller.ExecutionId != read.ReconciliationAuthorityId
            || caller.ContributionId != read.OriginalMessageId
            || original.ContributionRef != read.OriginalMessageId
            || original.RelationshipRef != caller.RelationshipId
            || original.ReservationId is not null
            || original.InputTokens is not null
            || original.OutputTokens is not null
        )
            throw new ConversationNotAccessibleException();
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await SetTenantAsync(db, caller.TenantId, ct);
        var permission =
            await db
                .ReconciliationAuthorities.AsNoTracking()
                .SingleOrDefaultAsync(
                    row =>
                        row.TenantId == caller.TenantId
                        && row.RelationshipId == caller.RelationshipId
                        && row.AuthorityId == read.ReconciliationAuthorityId
                        && row.RequesterId == caller.ActorId
                        && row.IdempotencyKey == caller.IdempotencyKey,
                    ct
                )
            ?? throw new ConversationNotAccessibleException();
        if (
            permission.Role != caller.Role
            || permission.SourceDigest != read.OriginalSourceDigest
            || permission.ExpiresAt.UtcTicks / 10 != read.PermissionExpiresAt.UtcTicks / 10
            || permission.ExpectedProjectionVersion != read.ExpectedProjectionVersion
        )
            throw new ConversationNotAccessibleException();
        var initialExecution =
            await db
                .Executions.AsNoTracking()
                .SingleOrDefaultAsync(
                    row =>
                        row.TenantId == caller.TenantId
                        && row.ExecutionId == permission.ExecutionId,
                    ct
                )
            ?? throw new ConversationNotAccessibleException();
        if (
            (initialExecution.OriginChannelBindingId is null)
            != (initialExecution.OriginRecipientDigest is null)
        )
            throw new ConversationNotAccessibleException();
        Guid? senderTenant = null;
        if (initialExecution.OriginRecipientDigest is { } originalSender)
        {
            var activation = capability.RequireActive(clock.GetUtcNow());
            senderTenant = activation.TenantId;
            await SetTenantAsync(db, activation.TenantId, ct);
            var senderLock = WhatsAppGuestSession.LockKey(activation.TenantId, originalSender);
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT pg_advisory_xact_lock(hashtextextended({senderLock},0))",
                ct
            );
            await SetTenantAsync(db, caller.TenantId, ct);
        }
        await LockDispatchAsync(db, caller, ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT execution_id FROM business.conversation_executions WHERE tenant_id={caller.TenantId} AND execution_id={permission.ExecutionId} FOR UPDATE",
            ct
        );
        await using var authority = new EmploymentRelationshipDbContext(
            new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                .UseNpgsql(db.Database.GetDbConnection())
                .Options
        );
        await authority.Database.UseTransactionAsync(transaction.GetDbTransaction(), ct);
        await ConversationReconciliationBinding.RequirePermissionAsync(
            db,
            authority,
            runtimeIdentity,
            permission,
            clock.GetUtcNow(),
            ct,
            clock
        );
        var execution = await db
            .Executions.AsNoTracking()
            .SingleAsync(
                row => row.TenantId == caller.TenantId && row.ExecutionId == permission.ExecutionId,
                ct
            );
        if (
            execution.OriginChannelBindingId != initialExecution.OriginChannelBindingId
            || execution.OriginRecipientDigest != initialExecution.OriginRecipientDigest
        )
            throw new ConversationNotAccessibleException();
        var source = await ingestion.GetSourceAsync(
            db,
            authority,
            caller.TenantId,
            permission.ExecutionId,
            ct,
            permission
        );
        if (
            source.Caller.RuntimeExecutionId != original.ExecutionId
            || source.MessageId != original.ContributionRef
            || source.ConversationId != original.ConversationId
            || execution.ProjectionVersion != read.ExpectedProjectionVersion
            || execution.RuntimeSequence != read.AfterSequence
        )
            throw new ConversationNotAccessibleException();
        await runtimeIdentity.RequireCurrentAsync(db, execution, source.Caller.ActorId, ct);
        if (
            !await authority
                .RelationshipParticipants.AsNoTracking()
                .AnyAsync(
                    row =>
                        row.TenantId == caller.TenantId
                        && row.RelationshipId == caller.RelationshipId
                        && row.ParticipantId == source.Caller.ActorId
                        && row.Status == "ACTIVE",
                    ct
                )
        )
            throw new ConversationNotAccessibleException();
        var snapshot = await authority
            .OperationalMandateSnapshots.AsNoTracking()
            .SingleAsync(
                row =>
                    row.TenantId == caller.TenantId
                    && row.RelationshipId == caller.RelationshipId
                    && row.ActorParticipantId == source.Caller.ActorId
                    && row.IdempotencyIdentity == source.IdempotencyKey,
                ct
            );
        using var mandateJson = JsonDocument.Parse(snapshot.MandateJson);
        if (
            AgentAdmissionCanonicalizer.Digest(mandateJson.RootElement)
                != AgentAdmissionCanonicalizer.Digest(
                    JsonSerializer.SerializeToElement(original.OperationalMandate, Json)
                )
            || original.OperationalMandate.ConversationOperation?.Kind != "PROFESSIONAL_RESPONSE"
        )
            throw new ConversationNotAccessibleException();
        var input = await db
            .Messages.AsNoTracking()
            .SingleAsync(
                row => row.TenantId == caller.TenantId && row.MessageId == source.MessageId,
                ct
            );
        var blocks =
            JsonSerializer.Deserialize<List<ConversationTextBlockV1>>(input.ContentJson, Json)
            ?? throw new ConversationStateConflictException();
        if (
            blocks.Count != 1
            || blocks[0].Language != original.InputLanguage
            || Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(blocks[0].Text)))
                != original.InputDigest
        )
            throw new ConversationNotAccessibleException();
        if (
            execution.OriginChannelBindingId is { } binding
            && execution.OriginRecipientDigest is { } sender
        )
        {
            var activation = capability.RequireActive(clock.GetUtcNow());
            if (activation.TenantId != senderTenant)
                throw new ConversationNotAccessibleException();
            await SetTenantAsync(db, activation.TenantId, ct);
            await WhatsAppRelationshipRouting.RequireGuestConsentAsync(
                db,
                activation.TenantId,
                sender,
                clock.GetUtcNow(),
                ct
            );
            var route =
                await WhatsAppRelationshipRouteAuthority.FindAsync(
                    authority,
                    activation.TenantId,
                    sender,
                    ct
                ) ?? throw new ConversationNotAccessibleException();
            await SetTenantAsync(db, caller.TenantId, ct);
            var accepted = await WhatsAppRelationshipRouteAuthority.RequireCurrentAsync(
                authority,
                identity,
                route,
                activation.TenantId,
                sender,
                permission.Issuer,
                activation.Environment,
                clock.GetUtcNow(),
                ct
            );
            if (
                accepted.BindingId != binding
                || accepted.ParticipantId != source.Caller.ActorId
                || accepted.RelationshipId != caller.RelationshipId
                || accepted.ConversationId != original.ConversationId
            )
                throw new ConversationNotAccessibleException();
        }
        await ConversationReconciliationBinding.RequirePermissionAsync(
            db,
            authority,
            runtimeIdentity,
            permission,
            clock.GetUtcNow(),
            ct,
            clock
        );
        return new("READ_ALLOWED");
    }

    private async Task<T> WithSourceAsync<T>(
        InferenceCaller caller,
        ConversationInferenceRequest request,
        Func<ConversationStoreDbContext, BindingRow, ConversationRuntimeSource, Task<T>> operation,
        CancellationToken ct
    )
    {
        RequireOriginalIdentity(caller, request);
        var initialActivation = capability.RequireActive(clock.GetUtcNow());
        await using var db = await conversations.CreateDbContextAsync(ct);
        if (!db.Database.IsNpgsql())
            throw new ConversationExecutionUnavailableException();
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await SetTenantAsync(db, caller.TenantId, ct);
        var execution =
            await db.Executions.SingleOrDefaultAsync(
                row =>
                    row.TenantId == caller.TenantId
                    && row.MessageId
                        == (
                            request.Batch == null
                                ? request.ContributionRef
                                : request.Batch.Sources[0].MessageId
                        )
                    && row.ConversationId == request.ConversationId
                    && row.RelationshipId == caller.RelationshipId,
                ct
            ) ?? throw new ConversationNotAccessibleException();
        await using var authority = new EmploymentRelationshipDbContext(
            new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                .UseNpgsql(db.Database.GetDbConnection())
                .Options
        );
        await authority.Database.UseTransactionAsync(transaction.GetDbTransaction(), ct);
        if (
            execution.OriginRecipientDigest is { } sender
            && execution.OriginChannelBindingId is { } originalBinding
        )
        {
            var activation = capability.RequireActive(clock.GetUtcNow());
            await SetTenantAsync(db, activation.TenantId, ct);
            var senderLock = WhatsAppGuestSession.LockKey(activation.TenantId, sender);
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT pg_advisory_xact_lock(hashtextextended({senderLock},0))",
                ct
            );
            await WhatsAppRelationshipRouting.RequireGuestConsentAsync(
                db,
                activation.TenantId,
                sender,
                clock.GetUtcNow(),
                ct
            );
            var route =
                await WhatsAppRelationshipRouteAuthority.FindAsync(
                    authority,
                    activation.TenantId,
                    sender,
                    ct
                ) ?? throw new ConversationNotAccessibleException();
            await SetTenantAsync(db, caller.TenantId, ct);
            var issuer =
                configuration["IdentityBrokerRead:ActorIssuer"]
                ?? configuration["IdentityEnvironment:Keycloak:Issuer"]
                ?? throw new ConversationExecutionUnavailableException();
            var accepted = await WhatsAppRelationshipRouteAuthority.RequireCurrentAsync(
                authority,
                identity,
                route,
                activation.TenantId,
                sender,
                issuer,
                activation.Environment,
                clock.GetUtcNow(),
                ct
            );
            if (
                accepted.BindingId != originalBinding
                || accepted.RelationshipId != caller.RelationshipId
                || accepted.ParticipantId != caller.ActorId
                || accepted.ConversationId != request.ConversationId
            )
                throw new ConversationNotAccessibleException();
        }
        await LockDispatchAsync(db, caller, ct);
        var source = await ingestion.GetSourceAsync(
            db,
            authority,
            caller.TenantId,
            execution.ExecutionId,
            ct
        );
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT execution_id FROM business.conversation_executions WHERE tenant_id={caller.TenantId} AND execution_id={execution.ExecutionId} FOR UPDATE",
            ct
        );
        await db.Entry(execution).ReloadAsync(ct);
        source = await ingestion.GetSourceAsync(
            db,
            authority,
            caller.TenantId,
            execution.ExecutionId,
            ct
        );
        if (
            request.Batch is null && source.Caller.RuntimeExecutionId != request.ExecutionId
            || source.Caller.ActorId != caller.ActorId
            || source.Caller.ActorRole != caller.Role
            || request.Batch is null && source.IdempotencyKey != caller.IdempotencyKey
            || execution.RuntimeTerminal
            || execution.ProcessingState is "CANCELLED" or "STOPPED"
        )
            throw new ConversationNotAccessibleException();
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT relationship_id FROM business.employment_relationships WHERE tenant_id={caller.TenantId} AND relationship_id={caller.RelationshipId} FOR SHARE",
            ct
        );
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT binding_id FROM business.relationship_participants WHERE tenant_id={caller.TenantId} AND relationship_id={caller.RelationshipId} AND participant_id={caller.ActorId} FOR SHARE",
            ct
        );
        var input = await db.Messages.SingleAsync(
            row => row.TenantId == caller.TenantId && row.MessageId == source.MessageId,
            ct
        );
        var blocks =
            JsonSerializer.Deserialize<List<ConversationTextBlockV1>>(input.ContentJson, Json)
            ?? throw new ConversationStateConflictException();
        if (
            blocks.Count != 1
            || (
                request.Batch is null
                    ? blocks[0].Language != request.InputLanguage
                        || Convert.ToHexStringLower(
                            SHA256.HashData(Encoding.UTF8.GetBytes(blocks[0].Text))
                        ) != request.InputDigest
                    : blocks[0].Text != request.Batch.Sources[0].Text
                        || blocks[0].Language != request.Batch.Sources[0].Language
            )
        )
            throw new ConversationNotAccessibleException();
        var current = await new OperationalMandateResolver(relationships).ValidateExistingAsync(
            authority,
            caller.TenantId,
            caller.ActorId,
            caller.RelationshipId,
            source.IdempotencyKey,
            input.EvidenceRecordId ?? Guid.Empty,
            input.SkillId,
            blocks[0].Text,
            ct
        );
        if (
            current.MandateDigest != request.OperationalMandate.MandateDigest
            || AgentAdmissionCanonicalizer.Digest(JsonSerializer.SerializeToElement(current, Json))
                != AgentAdmissionCanonicalizer.Digest(
                    JsonSerializer.SerializeToElement(request.OperationalMandate, Json)
                )
            || current.ConversationOperation?.Kind != "PROFESSIONAL_RESPONSE"
            || current.Deadline <= clock.GetUtcNow()
            || current.RelationshipLifecycle is not ("TRIAL_ACTIVE" or "ACTIVE")
        )
            throw new ConversationNotAccessibleException();
        if (request.Batch is { } batch)
        {
            var persistedBatch = await db
                .Database.SqlQuery<InferenceBatchBindingRow>(
                    $"""
                    SELECT runtime_execution_id AS "RuntimeExecutionId",
                           source_list_digest AS "SourceListDigest",
                           dispatch_state AS "DispatchState"
                    FROM business.conversation_batch_groups
                    WHERE tenant_id = {caller.TenantId} AND batch_id = {batch.BatchId}
                    FOR SHARE
                    """
                )
                .SingleOrDefaultAsync(ct);
            var persistedMembers = await db
                .Database.SqlQuery<Guid?>(
                    $"""
                    SELECT message_id AS "Value"
                    FROM business.conversation_batch_members
                    WHERE tenant_id = {caller.TenantId} AND batch_id = {batch.BatchId}
                    ORDER BY ordinal
                    """
                )
                .ToListAsync(ct);
            if (
                batch.BatchId != caller.IdempotencyKey
                || batch.BatchId != request.ContributionRef
                || persistedBatch is null
                || persistedBatch.RuntimeExecutionId != request.ExecutionId
                || persistedBatch.SourceListDigest != batch.SourceListDigest
                || persistedBatch.DispatchState is not ("DISPATCHING" or "STARTED" or "UNRESOLVED")
                || persistedMembers.Any(value => value is null)
                || !persistedMembers
                    .Select(value => value!.Value)
                    .SequenceEqual(batch.Sources.Select(value => value.MessageId))
                || batch.Sources.Count is < 2 or > 3
                || batch.Sources[0].MessageId != source.MessageId
                || batch.Sources.Select(value => value.MessageId).Distinct().Count()
                    != batch.Sources.Count
                || batch.Sources.Select(value => value.WorkItemId).Distinct().Count() != 1
                || batch.Sources.Select(value => value.WorkItemRevision).Distinct().Count() != 1
                || batch.Sources.Select(value => value.WorkItemInvocationId).Distinct().Count() != 1
                || batch
                    .Sources.Zip(batch.Sources.Skip(1))
                    .Any(pair => pair.Second.Sequence != pair.First.Sequence + 1)
                || AgentAdmissionCanonicalizer.Digest(
                    JsonSerializer.SerializeToElement(
                        batch.Sources.Select(value => new
                        {
                            value.SchemaVersion,
                            value.MessageId,
                            value.ExecutionId,
                            value.Sequence,
                            value.WorkItemId,
                            value.WorkItemRevision,
                            value.WorkItemInvocationId,
                            value.IdempotencyKey,
                            value.EvidenceId,
                            value.Text,
                            value.Language,
                            value.OperationalMandate.MandateId,
                            value.OperationalMandate.MandateDigest,
                        }),
                        Json
                    )
                ) != batch.SourceListDigest
                || Convert.ToHexStringLower(
                    SHA256.HashData(
                        Encoding.UTF8.GetBytes(
                            string.Join("\n", batch.Sources.Select(value => value.Text))
                        )
                    )
                ) != request.InputDigest
                || batch.Sources.Any(value => value.Language != request.InputLanguage)
            )
                throw new ConversationNotAccessibleException();
            for (var index = 0; index < batch.Sources.Count; index++)
            {
                var member = batch.Sources[index];
                var canonical = await db.Messages.SingleAsync(
                    row => row.TenantId == caller.TenantId && row.MessageId == member.MessageId,
                    ct
                );
                var memberBlocks =
                    JsonSerializer.Deserialize<List<ConversationTextBlockV1>>(
                        canonical.ContentJson,
                        Json
                    ) ?? throw new ConversationStateConflictException();
                if (
                    canonical.Sequence != member.Sequence
                    || memberBlocks.Count != 1
                    || memberBlocks[0].Text != member.Text
                    || memberBlocks[0].Language != member.Language
                    || canonical.EvidenceRecordId != member.EvidenceId
                )
                    throw new ConversationNotAccessibleException();
                var memberMandate = await new OperationalMandateResolver(
                    relationships
                ).ValidateExistingAsync(
                    authority,
                    caller.TenantId,
                    caller.ActorId,
                    caller.RelationshipId,
                    member.IdempotencyKey,
                    member.EvidenceId,
                    canonical.SkillId,
                    member.Text,
                    ct
                );
                if (
                    memberMandate.MandateDigest != member.OperationalMandate.MandateDigest
                    || memberMandate.Deadline <= clock.GetUtcNow()
                    || memberMandate.Stopped
                )
                    throw new ConversationNotAccessibleException();
            }
        }
        var relationship = await authority.EmploymentRelationships.SingleAsync(
            row => row.TenantId == caller.TenantId && row.RelationshipId == caller.RelationshipId,
            ct
        );
        var binding =
            await db
                .Database.SqlQuery<BindingRow>(
                    $"""
                    SELECT binding_id AS "BindingId",binding_digest AS "Digest",binding_json AS "BindingJson",
                        approved_evidence_id AS "ApprovedEvidenceId"
                    FROM business.lock_conversation_inference_bindings({caller.TenantId}, {caller.RelationshipId})
                    WHERE tenant_id={caller.TenantId}
                        AND relationship_id={caller.RelationshipId} AND accepted_contract_id={relationship.AcceptedContractId}
                        AND configuration_revision={current.ConfigurationRevision}
                        AND admission_id={relationship.ProfessionalAdmissionId} AND admission_revision={current.AdmissionRevision}
                        AND professional_type={current.ProfessionalType} AND professional_version={current.ProfessionalVersion}
                        AND skill_id={current.SkillId} AND skill_version={current.SkillVersion}
                        AND prompt_ref={current.ConversationOperation.PromptPolicy.Ref}
                        AND prompt_version={current.PromptVersion} AND prompt_digest={current.PromptDigest}
                        AND model_policy_ref={current.ConversationOperation.ModelPolicy.Ref}
                        AND model_policy_version={current.ConversationOperation.ModelPolicy.Version}
                        AND model_policy_digest={current.ConversationOperation.ModelPolicy.Digest} AND active
                    """
                )
                .SingleOrDefaultAsync(ct)
            ?? throw new ConversationExecutionUnavailableException();
        if (
            binding.ApprovedEvidenceId == Guid.Empty
            || AgentAdmissionCanonicalizer.Digest(binding.Content) != binding.Digest
            || binding.Content.GetProperty("bindingId").GetGuid() != binding.BindingId
            || binding.Content.GetProperty("promptDigest").GetString() != current.PromptDigest
            || binding.Content.GetProperty("modelPolicyDigest").GetString()
                != current.ConversationOperation.ModelPolicy.Digest
            || binding.Content.GetProperty("expiresAt").GetDateTimeOffset() <= clock.GetUtcNow()
        )
            throw new ConversationStateConflictException();
        var providerName = binding.Content.GetProperty("providerId").GetString()!;
        var provider =
            await db
                .Database.SqlQuery<ProviderRow>(
                    $"""
                    SELECT id AS "Id", provider_name AS "ProviderName", auth_method AS "AuthMethod", mcp_server_url AS "Endpoint",
                        provider_identity_uri AS "IdentityUri", scope_set AS "Scopes"
                    FROM business.provider_configs WHERE provider_name={providerName} AND active
                        AND (tenant_id={caller.TenantId} OR tenant_id IS NULL)
                    ORDER BY tenant_id NULLS LAST LIMIT 1 FOR SHARE
                    """
                )
                .SingleOrDefaultAsync(ct)
            ?? throw new ConversationExecutionUnavailableException();
        var configurationDigest = AgentAdmissionCanonicalizer.Digest(
            JsonSerializer.SerializeToElement(
                new
                {
                    provider.Id,
                    provider.ProviderName,
                    provider.AuthMethod,
                    provider.Endpoint,
                    provider.IdentityUri,
                    scopes = provider.Scopes.Order(StringComparer.Ordinal).ToArray(),
                },
                Json
            )
        );
        if (
            provider.AuthMethod != "INSTITUTIONAL_MTLS"
            || provider.Endpoint != binding.Content.GetProperty("endpoint").GetString()
            || provider.IdentityUri
                != binding.Content.GetProperty("providerIdentityUri").GetString()
            || configurationDigest != binding.Content.GetProperty("configurationDigest").GetString()
            || !provider.Scopes.Contains(
                current.ConversationOperation.GovernedAction,
                StringComparer.Ordinal
            )
        )
            throw new ConversationNotAccessibleException();
        var result = await operation(db, binding, source);
        await SetTenantAsync(db, caller.TenantId, ct);
        var final = await ingestion.GetSourceAsync(
            db,
            authority,
            caller.TenantId,
            execution.ExecutionId,
            ct
        );
        var finalMandate = await new OperationalMandateResolver(
            relationships
        ).ValidateExistingAsync(
            authority,
            caller.TenantId,
            caller.ActorId,
            caller.RelationshipId,
            source.IdempotencyKey,
            input.EvidenceRecordId ?? Guid.Empty,
            input.SkillId,
            blocks[0].Text,
            ct
        );
        if (
            final != source
            || current.Deadline <= clock.GetUtcNow()
            || finalMandate.MandateDigest != current.MandateDigest
            || capability.RequireActive(clock.GetUtcNow()) != initialActivation
        )
            throw new ConversationNotAccessibleException();
        await transaction.CommitAsync(ct);
        return result;
    }

    private static void RequireOriginalIdentity(
        InferenceCaller caller,
        ConversationInferenceRequest request
    )
    {
        if (
            request.ExecutionId != caller.ExecutionId
            || request.ContributionRef != caller.ContributionId
            || request.RelationshipRef != caller.RelationshipId
            || (
                request.Batch is null
                    ? request.OperationalMandate.IdempotencyIdentity != caller.IdempotencyKey
                    : request.Batch.BatchId != caller.IdempotencyKey
                        || request.Batch.BatchId != request.ContributionRef
            )
            || request.RequestDigest.Length != 64
            || request.InputDigest.Length != 64
        )
            throw new ConversationNotAccessibleException();
    }

    private sealed class InferenceBatchBindingRow
    {
        public Guid RuntimeExecutionId { get; init; }
        public string SourceListDigest { get; init; } = string.Empty;
        public string DispatchState { get; init; } = string.Empty;
    }

    internal static async Task<Guid> OriginalBudgetTenantAsync(
        ConversationStoreDbContext db,
        Guid customerTenant,
        Guid execution,
        Guid reservation,
        CancellationToken ct
    )
    {
        await SetTenantAsync(db, customerTenant, ct);
        var receipt = await db
            .Database.SqlQuery<Guid>(
                $"""
                SELECT budget_tenant_id AS "Value" FROM business.conversation_model_budget_receipts
                WHERE tenant_id={customerTenant} AND execution_id={execution} AND reservation_id={reservation}
                """
            )
            .SingleOrDefaultAsync(ct);
        return receipt != Guid.Empty ? receipt : throw new ConversationNotAccessibleException();
    }

    internal static decimal Cost(
        long inputRate,
        long outputRate,
        long inputTokens,
        long outputTokens
    )
    {
        if (inputRate < 0 || outputRate < 0 || inputTokens < 0 || outputTokens < 0)
            throw new ConversationStateConflictException();
        return checked(
            decimal.Ceiling((decimal)inputRate * inputTokens / 1000000m)
            + decimal.Ceiling((decimal)outputRate * outputTokens / 1000000m)
        );
    }

    internal static async Task<decimal> CommittedModelSpendAsync(
        ConversationStoreDbContext db,
        Guid tenant,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        if (
            await db
                .Database.SqlQuery<int>(
                    $"SELECT 1 AS \"Value\" FROM business.conversation_model_reservations WHERE tenant_id={tenant} AND overrun"
                )
                .AnyAsync(ct)
        )
            throw new WhatsAppCapabilityUnavailableException("MODEL_COST_OVERRUN_HALTED");
        return await db
            .Database.SqlQuery<decimal>(
                $"""
                SELECT coalesce(sum(CASE WHEN state='RESERVED' THEN reserved_paise ELSE actual_paise END),0)::numeric AS "Value"
                FROM business.conversation_model_reservations
                WHERE tenant_id={tenant}
                  AND (state='RESERVED' OR settled_at >= {now.AddHours(-24)})
                """
            )
            .SingleAsync(ct);
    }

    private static Task SetTenantAsync(
        ConversationStoreDbContext db,
        Guid tenant,
        CancellationToken ct
    ) =>
        db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT set_config('app.current_tenant_id',{tenant.ToString("D")},true)",
            ct
        );

    private static async Task LockDispatchAsync(
        ConversationStoreDbContext db,
        InferenceCaller caller,
        CancellationToken ct
    )
    {
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT ai_runtime.lock_employment_dispatch({caller.TenantId},{caller.RelationshipId.ToString("D")})",
            ct
        );
        if (
            await db
                .Database.SqlQuery<int>(
                    $"SELECT 1 AS \"Value\" FROM constitutional.employment_dispatch_stops WHERE tenant_id={caller.TenantId} AND relationship_ref={caller.RelationshipId.ToString("D")}"
                )
                .AnyAsync(ct)
        )
            throw new ConversationStoppedException();
    }

    private static async Task<JsonElement> WithResumeContextAsync(
        ConversationStoreDbContext db,
        BindingRow binding,
        InferenceCaller caller,
        ConversationInferenceRequest request,
        CancellationToken ct
    )
    {
        var inputMessageId = request.Batch?.Sources[0].MessageId ?? request.ContributionRef;
        var input = await db
            .Messages.AsNoTracking()
            .SingleAsync(
                row => row.TenantId == caller.TenantId && row.MessageId == inputMessageId,
                ct
            );
        var context = await ConversationResumeContextReader.ReadAsync(db, input, ct);
        var payload =
            JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(
                binding.Content.GetRawText(),
                Json
            ) ?? throw new ConversationStateConflictException();
        payload["conversationContext"] = context;
        return JsonSerializer.SerializeToElement(payload, Json);
    }

    private static OfferingUsageIdentity OfferingIdentity(
        InferenceCaller caller,
        ConversationInferenceRequest request,
        Guid ownerEvidenceId
    ) =>
        new(
            caller.TenantId,
            caller.RelationshipId,
            caller.ActorId,
            request.OperationalMandate.AgentInstanceId,
            request.OperationalMandate.ProfessionalType,
            request.OperationalMandate.ProfessionalVersion,
            request.OperationalMandate.SkillId,
            request.OperationalMandate.SkillVersion,
            request.Batch?.Sources[0].WorkItemId ?? request.ExecutionId,
            request.ExecutionId,
            "MODEL_GENERATION",
            caller.IdempotencyKey,
            request.RequestDigest,
            ownerEvidenceId
        );

    private async Task<Guid?> ExistingCoordinatorEvidenceAsync(
        InferenceCaller caller,
        ConversationInferenceRequest request,
        CancellationToken ct
    )
    {
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await SetTenantAsync(db, caller.TenantId, ct);
        return await db
            .Database.SqlQuery<Guid?>(
                $"""
                SELECT owner_evidence_id AS "Value"
                FROM business.conversation_inference_spend_coordinators
                WHERE tenant_id={caller.TenantId}
                  AND relationship_id={caller.RelationshipId}
                  AND execution_id={request.ExecutionId}
                  AND request_digest={request.RequestDigest}
                """
            )
            .SingleOrDefaultAsync(ct);
    }

    private sealed class BindingRow
    {
        private static readonly HashSet<string> Fields = new(StringComparer.Ordinal)
        {
            "bindingId",
            "providerId",
            "providerIdentityUri",
            "adapter",
            "endpoint",
            "model",
            "modelDigest",
            "tokenizerDigest",
            "tokenizerVersion",
            "region",
            "tier",
            "languages",
            "domains",
            "planTiers",
            "resolvedPlanTier",
            "mandatoryTiers",
            "residencyRegions",
            "institutionalBoundary",
            "configurationDigest",
            "rateDigest",
            "inputPaisePerMillion",
            "outputPaisePerMillion",
            "systemPrompt",
            "promptVersion",
            "promptDigest",
            "promptWrapper",
            "modelPolicyDigest",
            "expiresAt",
        };
        private JsonElement? _content;
        public Guid BindingId { get; init; }
        public Guid ApprovedEvidenceId { get; init; }
        public string Digest { get; init; } = "";
        public string BindingJson { get; init; } = "{}";
        public JsonElement Content
        {
            get
            {
                if (_content is { } cached)
                    return cached;
                using var document = JsonDocument.Parse(BindingJson);
                var content = document.RootElement;
                RuntimeEventStreamReader.ValidateUniqueProperties(content);
                if (
                    content.EnumerateObject().Count() != Fields.Count
                    || content.EnumerateObject().Any(property => !Fields.Contains(property.Name))
                )
                    throw new ConversationStateConflictException();
                _content = content.Clone();
                return _content.Value;
            }
        }
    }

    private sealed class ReservationRow
    {
        public Guid ReservationId { get; init; }
        public string RequestDigest { get; init; } = "";
        public Guid EvidenceId { get; init; }
        public long ReservedPaise { get; init; }
        public DateTimeOffset ExpiresAt { get; init; }
        public string State { get; init; } = "";
        public decimal? ActualPaise { get; init; }
        public long? InputTokens { get; init; }
        public long? OutputTokens { get; init; }
        public long InputRate { get; init; }
        public long OutputRate { get; init; }
        public string Environment { get; init; } = "";
        public Guid? SettlementEvidenceId { get; init; }
    }

    private sealed class BudgetReceiptRow
    {
        public Guid BudgetTenantId { get; init; }
        public Guid ReservationId { get; init; }
    }

    private sealed class CoordinatorRow
    {
        public Guid? WbeReservationId { get; init; }
        public Guid? OperationalReservationId { get; init; }
        public string WbeState { get; init; } = "";
        public string OperationalState { get; init; } = "";
    }

    private sealed class ProviderRow
    {
        public Guid Id { get; init; }
        public string ProviderName { get; init; } = "";
        public string AuthMethod { get; init; } = "";
        public string? Endpoint { get; init; }
        public string? IdentityUri { get; init; }
        public string[] Scopes { get; init; } = [];
    }
}
