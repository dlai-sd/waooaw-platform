// Implements: work-contracts/WC-134-whatsapp-demo-complete-rollout-work-component.md §8
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

internal sealed record WhatsAppRoutedOutboxLease(
    WhatsAppOutboxLease Lease,
    WhatsAppRelationshipRoute Candidate,
    WhatsAppCurrentRelationshipRoute Route
);

public sealed class WhatsAppDeliveryObservationRouting(
    IDbContextFactory<EmploymentRelationshipDbContext> relationships,
    IDbContextFactory<ConversationStoreDbContext> conversations,
    WhatsAppTenantExecutionScope execution,
    IWhatsAppCapabilityGate capability,
    TimeProvider clock
)
{
    internal async Task<bool> ReconcileHistoricalWorkAsync(
        WhatsAppOutboxWork work,
        CancellationToken ct
    )
    {
        var authority = capability.RequireActive(clock.GetUtcNow());
        execution.RequireUnchangedAuthority();
        if (
            execution.CurrentTenantId != authority.TenantId
            || execution.ServiceTenantId != authority.TenantId
            || execution.DatabaseTenantOverrideId is not null
            || work.OutboxId == Guid.Empty
        )
            throw new WhatsAppCapabilityUnavailableException("DELIVERY_ROUTE_SCOPE_REQUIRED");
        capability.RequireRecipient(authority.TenantId, work.SenderHash, clock.GetUtcNow());
        await using var relationshipDb = await relationships.CreateDbContextAsync(ct);
        var candidate =
            await WhatsAppRelationshipRouteAuthority.FindDeliveryAsync(
                relationshipDb,
                authority.TenantId,
                work.SenderHash,
                authority.Environment,
                work.OutboxId,
                ct
            ) ?? throw new ConversationIdempotencyConflictException();
        var current = await WhatsAppRelationshipRouteAuthority.FindAsync(
            relationshipDb,
            authority.TenantId,
            work.SenderHash,
            ct
        );
        using var customer = execution.BeginRelationshipValidation(candidate);
        await using var db = await conversations.CreateDbContextAsync(ct);
        if (!db.Database.IsNpgsql())
            throw new WhatsAppChannelBindingUnavailableException(
                "Historical reconciliation requires PostgreSQL."
            );
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        var now = clock.GetUtcNow();
        var locked = await db
            .Database.SqlQuery<Guid>(
                $"""
                SELECT outbox_id AS "Value" FROM business.conversation_outbox
                WHERE outbox_id = {work.OutboxId} AND tenant_id = {candidate.TenantId}
                    AND environment = {authority.Environment}
                FOR UPDATE SKIP LOCKED
                """
            )
            .ToListAsync(ct);
        if (locked.Count == 0)
            return true;
        await RequireDeliverySourceAsync(
            db,
            candidate,
            work.OutboxId,
            work.SenderHash,
            authority.Environment,
            ct
        );
        var row = await db.ConversationOutbox.SingleAsync(
            value => value.OutboxId == work.OutboxId,
            ct
        );
        if (
            (row.State == "PENDING" && (row.LeaseExpiresAt is null || row.LeaseExpiresAt <= now))
            || (row.State == "LEASED" && row.AttemptNumber < 12 && row.LeaseExpiresAt <= now)
        )
        {
            var active = await db
                .Database.SqlQuery<bool>(
                    $"""
                    SELECT EXISTS (SELECT 1 FROM business.channel_bindings
                        WHERE tenant_id = {candidate.TenantId} AND binding_id = {candidate.BindingId}
                            AND status = 'ACTIVE' AND revoked_at IS NULL) AS "Value"
                    """
                )
                .SingleAsync(ct);
            if (!active || current?.BindingId != candidate.BindingId)
            {
                row.State = "BLOCKED";
                row.BlockedReason = "RELATIONSHIP_ROUTE_RETIRED";
                row.LeaseOwner = null;
                row.LeaseExpiresAt = null;
                row.HeartbeatAt = null;
                row.UpdatedAt = now;
                execution.RequireUnchangedAuthority();
                capability.RequireRecipient(authority.TenantId, work.SenderHash, clock.GetUtcNow());
                await db.SaveChangesAsync(ct);
                execution.RequireUnchangedAuthority();
                await transaction.CommitAsync(ct);
                return true;
            }
        }
        var ambiguous =
            row.State is "UNRESOLVED" or "DISPATCHING"
            || row.State == "LEASED" && row.AttemptNumber >= 12;
        if (!ambiguous)
            return row.State is "DELIVERED" or "BLOCKED";
        if (
            row.NextAttemptAt > now
            || row.State is "LEASED" or "DISPATCHING" && row.LeaseExpiresAt > now
        )
            return true;
        if (row.AttemptNumber <= 0 || !Guid.TryParseExact(row.AggregateId, "D", out var messageId))
            throw new ConversationIdempotencyConflictException();
        var receipts = db
            .DeliveryObservations.AsNoTracking()
            .Where(value =>
                value.Environment == row.Environment
                && value.TenantId == row.TenantId
                && value.RelationshipId == row.RelationshipId
                && value.MessageId == messageId
                && value.PortalContextId == null
                && value.Provider == "WHATSAPP"
            );
        var delivered = await receipts.AnyAsync(
            value => value.DeliveryState == "DELIVERED" || value.DeliveryState == "READ",
            ct
        );
        if (!delivered && !await receipts.AnyAsync(value => value.DeliveryState == "FAILED", ct))
            return true; // Unknown submission remains unresolved; never convert it to unsent work.
        row.State = delivered ? "DELIVERED" : "BLOCKED";
        row.BlockedReason = delivered ? null : "PROVIDER_REJECTED";
        row.LeaseOwner = null;
        row.LeaseExpiresAt = null;
        row.HeartbeatAt = null;
        row.UpdatedAt = now;
        execution.RequireUnchangedAuthority();
        capability.RequireRecipient(authority.TenantId, work.SenderHash, clock.GetUtcNow());
        await db.SaveChangesAsync(ct);
        execution.RequireUnchangedAuthority();
        await transaction.CommitAsync(ct);
        return true;
    }

    internal async Task<bool> RecordDeliveryObservationAsync(
        WhatsAppProviderStatusEvent status,
        Func<ConversationStoreDbContext, CancellationToken, Task<bool>> record,
        CancellationToken ct
    )
    {
        var authority = capability.RequireActive(clock.GetUtcNow());
        if (
            execution.ServiceTenantId != authority.TenantId
            || execution.CurrentTenantId != authority.TenantId
            || status.SenderBindingDigest is not { } senderHash
        )
            throw new WhatsAppCapabilityUnavailableException("DELIVERY_ROUTE_SCOPE_REQUIRED");
        execution.RequireUnchangedAuthority();
        capability.RequireRecipient(authority.TenantId, senderHash, clock.GetUtcNow());
        await using var relationshipDb = await relationships.CreateDbContextAsync(ct);
        var candidate = await WhatsAppRelationshipRouteAuthority.FindAsync(
            relationshipDb,
            authority.TenantId,
            senderHash,
            ct
        );
        if (candidate is null)
        {
            await using var serviceDb = await conversations.CreateDbContextAsync(ct);
            return await record(serviceDb, ct);
        }
        if (status.OutboxId is null)
            throw new WhatsAppCapabilityUnavailableException("DELIVERY_ROUTE_CORRELATION_REQUIRED");
        candidate =
            await WhatsAppRelationshipRouteAuthority.FindDeliveryAsync(
                relationshipDb,
                authority.TenantId,
                senderHash,
                authority.Environment,
                status.OutboxId.Value,
                ct
            ) ?? throw new ConversationIdempotencyConflictException();
        if (!relationshipDb.Database.IsNpgsql())
            throw new WhatsAppChannelBindingUnavailableException(
                "Delivery routing requires PostgreSQL."
            );
        using var customer = execution.BeginRelationshipValidation(candidate);
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await RequireDeliverySourceAsync(db, candidate, status, authority.Environment, ct);
        var accepted = await record(db, ct);
        execution.RequireUnchangedAuthority();
        await transaction.CommitAsync(ct);
        return accepted;
    }

    internal static async Task RequireDeliverySourceAsync(
        ConversationStoreDbContext db,
        WhatsAppRelationshipRoute route,
        WhatsAppProviderStatusEvent status,
        string environment,
        CancellationToken ct
    )
    {
        if (status.OutboxId is not { } outboxId)
            throw new ConversationIdempotencyConflictException();
        await RequireDeliverySourceAsync(
            db,
            route,
            outboxId,
            status.SenderBindingDigest,
            environment,
            ct
        );
    }

    private static async Task RequireDeliverySourceAsync(
        ConversationStoreDbContext db,
        WhatsAppRelationshipRoute route,
        Guid outboxId,
        string? senderHash,
        string environment,
        CancellationToken ct
    )
    {
        if (
            outboxId == Guid.Empty
            || senderHash != route.SenderHash
            || string.IsNullOrWhiteSpace(environment)
        )
            throw new ConversationIdempotencyConflictException();
        if (!db.Database.IsNpgsql() || db.Database.CurrentTransaction is null)
            throw new WhatsAppChannelBindingUnavailableException(
                "Delivery route correlation requires the owning PostgreSQL transaction."
            );
        var matches = await db
            .Database.SqlQuery<Guid>(
                $"""
                SELECT o.outbox_id AS "Value"
                FROM business.conversation_outbox AS o
                JOIN business.channel_bindings AS b
                    ON b.tenant_id = o.tenant_id AND b.relationship_id = o.relationship_id
                WHERE o.outbox_id = {outboxId} AND o.environment = {environment}
                    AND o.tenant_id = {route.TenantId} AND o.recipient_binding_digest = {route.SenderHash}
                    AND o.portal_context_id IS NULL
                    AND b.binding_id = {route.BindingId} AND b.channel = 'WHATSAPP'
                    AND b.external_subject_hash = {route.SenderHash} AND b.participant_id = {route.ActorId}
                    AND b.bound_evidence_id = {route.BoundEvidenceId}
                    AND b.conversation_id = o.conversation_id::text
                FOR SHARE OF o, b
                """
            )
            .ToListAsync(ct);
        if (matches.Count != 1 || matches[0] != outboxId)
            throw new ConversationIdempotencyConflictException();
    }
}

