// Implements: architecture/reference/components/conversation-core.md section 4.2.
// constitutional_basis: C-023, C-026, C-059, C-063; ADR-046
using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

[JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
public sealed record ReconcileConversationExecutionRequestV1(
    string SchemaVersion,
    Guid ExpectedMessageId,
    [property: JsonRequired, JsonNumberHandling(JsonNumberHandling.Strict)]
        long ExpectedProjectionVersion
);

public sealed record ConversationReconciliationOutcomeV1(
    string SchemaVersion,
    Guid ExecutionId,
    string State,
    string NextAction,
    long ProjectionVersion,
    bool Replayed
);

public sealed record ConversationOriginalSourceV1(
    string SchemaVersion,
    Guid TenantId,
    Guid RelationshipId,
    Guid ConversationId,
    Guid ExecutionId,
    Guid OriginalMessageId,
    Guid OriginalActorId,
    Guid MandateId,
    string MandateDigest
);

public sealed record RuntimeReconciliationRequestV1(
    string SchemaVersion,
    Guid OriginalMessageId,
    string OriginalSourceDigest,
    long AfterSequence,
    Guid ReconciliationAuthorityId,
    DateTimeOffset PermissionExpiresAt,
    long ExpectedProjectionVersion
);

[JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
public sealed record RuntimeReconciliationResultV1(
    string SchemaVersion,
    Guid ConversationId,
    Guid ExecutionId,
    Guid OriginalMessageId,
    string OriginalSourceDigest,
    Guid ReconciliationAuthorityId,
    string State,
    IReadOnlyList<RuntimeExecutionEventV1> Events,
    string NextAction,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        string? OriginalRequestDigest = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        string? ResultDigest = null
);

public interface IConversationExecutionReconciliationGateway
{
    Task<RuntimeReconciliationResultV1> ReadTerminalAsync(
        ConversationOriginalSourceV1 source,
        ConversationReconciliationAuthority authority,
        long afterSequence,
        CancellationToken cancellationToken
    );
}

public static class ConversationReconciliationBinding
{
    public static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    public static string Digest<T>(T value) =>
        AgentAdmissionCanonicalizer.Digest(JsonSerializer.SerializeToElement(value, Json));

    public static async Task<(
        ConversationRuntimeSource Source,
        ConversationOriginalSourceV1 Original
    )> SourceAsync(
        ConversationStoreDbContext db,
        EmploymentRelationshipDbContext relationships,
        ConversationExecution execution,
        string environment,
        CancellationToken ct
    )
    {
        var input =
            await db
                .Messages.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == execution.TenantId
                        && value.MessageId == execution.MessageId
                        && value.RelationshipId == execution.RelationshipId
                        && value.ConversationId == execution.ConversationId
                        && value.Environment == environment
                        && value.Actor == "CUSTOMER"
                        && value.SchemaVersion == "1.0",
                    ct
                )
            ?? throw new ConversationStateConflictException();
        var send =
            await db
                .IdempotencyOutcomes.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == execution.TenantId
                        && value.RelationshipId == execution.RelationshipId
                        && value.ExecutionId == execution.ExecutionId
                        && value.MessageId == execution.MessageId
                        && value.OperationFamily == "SEND",
                    ct
                )
            ?? throw new ConversationStateConflictException();
        var snapshot =
            await relationships
                .OperationalMandateSnapshots.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == execution.TenantId
                        && value.RelationshipId == execution.RelationshipId
                        && value.ActorParticipantId == send.ActorParticipantId
                        && value.IdempotencyIdentity == send.IdempotencyKey,
                    ct
                )
            ?? throw new ConversationExecutionUnavailableException();
        OperationalMandateV1 mandate;
        try
        {
            mandate =
                JsonSerializer.Deserialize<OperationalMandateV1>(snapshot.MandateJson, Json)
                ?? throw new ConversationStateConflictException();
            using var content = JsonDocument.Parse(snapshot.MandateJson);
            RuntimeEventStreamReader.ValidateUniqueProperties(content.RootElement);
            var bound = content
                .RootElement.EnumerateObject()
                .Where(value => value.Name != "mandateDigest")
                .ToDictionary(value => value.Name, value => value.Value);
            if (
                Digest(bound) != snapshot.MandateDigest
                || mandate.MandateDigest != snapshot.MandateDigest
            )
                throw new ConversationStateConflictException();
        }
        catch (JsonException)
        {
            throw new ConversationStateConflictException();
        }
        if (
            mandate.MandateId != snapshot.MandateId
            || mandate.TenantId != execution.TenantId
            || mandate.RelationshipId != execution.RelationshipId
            || mandate.ActorId != send.ActorParticipantId
            || mandate.IdempotencyIdentity != send.IdempotencyKey
            || string.IsNullOrWhiteSpace(mandate.ActorRole)
            || input.EvidenceRecordId is not { } evidence
            || evidence == Guid.Empty
        )
            throw new ConversationStateConflictException();
        var runtimeId = ConversationExecutionIdentity.Create(
            execution.TenantId,
            execution.RelationshipId,
            send.ActorParticipantId,
            execution.ConversationId,
            send.IdempotencyKey
        );
        var original = new ConversationOriginalSourceV1(
            "1.0",
            execution.TenantId,
            execution.RelationshipId,
            execution.ConversationId,
            runtimeId,
            execution.MessageId,
            send.ActorParticipantId,
            snapshot.MandateId,
            snapshot.MandateDigest
        );
        var source = new ConversationRuntimeSource(
            execution.TenantId,
            execution.RelationshipId,
            execution.ExecutionId,
            execution.ConversationId,
            execution.MessageId,
            send.IdempotencyKey,
            new(
                execution.TenantId,
                execution.RelationshipId,
                send.ActorParticipantId,
                mandate.ActorRole,
                $"ce-decision:{evidence:D}",
                runtimeId
            ),
            execution.RuntimeSequence,
            execution.OriginChannelBindingId,
            execution.OriginRecipientDigest
        );
        return (source, original);
    }

    public static async Task RequirePermissionAsync(
        ConversationStoreDbContext db,
        EmploymentRelationshipDbContext relationships,
        ConversationRuntimeIdentityAuthority identity,
        ConversationReconciliationAuthority permission,
        DateTimeOffset now,
        CancellationToken ct,
        TimeProvider? timeProvider = null
    )
    {
        if (
            permission.EvidenceId == Guid.Empty
            || permission.ExpiresAt <= now
            || permission.CreatedAt > now
            || permission.ExpiresAt > permission.CreatedAt.AddMinutes(5)
        )
            throw new ConversationNotAccessibleException();
        var membership = await identity.ResolveAsync(
            db,
            permission.TenantId,
            permission.RequesterId,
            ct
        );
        if (
            membership.Issuer != permission.Issuer
            || membership.AccountId != permission.AccountId
            || membership.MembershipId != permission.MembershipId
            || membership.Role != permission.Role
        )
            throw new ConversationNotAccessibleException();
        if (db.Database.IsRelational())
        {
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT relationship_id FROM business.employment_relationships WHERE tenant_id = {permission.TenantId} AND relationship_id = {permission.RelationshipId} FOR SHARE",
                ct
            );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT binding_id FROM business.relationship_participants WHERE tenant_id = {permission.TenantId} AND relationship_id = {permission.RelationshipId} AND participant_id = {permission.RequesterId} FOR SHARE",
                ct
            );
        }
        var relationship =
            await relationships
                .EmploymentRelationships.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == permission.TenantId
                        && value.RelationshipId == permission.RelationshipId,
                    ct
                )
            ?? throw new ConversationNotAccessibleException();
        if (
            relationship.State == EmploymentRelationshipState.StoppedEmergency
            || relationship.StoppedAt is not null
            || await db.EmergencyStopLatches.AnyAsync(
                value =>
                    value.TenantId == permission.TenantId
                    && value.RelationshipId == permission.RelationshipId
                    && (value.State == "LATCHED" || value.State == "EVIDENCE_CONFIRMED"),
                ct
            )
        )
            throw new ConversationStoppedException();
        if (
            relationship.AuthoritySnapshotId != permission.DecisionSpaceSnapshotId
            || !await relationships
                .DecisionSpaceSnapshots.AsNoTracking()
                .AnyAsync(
                    value =>
                        value.TenantId == permission.TenantId
                        && value.RelationshipId == permission.RelationshipId
                        && value.SnapshotId == permission.DecisionSpaceSnapshotId
                        && value.Version == permission.DecisionSpaceVersion,
                    ct
                )
            || !await relationships
                .RelationshipParticipants.AsNoTracking()
                .AnyAsync(
                    value =>
                        value.TenantId == permission.TenantId
                        && value.RelationshipId == permission.RelationshipId
                        && value.ParticipantId == permission.RequesterId
                        && value.Status == "ACTIVE",
                    ct
                )
        )
            throw new ConversationNotAccessibleException();
        if (permission.ExpiresAt <= (timeProvider ?? TimeProvider.System).GetUtcNow())
            throw new ConversationNotAccessibleException();
    }
}

public sealed class ConversationReconciliationService(
    IDbContextFactory<ConversationStoreDbContext> conversations,
    IDbContextFactory<EmploymentRelationshipDbContext> relationships,
    IRelationshipConstitutionalGateway constitutional,
    IConversationExecutionReconciliationGateway runtime,
    ConversationRuntimeIdentityAuthority identity,
    ConversationRuntimeEventIngestion ingestion,
    Microsoft.Extensions.Options.IOptions<Wc120ConversationOptions> options,
    TimeProvider clock
)
{
    private static readonly ActivitySource Activities = new(
        "waooaw.business-platform.conversation"
    );

    public async Task<ConversationReconciliationOutcomeV1> ReconcileAsync(
        Guid tenant,
        Guid requester,
        Guid relationshipId,
        Guid executionId,
        Guid key,
        Guid correlation,
        ReconcileConversationExecutionRequestV1 request,
        CancellationToken ct
    )
    {
        using var activity = Activities.StartActivity("bp.conversation.reconcile");
        if (
            request.SchemaVersion != "1.0"
            || request.ExpectedMessageId == Guid.Empty
            || request.ExpectedProjectionVersion < 0
            || key == Guid.Empty
            || correlation == Guid.Empty
        )
            throw new ConversationRequestException(
                "A closed versioned recovery request and UUID headers are required."
            );
        var requestDigest = ConversationReconciliationBinding.Digest(
            new
            {
                request,
                tenant,
                requester,
                relationshipId,
                executionId,
            }
        );
        var admitted = await AdmitAsync(
            tenant,
            requester,
            relationshipId,
            executionId,
            key,
            correlation,
            request,
            requestDigest,
            ct
        );
        if (admitted.Permission.ResponseJson is { } prior)
            return (
                JsonSerializer.Deserialize<ConversationReconciliationOutcomeV1>(
                    prior,
                    ConversationReconciliationBinding.Json
                ) ?? throw new ConversationStateConflictException()
            ) with
            {
                Replayed = true,
            };
        if (!options.Value.RuntimeEventIngestionEnabled)
            throw new ConversationExecutionUnavailableException();
        var result = await runtime.ReadTerminalAsync(
            admitted.Original,
            admitted.Permission,
            admitted.Source.AfterSequence,
            ct
        );
        try
        {
            HttpConversationExecutionGateway.ValidateReconciliationShape(
                result,
                admitted.Original,
                admitted.Permission,
                admitted.Source.AfterSequence
            );
        }
        catch (JsonException)
        {
            throw new ConversationExecutionUnavailableException();
        }
        if (result.State == "UNKNOWN")
        {
            await RecheckAsync(admitted.Permission, ct, requireProjection: true);
            return new(
                "1.0",
                executionId,
                "UNRESOLVED",
                "OPERATOR_RECONCILIATION_REQUIRED",
                request.ExpectedProjectionVersion,
                false
            );
        }
        try
        {
            return await ingestion.ApplyReconciliationAsync(
                admitted.Source,
                admitted.Permission.AuthorityId,
                result,
                ct
            );
        }
        catch (JsonException)
        {
            throw new ConversationExecutionUnavailableException();
        }
    }

    private async Task<(
        ConversationReconciliationAuthority Permission,
        ConversationRuntimeSource Source,
        ConversationOriginalSourceV1 Original
    )> AdmitAsync(
        Guid tenant,
        Guid requester,
        Guid relationshipId,
        Guid executionId,
        Guid key,
        Guid correlation,
        ReconcileConversationExecutionRequestV1 request,
        string requestDigest,
        CancellationToken ct
    )
    {
        // CE is called only after source/access resolution and outside the projection/Stop transaction.
        await using var initial = await conversations.CreateDbContextAsync(ct);
        await using var initialRelationships = await relationships.CreateDbContextAsync(ct);
        var execution =
            await initial
                .Executions.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == tenant
                        && value.RelationshipId == relationshipId
                        && value.ExecutionId == executionId,
                    ct
                )
            ?? throw new ConversationNotAccessibleException();
        var relationship =
            await initialRelationships
                .EmploymentRelationships.AsNoTracking()
                .SingleOrDefaultAsync(
                    value => value.TenantId == tenant && value.RelationshipId == relationshipId,
                    ct
                )
            ?? throw new ConversationNotAccessibleException();
        if (
            !await initialRelationships
                .RelationshipParticipants.AsNoTracking()
                .AnyAsync(
                    value =>
                        value.TenantId == tenant
                        && value.RelationshipId == relationshipId
                        && value.ParticipantId == requester
                        && value.Status == "ACTIVE",
                    ct
                )
        )
            throw new ConversationNotAccessibleException();
        var membership = await identity.ResolveAsync(initial, tenant, requester, ct);
        var decision =
            await initialRelationships
                .DecisionSpaceSnapshots.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == tenant
                        && value.RelationshipId == relationshipId
                        && value.SnapshotId == relationship.AuthoritySnapshotId,
                    ct
                )
            ?? throw new ConversationNotAccessibleException();
        var bound = await ConversationReconciliationBinding.SourceAsync(
            initial,
            initialRelationships,
            execution,
            options.Value.Environment,
            ct
        );
        var existing = await initial
            .ReconciliationAuthorities.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenant
                    && value.ExecutionId == executionId
                    && value.RequesterId == requester
                    && value.IdempotencyKey == key,
                ct
            );
        if (existing is not null)
        {
            if (existing.RequestDigest != requestDigest)
                throw new ConversationIdempotencyConflictException();
            await RecheckAsync(existing, ct);
            if (existing.SourceDigest != ConversationReconciliationBinding.Digest(bound.Original))
                throw new ConversationStateConflictException();
            return (existing, bound.Source, bound.Original);
        }
        if (
            execution.MessageId != request.ExpectedMessageId
            || execution.ProjectionVersion != request.ExpectedProjectionVersion
        )
            throw new ConversationStateConflictException();
        var sourceDigest = ConversationReconciliationBinding.Digest(bound.Original);
        Guid evidence;
        try
        {
            evidence = await constitutional.AuthorizeAndRecordAsync(
                tenant,
                relationshipId,
                relationship.ProfessionalType,
                "READ_EXISTING_RUNTIME_RESULT",
                correlation,
                new
                {
                    requesterId = requester,
                    executionId,
                    sourceDigest,
                    requestDigest,
                    expectedProjectionVersion = request.ExpectedProjectionVersion,
                },
                decision.Version,
                ct
            );
        }
        catch (Exception failure)
            when (failure is Grpc.Core.RpcException or InvalidOperationException
                || failure is OperationCanceledException && !ct.IsCancellationRequested
            )
        {
            throw new ConversationExecutionUnavailableException();
        }
        if (evidence == Guid.Empty)
            throw new ConversationExecutionUnavailableException();
        var now = clock.GetUtcNow();
        var permission = new ConversationReconciliationAuthority
        {
            AuthorityId = Guid.NewGuid(),
            TenantId = tenant,
            RelationshipId = relationshipId,
            ExecutionId = executionId,
            RequesterId = requester,
            Issuer = membership.Issuer,
            AccountId = membership.AccountId,
            MembershipId = membership.MembershipId,
            Role = membership.Role,
            DecisionSpaceSnapshotId = decision.SnapshotId,
            DecisionSpaceVersion = decision.Version,
            EvidenceId = evidence,
            SourceDigest = sourceDigest,
            IdempotencyKey = key,
            RequestDigest = requestDigest,
            ExpectedProjectionVersion = request.ExpectedProjectionVersion,
            CreatedAt = now,
            ExpiresAt = now.AddMinutes(5),
        };
        await using var db = await conversations.CreateDbContextAsync(ct);
        if (!db.Database.IsRelational())
            throw new ConversationExecutionUnavailableException();
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT ai_runtime.lock_employment_dispatch({tenant}, {relationshipId.ToString("D")})",
            ct
        );
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT execution_id FROM business.conversation_executions WHERE tenant_id = {tenant} AND execution_id = {executionId} FOR UPDATE",
            ct
        );
        await using var currentRelationships = new EmploymentRelationshipDbContext(
            new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                .UseNpgsql(db.Database.GetDbConnection())
                .Options
        );
        await currentRelationships.Database.UseTransactionAsync(transaction.GetDbTransaction(), ct);
        await ConversationReconciliationBinding.RequirePermissionAsync(
            db,
            currentRelationships,
            identity,
            permission,
            clock.GetUtcNow(),
            ct,
            clock
        );
        var current = await db
            .Executions.AsNoTracking()
            .SingleAsync(value => value.TenantId == tenant && value.ExecutionId == executionId, ct);
        var currentSource = await ConversationReconciliationBinding.SourceAsync(
            db,
            currentRelationships,
            current,
            options.Value.Environment,
            ct
        );
        if (
            current.MessageId != request.ExpectedMessageId
            || current.ProjectionVersion != request.ExpectedProjectionVersion
            || ConversationReconciliationBinding.Digest(currentSource.Original) != sourceDigest
        )
            throw new ConversationStateConflictException();
        existing = await db.ReconciliationAuthorities.SingleOrDefaultAsync(
            value =>
                value.TenantId == tenant
                && value.ExecutionId == executionId
                && value.RequesterId == requester
                && value.IdempotencyKey == key,
            ct
        );
        if (existing is not null)
        {
            if (existing.RequestDigest != requestDigest)
                throw new ConversationIdempotencyConflictException();
            await ConversationReconciliationBinding.RequirePermissionAsync(
                db,
                currentRelationships,
                identity,
                existing,
                clock.GetUtcNow(),
                ct,
                clock
            );
            permission = existing;
        }
        else
        {
            db.ReconciliationAuthorities.Add(permission);
            await db.SaveChangesAsync(ct);
        }
        if (permission.ExpiresAt <= clock.GetUtcNow())
            throw new ConversationNotAccessibleException();
        await transaction.CommitAsync(ct);
        return (permission, currentSource.Source, currentSource.Original);
    }

    private async Task RecheckAsync(
        ConversationReconciliationAuthority permission,
        CancellationToken ct,
        bool requireProjection = false
    )
    {
        await using var db = await conversations.CreateDbContextAsync(ct);
        if (!db.Database.IsRelational())
            throw new ConversationExecutionUnavailableException();
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT ai_runtime.lock_employment_dispatch({permission.TenantId}, {permission.RelationshipId.ToString("D")})",
            ct
        );
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT execution_id FROM business.conversation_executions WHERE tenant_id = {permission.TenantId} AND execution_id = {permission.ExecutionId} FOR UPDATE",
            ct
        );
        await using var currentRelationships = new EmploymentRelationshipDbContext(
            new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                .UseNpgsql(db.Database.GetDbConnection())
                .Options
        );
        await currentRelationships.Database.UseTransactionAsync(transaction.GetDbTransaction(), ct);
        await ConversationReconciliationBinding.RequirePermissionAsync(
            db,
            currentRelationships,
            identity,
            permission,
            clock.GetUtcNow(),
            ct,
            clock
        );
        if (
            await db
                .Database.SqlQuery<int>(
                    $"SELECT 1 AS \"Value\" FROM constitutional.employment_dispatch_stops WHERE tenant_id = {permission.TenantId} AND relationship_ref = {permission.RelationshipId.ToString("D")}"
                )
                .AnyAsync(ct)
        )
            throw new ConversationStoppedException();
        var execution =
            await db
                .Executions.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == permission.TenantId
                        && value.ExecutionId == permission.ExecutionId,
                    ct
                )
            ?? throw new ConversationNotAccessibleException();
        var original = await ConversationReconciliationBinding.SourceAsync(
            db,
            currentRelationships,
            execution,
            options.Value.Environment,
            ct
        );
        if (
            ConversationReconciliationBinding.Digest(original.Original) != permission.SourceDigest
            || requireProjection
                && execution.ProjectionVersion != permission.ExpectedProjectionVersion
        )
            throw new ConversationStateConflictException();
        if (permission.ExpiresAt <= clock.GetUtcNow())
            throw new ConversationNotAccessibleException();
        await transaction.CommitAsync(ct);
    }
}