public sealed class WhatsAppRelationshipRouting(
    IDbContextFactory<EmploymentRelationshipDbContext> relationships,
    IDbContextFactory<ConversationStoreDbContext> conversations,
    IdentityService identity,
    WhatsAppTenantExecutionScope execution,
    IWhatsAppCapabilityGate capability,
    IConfiguration configuration,
    TimeProvider clock
)
{
    internal static async Task RequireIngressDispatchAsync(
        WhatsAppTenantExecutionScope? execution,
        WhatsAppRelationshipRouting? owner,
        CancellationToken ct
    )
    {
        if (execution?.CurrentTenantId is not { } selected || selected == execution.ServiceTenantId)
            return;
        var routing =
            owner ?? throw new WhatsAppWebhookException(503, "WHATSAPP_ROUTING_OWNER_UNAVAILABLE");
        await routing.RequireCurrentEgressRouteAsync(
            execution.RequireConfirmedRelationshipRoute(),
            ct
        );
    }

    internal static async Task RequireIngressCommitAsync(
        WhatsAppTenantExecutionScope? execution,
        WhatsAppRelationshipRouting? owner,
        ConversationStoreDbContext db,
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid conversationId,
        string channel,
        Guid? bindingId,
        string? senderHash,
        CancellationToken ct
    )
    {
        if (execution?.CurrentTenantId is not { } selected || selected == execution.ServiceTenantId)
            return;
        var route = execution.RequireConfirmedRelationshipRoute();
        if (
            route.TenantId != tenantId
            || route.ParticipantId != participantId
            || route.RelationshipId != relationshipId
            || route.ConversationId != conversationId
            || channel != "WHATSAPP"
            || bindingId is { } binding && binding != route.BindingId
            || senderHash is { } sender && sender != route.SenderHash
        )
            throw new WhatsAppCapabilityUnavailableException("INGRESS_ROUTE_DENIED");
        var routing =
            owner ?? throw new WhatsAppWebhookException(503, "WHATSAPP_ROUTING_OWNER_UNAVAILABLE");
        await routing.RequireCurrentIngressTransactionAsync(db, route, ct);
    }

    internal static async Task<IDbContextTransaction?> BeginIngressReadAsync(
        WhatsAppTenantExecutionScope? execution,
        WhatsAppRelationshipRouting? owner,
        ConversationStoreDbContext db,
        string environment,
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        CancellationToken ct
    )
    {
        if (execution?.CurrentTenantId is not { } selected || selected == execution.ServiceTenantId)
            return null;
        if (!db.Database.IsNpgsql())
        {
            await RequireIngressReadAsync(
                execution,
                owner,
                db,
                environment,
                tenantId,
                participantId,
                relationshipId,
                ct
            );
            throw new WhatsAppChannelBindingUnavailableException(
                "Protected routing reads require PostgreSQL."
            );
        }
        var transaction = await db.Database.BeginTransactionAsync(ct);
        try
        {
            await RequireIngressReadAsync(
                execution,
                owner,
                db,
                environment,
                tenantId,
                participantId,
                relationshipId,
                ct
            );
            return transaction;
        }
        catch
        {
            await transaction.DisposeAsync();
            throw;
        }
    }

    internal static Task RequireIngressReadAsync(
        WhatsAppTenantExecutionScope? execution,
        WhatsAppRelationshipRouting? owner,
        ConversationStoreDbContext db,
        string environment,
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        CancellationToken ct
    )
    {
        if (execution?.CurrentTenantId is not { } selected || selected == execution.ServiceTenantId)
            return Task.CompletedTask;
        var route = execution.RequireConfirmedRelationshipRoute();
        if (route.Environment != environment)
            throw new WhatsAppCapabilityUnavailableException("INGRESS_ROUTE_DENIED");
        return RequireIngressCommitAsync(
            execution,
            owner,
            db,
            tenantId,
            participantId,
            relationshipId,
            route.ConversationId,
            "WHATSAPP",
            route.BindingId,
            route.SenderHash,
            ct
        );
    }

    internal static void RequireIngressReadRelease(WhatsAppTenantExecutionScope? execution)
    {
        if (execution?.CurrentTenantId is { } selected && selected != execution.ServiceTenantId)
            execution.RequireRelationshipRoute(execution.RequireConfirmedRelationshipRoute());
    }

    private async Task RequireCurrentIngressTransactionAsync(
        ConversationStoreDbContext db,
        WhatsAppCurrentRelationshipRoute expected,
        CancellationToken ct
    )
    {
        execution.RequireRelationshipRoute(expected);
        if (!db.Database.IsNpgsql() || db.Database.CurrentTransaction is not { } transaction)
            throw new WhatsAppChannelBindingUnavailableException(
                "Ingress commit validation requires the owning PostgreSQL transaction."
            );
        var issuer =
            configuration["IdentityBrokerRead:ActorIssuer"]
            ?? configuration["IdentityEnvironment:Keycloak:Issuer"];
        if (string.IsNullOrWhiteSpace(issuer))
            throw new WhatsAppChannelBindingUnavailableException(
                "Identity routing issuer is unavailable."
            );
        await using var customer = new EmploymentRelationshipDbContext(
            new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                .UseNpgsql(db.Database.GetDbConnection())
                .Options
        );
        await customer.Database.UseTransactionAsync(transaction.GetDbTransaction(), ct);
        WhatsAppRelationshipRoute candidate;
        using (execution.BeginDatabaseTenantOverride(expected.ServiceTenantId))
        {
            var senderLock = WhatsAppGuestSession.LockKey(
                expected.ServiceTenantId,
                expected.SenderHash
            );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT pg_advisory_xact_lock(hashtextextended({senderLock}, 0))",
                ct
            );
            await RequireGuestConsentAsync(
                db,
                expected.ServiceTenantId,
                expected.SenderHash,
                clock.GetUtcNow(),
                ct
            );
            candidate =
                await WhatsAppRelationshipRouteAuthority.FindAsync(
                    customer,
                    expected.ServiceTenantId,
                    expected.SenderHash,
                    ct
                )
                ?? throw new ConstitutionalActionDeniedException(
                    "WhatsApp relationship route is unavailable."
                );
        }
        // The borrowed context shares this connection; restore customer RLS before its Identity/relationship reads.
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_catalog.set_config('app.current_tenant_id', {expected.TenantId.ToString("D")}, true)",
            ct
        );
        var current = await WhatsAppRelationshipRouteAuthority.RequireCurrentAsync(
            customer,
            identity,
            candidate,
            expected.ServiceTenantId,
            expected.SenderHash,
            issuer,
            expected.Environment,
            clock.GetUtcNow(),
            ct
        );
        if (current != expected)
            throw new ConstitutionalActionDeniedException(
                "WhatsApp relationship route is unavailable."
            );
        await RequireRelationshipNotStoppedAsync(customer, current, ct);
        execution.RequireRelationshipRoute(expected);
        // Sender, Identity and customer row locks remain owned by the caller through canonical commit.
    }

    internal async Task<WhatsAppJourneyReceipt> ReceiveSignedSafetyControlAsync(
        VerifiedPhoneIdentityProof proof,
        RelationshipEmergencyStopService? emergencyStops,
        CancellationToken ct
    )
    {
        var stop = proof.Text.Trim().Equals("STOP", StringComparison.OrdinalIgnoreCase);
        var emergency = proof
            .Text.Trim()
            .Equals("EMERGENCY STOP", StringComparison.OrdinalIgnoreCase);
        var authority = capability.RequireActive(clock.GetUtcNow());
        if (
            (!stop && !emergency)
            || proof.UnsupportedContent
            || execution.CurrentTenantId != authority.TenantId
            || execution.ServiceTenantId != authority.TenantId
            || execution.DatabaseTenantOverrideId is not null
            || proof.Environment != authority.Environment
            || string.IsNullOrWhiteSpace(proof.MessageId)
            || proof.PhoneSubjectHash.Length != 64
            || proof.PhoneSubjectHash.Any(value =>
                value is not (>= '0' and <= '9') and not (>= 'a' and <= 'f')
            )
            || proof.ExpiresAt <= clock.GetUtcNow()
            || (proof.VerifiedAt - proof.SentAt).Duration() > TimeSpan.FromMinutes(5)
        )
            throw new WhatsAppCapabilityUnavailableException("SAFETY_ROUTE_DENIED");
        execution.RequireUnchangedAuthority();
        capability.RequireRecipient(authority.TenantId, proof.PhoneSubjectHash, clock.GetUtcNow());

        await using var db = await relationships.CreateDbContextAsync(ct);
        await using var serviceDb = await conversations.CreateDbContextAsync(ct);
        if (!db.Database.IsNpgsql() || !serviceDb.Database.IsNpgsql())
            throw new WhatsAppChannelBindingUnavailableException(
                "Safety routing requires PostgreSQL."
            );
        if (stop)
        {
            await using var transaction = await serviceDb.Database.BeginTransactionAsync(ct);
            var senderLock = WhatsAppGuestSession.LockKey(
                authority.TenantId,
                proof.PhoneSubjectHash
            );
            await serviceDb.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT pg_advisory_xact_lock(hashtextextended({senderLock}, 0))",
                ct
            );
            var guest = await serviceDb
                .Set<WhatsAppGuestSession>()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == authority.TenantId
                        && value.BindingDigest == proof.PhoneSubjectHash,
                    ct
                );
            if (guest is null)
            {
                guest = new WhatsAppGuestSession
                {
                    TenantId = authority.TenantId,
                    BindingDigest = proof.PhoneSubjectHash,
                    FirstObservedAt = proof.VerifiedAt,
                    LastInboundAt = proof.SentAt,
                };
                serviceDb.Add(guest);
            }
            guest.StoppedAt ??= clock.GetUtcNow();
            execution.RequireUnchangedAuthority();
            await serviceDb.SaveChangesAsync(ct);
            execution.RequireUnchangedAuthority();
            await transaction.CommitAsync(ct);
        }
        // STOP containment commits before directory/customer work and never waits on remote evidence.
        var candidate = await WhatsAppRelationshipRouteAuthority.FindAsync(
            db,
            authority.TenantId,
            proof.PhoneSubjectHash,
            ct
        );
        execution.RequireUnchangedAuthority();
        if (candidate is null)
            return stop
                ? SafetyReceipt(proof.MessageId, "STOPPED", string.Empty)
                : throw new WhatsAppWebhookException(404, "WHATSAPP_IDENTITY_NOT_BOUND");

        using var customer = execution.BeginRelationshipValidation(candidate);
        ChannelBinding binding;
        await using (var transaction = await db.Database.BeginTransactionAsync(ct))
        {
            binding = await RequireSafetyBindingAsync(
                db,
                candidate,
                emergency,
                clock.GetUtcNow(),
                ct
            );
            if (stop)
            {
                var contact = await db.WhatsAppJourneyContacts.SingleAsync(
                    value =>
                        value.TenantId == candidate.TenantId
                        && value.PhoneHmac == candidate.SenderHash,
                    ct
                );
                contact.OptedOutAt ??= proof.VerifiedAt;
                contact.PendingMediumRiskConfirmation = false;
                contact.JourneyStage = "STOP";
                execution.RequireUnchangedAuthority();
                await db.SaveChangesAsync(ct);
            }
            execution.RequireUnchangedAuthority();
            await transaction.CommitAsync(ct);
        }
        if (stop)
            return SafetyReceipt(proof.MessageId, "STOPPED", string.Empty);
        var owner =
            emergencyStops
            ?? throw new WhatsAppWebhookException(503, "WHATSAPP_EMERGENCY_STOP_UNAVAILABLE");
        execution.RequireUnchangedAuthority();
        // Candidate scope permits only this safety owner, not ordinary ingress, budget or provider work.
        var stopped = await owner.StopAsync(
            candidate.TenantId,
            binding.RelationshipId,
            binding.ParticipantId,
            RelationshipRoleCodec.FromDatabase(binding.ParticipantRole),
            proof.CorrelationId,
            ct
        );
        if (stopped is null || stopped.State != EmploymentRelationshipState.StoppedEmergency)
            throw new ConstitutionalActionDeniedException(
                "Relationship Emergency Stop was not confirmed."
            );
        execution.RequireUnchangedAuthority();
        return SafetyReceipt(
            proof.MessageId,
            "ACCEPTED",
            "Emergency Stop is recorded and the relationship is blocked. Session halt confirmation may still be pending."
        );
    }

    private static WhatsAppJourneyReceipt SafetyReceipt(
        string messageId,
        string status,
        string reply
    ) => new(messageId, status, "STOP", reply, false, string.Empty);

    private static async Task<ChannelBinding> RequireSafetyBindingAsync(
        EmploymentRelationshipDbContext db,
        WhatsAppRelationshipRoute candidate,
        bool emergency,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        if (candidate.BoundEvidenceId == Guid.Empty || candidate.PublishedAt > now)
            throw new ConstitutionalActionDeniedException(
                "WhatsApp safety correlation is unavailable."
            );
        var binding =
            await db
                .ChannelBindings.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == candidate.TenantId
                        && value.BindingId == candidate.BindingId,
                    ct
                )
            ?? throw new ConstitutionalActionDeniedException(
                "WhatsApp safety correlation is unavailable."
            );
        var relationshipId = binding.RelationshipId;
        if (db.Database.IsNpgsql())
        {
            if (db.Database.CurrentTransaction is null)
                throw new WhatsAppChannelBindingUnavailableException(
                    "Safety correlation requires its transaction."
                );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT relationship_id FROM business.employment_relationships WHERE tenant_id = {candidate.TenantId} AND relationship_id = {binding.RelationshipId} FOR SHARE",
                ct
            );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT binding_id FROM business.relationship_participants WHERE tenant_id = {candidate.TenantId} AND relationship_id = {binding.RelationshipId} AND participant_id = {candidate.ActorId} FOR SHARE",
                ct
            );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT contact_id FROM business.whatsapp_journey_contacts WHERE tenant_id = {candidate.TenantId} AND phone_hmac = {candidate.SenderHash} FOR UPDATE",
                ct
            );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT binding_id FROM business.channel_bindings WHERE tenant_id = {candidate.TenantId} AND binding_id = {candidate.BindingId} FOR SHARE",
                ct
            );
            binding = await db
                .ChannelBindings.AsNoTracking()
                .SingleAsync(
                    value =>
                        value.TenantId == candidate.TenantId
                        && value.BindingId == candidate.BindingId,
                    ct
                );
        }
        if (
            binding.RelationshipId != relationshipId
            || binding.Channel != "WHATSAPP"
            || binding.ExternalSubjectHash != candidate.SenderHash
            || binding.ParticipantId != candidate.ActorId
            || binding.BoundEvidenceId != candidate.BoundEvidenceId
            || binding.BoundAt is null
            || binding.BoundAt > now
            || !await db.WhatsAppJourneyContacts.AnyAsync(
                value =>
                    value.TenantId == candidate.TenantId && value.PhoneHmac == candidate.SenderHash,
                ct
            )
            || !await db.EmploymentRelationships.AnyAsync(
                value =>
                    value.TenantId == candidate.TenantId
                    && value.RelationshipId == binding.RelationshipId,
                ct
            )
            || await db.ChannelBindings.AnyAsync(
                value =>
                    value.TenantId == candidate.TenantId
                    && value.Channel == "WHATSAPP"
                    && value.Status == "ACTIVE"
                    && value.ExternalSubjectHash == candidate.SenderHash
                    && value.BindingId != candidate.BindingId,
                ct
            )
        )
            throw new ConstitutionalActionDeniedException(
                "WhatsApp safety correlation is unavailable."
            );
        if (
            emergency
            && (
                binding.Status != "ACTIVE"
                || binding.RevokedAt is not null
                || !await db.RelationshipParticipants.AnyAsync(
                    value =>
                        value.TenantId == candidate.TenantId
                        && value.RelationshipId == binding.RelationshipId
                        && value.ParticipantId == candidate.ActorId
                        && value.Status == "ACTIVE"
                        && value.RevokedAt == null
                        && value.BoundAt <= now
                        && value.BoundEvidenceId != Guid.Empty
                        && value.Role
                            == RelationshipRoleCodec.FromDatabase(binding.ParticipantRole),
                    ct
                )
            )
        )
            throw new ConstitutionalActionDeniedException(
                "Emergency Stop requires a current channel participant."
            );
        return binding;
    }

    internal async Task<T> ExecuteSignedIngressAsync<T>(
        string senderHash,
        Func<CancellationToken, Task<T>> operation,
        CancellationToken ct
    )
    {
        if (execution.ServiceTenantId is null)
            throw new WhatsAppCapabilityUnavailableException("RELATIONSHIP_ROUTE_SCOPE_REQUIRED");
        execution.RequireUnchangedAuthority();
        var authority = capability.RequireActive(clock.GetUtcNow());
        if (
            execution.CurrentTenantId != authority.TenantId
            || execution.ServiceTenantId != authority.TenantId
            || execution.DatabaseTenantOverrideId is not null
        )
            throw new WhatsAppCapabilityUnavailableException("RELATIONSHIP_ROUTE_SCOPE_REQUIRED");
        capability.RequireRecipient(authority.TenantId, senderHash, clock.GetUtcNow());
        await using var db = await relationships.CreateDbContextAsync(ct);
        var candidate = await WhatsAppRelationshipRouteAuthority.FindAsync(
            db,
            authority.TenantId,
            senderHash,
            ct
        );
        if (candidate is null)
        {
            execution.RequireUnchangedAuthority();
            var serviceResult = await operation(ct);
            execution.RequireUnchangedAuthority();
            capability.RequireRecipient(authority.TenantId, senderHash, clock.GetUtcNow());
            if (
                await WhatsAppRelationshipRouteAuthority.FindAsync(
                    db,
                    authority.TenantId,
                    senderHash,
                    ct
                )
                is not null
            )
                throw new ConstitutionalActionDeniedException(
                    "The WhatsApp sender route changed during ingress."
                );
            return serviceResult;
        }
        var route = await ExecuteOrdinaryDatabaseWorkAsync(
            senderHash,
            (_, current, _) => Task.FromResult(current),
            ct
        );
        using var customer = execution.BeginRelationshipValidation(candidate);
        execution.ConfirmRelationshipRoute(route);
        await RequireCurrentEgressRouteAsync(route, ct);
        var result = await operation(ct);
        // Provider-event replay may return retained content without calling a Conversation reader.
        await RequireCurrentEgressRouteAsync(route, ct);
        return result;
    }

    internal async Task RequireCurrentEgressRouteAsync(
        WhatsAppCurrentRelationshipRoute expected,
        CancellationToken ct
    )
    {
        execution.RequireRelationshipRoute(expected);
        var authority = capability.RequireActive(clock.GetUtcNow());
        var issuer =
            configuration["IdentityBrokerRead:ActorIssuer"]
            ?? configuration["IdentityEnvironment:Keycloak:Issuer"];
        if (string.IsNullOrWhiteSpace(issuer))
            throw new WhatsAppChannelBindingUnavailableException(
                "Identity routing issuer is unavailable."
            );
        await using var guestDb = await conversations.CreateDbContextAsync(ct);
        await using var db = await relationships.CreateDbContextAsync(ct);
        if (!guestDb.Database.IsNpgsql() || !db.Database.IsNpgsql())
            throw new WhatsAppChannelBindingUnavailableException(
                "Final WhatsApp route validation requires PostgreSQL."
            );
        WhatsAppRelationshipRoute candidate;
        await using (var guestTransaction = await guestDb.Database.BeginTransactionAsync(ct))
        {
            using (execution.BeginDatabaseTenantOverride(expected.ServiceTenantId))
            {
                var senderLock = WhatsAppGuestSession.LockKey(
                    expected.ServiceTenantId,
                    expected.SenderHash
                );
                await guestDb.Database.ExecuteSqlInterpolatedAsync(
                    $"SELECT pg_advisory_xact_lock(hashtextextended({senderLock}, 0))",
                    ct
                );
                await RequireGuestConsentAsync(
                    guestDb,
                    expected.ServiceTenantId,
                    expected.SenderHash,
                    clock.GetUtcNow(),
                    ct
                );
                candidate =
                    await WhatsAppRelationshipRouteAuthority.FindAsync(
                        db,
                        expected.ServiceTenantId,
                        expected.SenderHash,
                        ct
                    )
                    ?? throw new ConstitutionalActionDeniedException(
                        "WhatsApp relationship route is unavailable."
                    );
            }
            await RequireCurrentCustomerEgressAsync(db, candidate, expected, issuer, ct);
            using (execution.BeginDatabaseTenantOverride(expected.ServiceTenantId))
                await RequireGuestConsentAsync(
                    guestDb,
                    expected.ServiceTenantId,
                    expected.SenderHash,
                    clock.GetUtcNow(),
                    ct
                );
            await guestTransaction.CommitAsync(ct);
        }
        execution.RequireRelationshipRoute(expected);
        if (capability.RequireActive(clock.GetUtcNow()) != authority)
            throw new WhatsAppCapabilityUnavailableException("EXECUTION_AUTHORITY_CHANGED");
    }

    private async Task RequireCurrentCustomerEgressAsync(
        EmploymentRelationshipDbContext db,
        WhatsAppRelationshipRoute candidate,
        WhatsAppCurrentRelationshipRoute expected,
        string issuer,
        CancellationToken ct
    )
    {
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        var current = await WhatsAppRelationshipRouteAuthority.RequireCurrentAsync(
            db,
            identity,
            candidate,
            expected.ServiceTenantId,
            expected.SenderHash,
            issuer,
            expected.Environment,
            clock.GetUtcNow(),
            ct
        );
        if (current != expected)
            throw new ConstitutionalActionDeniedException(
                "WhatsApp relationship route is unavailable."
            );
        await RequireRelationshipNotStoppedAsync(db, current, ct);
        execution.RequireRelationshipRoute(expected);
        await transaction.CommitAsync(ct);
    }

    internal Task<WhatsAppRoutedOutboxLease?> LeaseCustomerOutboxAsync(
        WhatsAppOutboxWork work,
        WhatsAppOutboxService outbox,
        string workerId,
        CancellationToken ct
    ) =>
        ExecuteOrdinaryDatabaseWorkAsync(
            work.SenderHash,
            async (db, route, token) =>
            {
                WhatsAppRelationshipRoute? source;
                using (execution.BeginDatabaseTenantOverride(route.ServiceTenantId))
                    source = await WhatsAppRelationshipRouteAuthority.FindDeliveryAsync(
                        db,
                        route.ServiceTenantId,
                        route.SenderHash,
                        route.Environment,
                        work.OutboxId,
                        token
                    );
                if (
                    source is null
                    || source.TenantId != route.TenantId
                    || source.BindingId != route.BindingId
                )
                    throw new ConstitutionalActionDeniedException(
                        "The original outbox route has been retired."
                    );
                var lease = await outbox.LeaseRelationshipAsync(
                    work.OutboxId,
                    route,
                    workerId,
                    clock.GetUtcNow(),
                    token
                );
                if (lease is null)
                    return null;
                var candidate =
                    await WhatsAppRelationshipRouteAuthority.FindAsync(
                        db,
                        route.ServiceTenantId,
                        route.SenderHash,
                        token
                    )
                    ?? throw new ConstitutionalActionDeniedException(
                        "WhatsApp relationship route is unavailable."
                    );
                return new WhatsAppRoutedOutboxLease(lease, candidate, route);
            },
            ct
        );

    internal async Task<bool> ExecuteLeasedCustomerWorkAsync(
        WhatsAppRoutedOutboxLease work,
        Func<WhatsAppOutboxLease, CancellationToken, Task<bool>> operation,
        CancellationToken ct
    )
    {
        execution.RequireUnchangedAuthority();
        if (
            execution.CurrentTenantId != work.Route.ServiceTenantId
            || execution.ServiceTenantId != work.Route.ServiceTenantId
            || work.Lease.TenantId != work.Route.TenantId
            || work.Lease.Environment != work.Route.Environment
            || work.Lease.RelationshipId != work.Route.RelationshipId
            || work.Lease.ConversationId != work.Route.ConversationId
            || work.Lease.LeaseExpiresAt <= clock.GetUtcNow()
        )
            throw new WhatsAppCapabilityUnavailableException("OUTBOX_ROUTE_DENIED");
        using var customer = execution.BeginRelationshipValidation(work.Candidate);
        execution.ConfirmRelationshipRoute(work.Route);
        await RequireCurrentEgressRouteAsync(work.Route, ct);
        // Recheck transactions have ended; provider/heartbeat operations must not hold sender locks.
        return await operation(work.Lease, ct);
    }

    internal async Task<T> ExecuteOrdinaryDatabaseWorkAsync<T>(
        string senderHash,
        Func<
            EmploymentRelationshipDbContext,
            WhatsAppCurrentRelationshipRoute,
            CancellationToken,
            Task<T>
        > operation,
        CancellationToken ct
    )
    {
        var authority = capability.RequireActive(clock.GetUtcNow());
        if (
            execution.ServiceTenantId != authority.TenantId
            || execution.CurrentTenantId != authority.TenantId
        )
            throw new WhatsAppCapabilityUnavailableException("RELATIONSHIP_ROUTE_SCOPE_REQUIRED");
        execution.RequireUnchangedAuthority();
        capability.RequireRecipient(authority.TenantId, senderHash, clock.GetUtcNow());
        var issuer =
            configuration["IdentityBrokerRead:ActorIssuer"]
            ?? configuration["IdentityEnvironment:Keycloak:Issuer"];
        if (string.IsNullOrWhiteSpace(issuer))
            throw new WhatsAppChannelBindingUnavailableException(
                "Identity routing issuer is unavailable."
            );

        await using var db = await relationships.CreateDbContextAsync(ct);
        var candidate =
            await WhatsAppRelationshipRouteAuthority.FindAsync(
                db,
                authority.TenantId,
                senderHash,
                ct
            )
            ?? throw new ConstitutionalActionDeniedException(
                "WhatsApp relationship route is unavailable."
            );

        await using var guestDb = await conversations.CreateDbContextAsync(ct);
        if (!guestDb.Database.IsNpgsql() || !db.Database.IsNpgsql())
            throw new WhatsAppChannelBindingUnavailableException(
                "WhatsApp relationship routing requires PostgreSQL owner transactions."
            );
        await using var guestTransaction = await guestDb.Database.BeginTransactionAsync(ct);
        var senderLock = WhatsAppGuestSession.LockKey(authority.TenantId, senderHash);
        using (execution.BeginDatabaseTenantOverride(authority.TenantId))
        {
            await guestDb.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT pg_advisory_xact_lock(hashtextextended({senderLock}, 0))",
                ct
            );
            await RequireGuestConsentAsync(
                guestDb,
                authority.TenantId,
                senderHash,
                clock.GetUtcNow(),
                ct
            );
        }
        using var customer = execution.BeginRelationshipValidation(candidate);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        var route = await WhatsAppRelationshipRouteAuthority.RequireCurrentAsync(
            db,
            identity,
            candidate,
            authority.TenantId,
            senderHash,
            issuer,
            authority.Environment,
            clock.GetUtcNow(),
            ct
        );
        execution.ConfirmRelationshipRoute(route);
        execution.RequireRelationshipRecipient(
            route.TenantId,
            route.RelationshipId,
            route.BindingId,
            senderHash
        );
        await RequireRelationshipNotStoppedAsync(db, route, ct);
        var result = await operation(db, route, ct);
        await db.SaveChangesAsync(ct);
        var finalRoute = await WhatsAppRelationshipRouteAuthority.RequireCurrentAsync(
            db,
            identity,
            candidate,
            authority.TenantId,
            senderHash,
            issuer,
            authority.Environment,
            clock.GetUtcNow(),
            ct
        );
        if (finalRoute != route)
            throw new ConstitutionalActionDeniedException(
                "WhatsApp relationship route is unavailable."
            );
        await RequireRelationshipNotStoppedAsync(db, route, ct);
        using (execution.BeginDatabaseTenantOverride(authority.TenantId))
            await RequireGuestConsentAsync(
                guestDb,
                authority.TenantId,
                senderHash,
                clock.GetUtcNow(),
                ct
            );
        execution.RequireRelationshipRecipient(
            route.TenantId,
            route.RelationshipId,
            route.BindingId,
            senderHash
        );
        if (capability.RequireActive(clock.GetUtcNow()) != authority)
            throw new WhatsAppCapabilityUnavailableException("EXECUTION_AUTHORITY_CHANGED");
        await transaction.CommitAsync(ct);
        await guestTransaction.CommitAsync(ct);
        return result;
    }

    internal static async Task RequireGuestConsentAsync(
        ConversationStoreDbContext db,
        Guid serviceTenantId,
        string senderHash,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        var guest = await db.Set<WhatsAppGuestSession>()
            .AsNoTracking()
            .SingleOrDefaultAsync(
                value => value.TenantId == serviceTenantId && value.BindingDigest == senderHash,
                ct
            );
        if (
            guest is null
            || guest.StoppedAt is not null
            || guest.AdmittedAt is null
            || guest.AdmittedAt > now
            || guest.EvidenceId is null
            || guest.EvidenceId == Guid.Empty
            || !WhatsAppGuestConsent.IsCurrent(guest)
            || guest.ServiceConsentAt > now
            || guest.ServiceConsentEvidenceId == Guid.Empty
            || guest.ServiceConsentNoticeQueuedAt is null
            || guest.ServiceConsentNoticeQueuedAt > now
            || guest.ServiceConsentNoticeMessageId is null
            || guest.ServiceConsentNoticeMessageId == Guid.Empty
            || string.IsNullOrWhiteSpace(guest.ServiceConsentMessageId)
            || guest.ServiceConsentAt <= guest.ServiceConsentNoticeQueuedAt
        )
            throw new ConstitutionalActionDeniedException(
                "WhatsApp relationship route is unavailable."
            );
    }

    private static async Task RequireRelationshipNotStoppedAsync(
        EmploymentRelationshipDbContext db,
        WhatsAppCurrentRelationshipRoute route,
        CancellationToken ct
    )
    {
        var stopped = await db
            .Database.SqlQuery<bool>(
                $"""
                SELECT EXISTS (
                    SELECT 1 FROM business.relationship_emergency_stop_latches
                    WHERE tenant_id = {route.TenantId} AND relationship_id = {route.RelationshipId}
                ) AS "Value"
                """
            )
            .SingleAsync(ct);
        if (stopped)
            throw new ConstitutionalActionDeniedException(
                "WhatsApp relationship route is unavailable."
            );
    }
}
