// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-02, C6-03
// Constitutional basis: C-005, C-023, C-026, C-059, C-063, ADR-051
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Npgsql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

[Collection(Wc136PostgresFixture.CollectionName)]
public sealed class WorkbenchPostgresLedgerStoreTests(Wc136PostgresFixture fixture)
{
    private readonly PostgresWorkbenchLedgerStore _store = new(fixture.AppConversations);

    private static WorkbenchContext Context(Guid? tenant = null) =>
        new(
            tenant ?? Guid.NewGuid(),
            Guid.NewGuid(),
            "actor",
            Guid.NewGuid(),
            RelationshipParticipantRole.Employer,
            "web",
            "correlation"
        );

    private static string Digest(char value) => new(value, 64);

    private Task<WorkbenchLedgerClaim> ClaimAsync(
        WorkbenchContext context,
        Guid key,
        string digest,
        DateTimeOffset now,
        TimeSpan lease
    ) => _store.ClaimAsync(context, key, digest, now, now + lease, CancellationToken.None);

    private Task<string> StateAsync(WorkbenchContext context, Guid key) =>
        fixture.ScalarAsync<string>(
            $"""
            SELECT COALESCE(
                (SELECT state FROM business.workbench_command_ledger
                 WHERE tenant_id='{context.TenantId}' AND relationship_id='{context.RelationshipId}'
                   AND participant_id='{context.ParticipantId}' AND idempotency_key='{key}'),
                'MISSING')
            """
        );

    [Fact]
    public async Task A_first_claim_records_an_in_progress_receipt_with_its_lease()
    {
        var context = Context();
        var key = Guid.NewGuid();
        var now = DateTimeOffset.UtcNow;

        var claim = await ClaimAsync(context, key, Digest('a'), now, TimeSpan.FromMinutes(1));

        Assert.Equal(WorkbenchLedgerClaimKind.Claimed, claim.Kind);
        Assert.Null(claim.ResultJson);
        Assert.Equal("IN_PROGRESS", await StateAsync(context, key));
        var leaseExpiresAt = await fixture.ScalarAsync<DateTime>(
            $"SELECT lease_expires_at FROM business.workbench_command_ledger WHERE tenant_id='{context.TenantId}'"
        );
        Assert.True(
            Math.Abs(
                (
                    new DateTimeOffset(DateTime.SpecifyKind(leaseExpiresAt, DateTimeKind.Utc))
                    - now.AddMinutes(1)
                ).TotalMilliseconds
            ) < 1
        );
    }

    [Fact]
    public async Task A_retry_while_the_lease_is_live_reports_in_progress_without_a_second_run()
    {
        var context = Context();
        var key = Guid.NewGuid();
        var now = DateTimeOffset.UtcNow;
        await ClaimAsync(context, key, Digest('a'), now, TimeSpan.FromMinutes(1));

        var retry = await ClaimAsync(
            context,
            key,
            Digest('a'),
            now.AddSeconds(5),
            TimeSpan.FromMinutes(1)
        );

        Assert.Equal(WorkbenchLedgerClaimKind.InProgress, retry.Kind);
    }

    [Fact]
    public async Task The_same_key_with_another_request_digest_is_a_conflict_before_and_after_completion()
    {
        var context = Context();
        var key = Guid.NewGuid();
        var now = DateTimeOffset.UtcNow;
        await ClaimAsync(context, key, Digest('a'), now, TimeSpan.FromMinutes(1));

        var running = await ClaimAsync(context, key, Digest('b'), now, TimeSpan.FromMinutes(1));
        await _store.CompleteAsync(context, key, """{"ok":true}""", now, CancellationToken.None);
        var completed = await ClaimAsync(context, key, Digest('b'), now, TimeSpan.FromMinutes(1));

        Assert.Equal(WorkbenchLedgerClaimKind.Conflict, running.Kind);
        Assert.Equal(WorkbenchLedgerClaimKind.Conflict, completed.Kind);
    }

    [Fact]
    public async Task A_completed_receipt_is_replayed_with_its_stored_result()
    {
        var context = Context();
        var key = Guid.NewGuid();
        var now = DateTimeOffset.UtcNow;
        await ClaimAsync(context, key, Digest('a'), now, TimeSpan.FromMinutes(1));
        await _store.CompleteAsync(
            context,
            key,
            """{"outcome":"done","count":3}""",
            now,
            CancellationToken.None
        );

        var replay = await ClaimAsync(context, key, Digest('a'), now, TimeSpan.FromMinutes(1));

        Assert.Equal(WorkbenchLedgerClaimKind.Replay, replay.Kind);
        using var result = JsonDocument.Parse(replay.ResultJson!);
        Assert.Equal("done", result.RootElement.GetProperty("outcome").GetString());
        Assert.Equal(3, result.RootElement.GetProperty("count").GetInt32());
        Assert.Equal("COMPLETED", await StateAsync(context, key));
    }

    [Fact]
    public async Task A_second_completion_never_overwrites_the_first_receipt()
    {
        var context = Context();
        var key = Guid.NewGuid();
        var now = DateTimeOffset.UtcNow;
        await ClaimAsync(context, key, Digest('a'), now, TimeSpan.FromMinutes(1));
        await _store.CompleteAsync(context, key, """{"n":1}""", now, CancellationToken.None);

        await _store.CompleteAsync(context, key, """{"n":2}""", now, CancellationToken.None);
        var replay = await ClaimAsync(context, key, Digest('a'), now, TimeSpan.FromMinutes(1));

        using var result = JsonDocument.Parse(replay.ResultJson!);
        Assert.Equal(1, result.RootElement.GetProperty("n").GetInt32());
    }

    [Fact]
    public async Task An_abandoned_run_whose_lease_lapsed_is_taken_over_with_a_new_lease()
    {
        var context = Context();
        var key = Guid.NewGuid();
        var now = DateTimeOffset.UtcNow;
        await ClaimAsync(context, key, Digest('a'), now, TimeSpan.FromMinutes(1));
        var later = now.AddMinutes(2);

        var takeover = await ClaimAsync(context, key, Digest('a'), later, TimeSpan.FromMinutes(3));

        Assert.Equal(WorkbenchLedgerClaimKind.Claimed, takeover.Kind);
        var leaseExpiresAt = await fixture.ScalarAsync<DateTime>(
            $"SELECT lease_expires_at FROM business.workbench_command_ledger WHERE tenant_id='{context.TenantId}'"
        );
        Assert.True(
            Math.Abs(
                (
                    new DateTimeOffset(DateTime.SpecifyKind(leaseExpiresAt, DateTimeKind.Utc))
                    - later.AddMinutes(3)
                ).TotalMilliseconds
            ) < 1
        );
        Assert.Equal(
            WorkbenchLedgerClaimKind.InProgress,
            (
                await ClaimAsync(
                    context,
                    key,
                    Digest('a'),
                    later.AddMinutes(1),
                    TimeSpan.FromMinutes(1)
                )
            ).Kind
        );
    }

    [Fact]
    public async Task Abandoning_releases_an_in_progress_claim_but_keeps_a_completed_receipt()
    {
        var context = Context();
        var running = Guid.NewGuid();
        var completed = Guid.NewGuid();
        var now = DateTimeOffset.UtcNow;
        await ClaimAsync(context, running, Digest('a'), now, TimeSpan.FromMinutes(1));
        await ClaimAsync(context, completed, Digest('b'), now, TimeSpan.FromMinutes(1));
        await _store.CompleteAsync(context, completed, "{}", now, CancellationToken.None);

        await _store.AbandonAsync(context, running, CancellationToken.None);
        await _store.AbandonAsync(context, completed, CancellationToken.None);

        Assert.Equal("MISSING", await StateAsync(context, running));
        Assert.Equal("COMPLETED", await StateAsync(context, completed));
        Assert.Equal(
            WorkbenchLedgerClaimKind.Claimed,
            (await ClaimAsync(context, running, Digest('c'), now, TimeSpan.FromMinutes(1))).Kind
        );
    }

    [Fact]
    public async Task Receipts_are_scoped_to_the_participant_and_the_tenant()
    {
        var context = Context();
        var key = Guid.NewGuid();
        var now = DateTimeOffset.UtcNow;
        await ClaimAsync(context, key, Digest('a'), now, TimeSpan.FromMinutes(1));

        var otherParticipant = await ClaimAsync(
            context with
            {
                ParticipantId = Guid.NewGuid(),
            },
            key,
            Digest('b'),
            now,
            TimeSpan.FromMinutes(1)
        );
        var otherTenant = await ClaimAsync(
            Context(),
            key,
            Digest('b'),
            now,
            TimeSpan.FromMinutes(1)
        );

        Assert.Equal(WorkbenchLedgerClaimKind.Claimed, otherParticipant.Kind);
        Assert.Equal(WorkbenchLedgerClaimKind.Claimed, otherTenant.Kind);
    }

    [Fact]
    public async Task A_claim_prunes_only_that_tenants_receipts_older_than_a_day()
    {
        var context = Context();
        var other = Context();
        var now = DateTimeOffset.UtcNow;
        await fixture.ExecuteAsync(
            $"""
            INSERT INTO business.workbench_command_ledger
                (tenant_id,relationship_id,participant_id,idempotency_key,request_digest,state,result_json,
                 created_at,completed_at,lease_expires_at)
            VALUES
                ('{context.TenantId}',gen_random_uuid(),gen_random_uuid(),gen_random_uuid(),repeat('a',64),
                 'COMPLETED',jsonb_build_object(),now()-interval '25 hours',now()-interval '25 hours',now()-interval '25 hours'),
                ('{context.TenantId}',gen_random_uuid(),gen_random_uuid(),gen_random_uuid(),repeat('a',64),
                 'COMPLETED',jsonb_build_object(),now()-interval '1 hour',now()-interval '1 hour',now()-interval '1 hour'),
                ('{other.TenantId}',gen_random_uuid(),gen_random_uuid(),gen_random_uuid(),repeat('a',64),
                 'COMPLETED',jsonb_build_object(),now()-interval '25 hours',now()-interval '25 hours',now()-interval '25 hours')
            """
        );

        await ClaimAsync(context, Guid.NewGuid(), Digest('b'), now, TimeSpan.FromMinutes(1));

        Assert.Equal(
            2L,
            await fixture.ScalarAsync<long>(
                $"SELECT count(*) FROM business.workbench_command_ledger WHERE tenant_id='{context.TenantId}'"
            )
        );
        Assert.Equal(
            1L,
            await fixture.ScalarAsync<long>(
                $"SELECT count(*) FROM business.workbench_command_ledger WHERE tenant_id='{other.TenantId}'"
            )
        );
    }

    [Fact]
    public async Task Racing_replicas_cannot_both_claim_the_same_key()
    {
        var context = Context();
        var key = Guid.NewGuid();
        var now = DateTimeOffset.UtcNow;

        var claims = await Task.WhenAll(
            Enumerable
                .Range(0, 8)
                .Select(_ => ClaimAsync(context, key, Digest('a'), now, TimeSpan.FromMinutes(1)))
        );

        Assert.Equal(1, claims.Count(claim => claim.Kind == WorkbenchLedgerClaimKind.Claimed));
        Assert.Equal(7, claims.Count(claim => claim.Kind == WorkbenchLedgerClaimKind.InProgress));
    }

    [Fact]
    public async Task Row_level_security_hides_receipts_from_a_session_without_the_tenant()
    {
        var context = Context();
        await ClaimAsync(
            context,
            Guid.NewGuid(),
            Digest('a'),
            DateTimeOffset.UtcNow,
            TimeSpan.FromMinutes(1)
        );

        await using var connection = new NpgsqlConnection(fixture.AppConnectionString);
        await connection.OpenAsync();
        await using var count = new NpgsqlCommand(
            $"SELECT count(*) FROM business.workbench_command_ledger WHERE tenant_id='{context.TenantId}'",
            connection
        );

        Assert.Equal(0L, (long)(await count.ExecuteScalarAsync())!);
    }
}

[Collection(Wc136PostgresFixture.CollectionName)]
public sealed class WorkbenchPostgresHandoffStoreTests(Wc136PostgresFixture fixture)
{
    private readonly PostgresWorkbenchHandoffStore _store = new(fixture.AppConversations);

    private static string Hash() =>
        Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes(Guid.NewGuid().ToString()))
        );

    private static WorkbenchHandoffRecord Handoff(
        string? hash = null,
        Guid? tenant = null,
        string purpose = "WEB_WORKBENCH",
        string? contextRef = "item-1",
        DateTimeOffset? createdAt = null,
        TimeSpan? lifetime = null
    )
    {
        var created = createdAt ?? DateTimeOffset.UtcNow;
        return new(
            Guid.NewGuid(),
            hash ?? Hash(),
            tenant ?? Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            purpose,
            contextRef,
            created,
            created + (lifetime ?? TimeSpan.FromMinutes(10))
        );
    }

    private Task<WorkbenchHandoffRedemption?> ConsumeAsync(
        WorkbenchHandoffRecord record,
        DateTimeOffset? now = null,
        Guid? tenant = null,
        Guid? relationship = null,
        Guid? participant = null,
        string? hash = null
    ) =>
        _store.ConsumeAsync(
            hash ?? record.TokenHash,
            tenant ?? record.TenantId,
            relationship ?? record.RelationshipId,
            participant ?? record.ParticipantId,
            now ?? DateTimeOffset.UtcNow,
            CancellationToken.None
        );

    private Task<bool> ConsumedAsync(WorkbenchHandoffRecord record) =>
        fixture.ScalarAsync<bool>(
            $"SELECT consumed_at IS NOT NULL FROM business.workbench_handoffs WHERE handoff_ref='{record.HandoffRef}'"
        );

    [Fact]
    public async Task A_handoff_is_redeemed_once_and_returns_its_purpose_and_context()
    {
        var record = Handoff(purpose: "APPROVAL", contextRef: "approval-42");
        await _store.InsertAsync(record, CancellationToken.None);

        var first = await ConsumeAsync(record);
        var second = await ConsumeAsync(record);

        Assert.Equal(new WorkbenchHandoffRedemption("APPROVAL", "approval-42"), first);
        Assert.Null(second);
        Assert.True(await ConsumedAsync(record));
    }

    [Fact]
    public async Task A_handoff_without_context_redeems_with_a_null_context()
    {
        var record = Handoff(contextRef: null);
        await _store.InsertAsync(record, CancellationToken.None);

        var redemption = await ConsumeAsync(record);

        Assert.NotNull(redemption);
        Assert.Equal("WEB_WORKBENCH", redemption.Purpose);
        Assert.Null(redemption.ContextRef);
    }

    [Fact]
    public async Task A_handoff_is_not_redeemed_by_another_caller_after_expiry_or_for_an_unknown_token()
    {
        var record = Handoff(lifetime: TimeSpan.FromMinutes(5));
        await _store.InsertAsync(record, CancellationToken.None);

        Assert.Null(await ConsumeAsync(record, participant: Guid.NewGuid()));
        Assert.Null(await ConsumeAsync(record, relationship: Guid.NewGuid()));
        Assert.Null(await ConsumeAsync(record, tenant: Guid.NewGuid()));
        Assert.Null(await ConsumeAsync(record, hash: Hash()));
        Assert.Null(await ConsumeAsync(record, now: record.ExpiresAt.AddSeconds(1)));
        Assert.False(await ConsumedAsync(record));
        Assert.NotNull(await ConsumeAsync(record));
    }

    [Fact]
    public async Task Racing_redemptions_succeed_for_exactly_one_caller()
    {
        var record = Handoff();
        await _store.InsertAsync(record, CancellationToken.None);

        var results = await Task.WhenAll(Enumerable.Range(0, 8).Select(_ => ConsumeAsync(record)));

        Assert.Equal(1, results.Count(result => result is not null));
    }

    [Fact]
    public async Task Inserting_prunes_that_tenants_handoffs_expired_for_over_an_hour()
    {
        var tenant = Guid.NewGuid();
        await fixture.ExecuteAsync(
            $"""
            INSERT INTO business.workbench_handoffs
                (handoff_ref,token_hash,tenant_id,relationship_id,participant_id,purpose,created_at,expires_at)
            VALUES
                (gen_random_uuid(),'{Hash()}','{tenant}',gen_random_uuid(),gen_random_uuid(),'EVIDENCE',
                 now()-interval '3 hours',now()-interval '2 hours'),
                (gen_random_uuid(),'{Hash()}','{tenant}',gen_random_uuid(),gen_random_uuid(),'PAYMENT',
                 now()-interval '2 hours',now()-interval '10 minutes')
            """
        );

        await _store.InsertAsync(Handoff(tenant: tenant), CancellationToken.None);

        Assert.Equal(
            2L,
            await fixture.ScalarAsync<long>(
                $"SELECT count(*) FROM business.workbench_handoffs WHERE tenant_id='{tenant}'"
            )
        );
        Assert.Equal(
            0L,
            await fixture.ScalarAsync<long>(
                $"SELECT count(*) FROM business.workbench_handoffs WHERE tenant_id='{tenant}' AND purpose='EVIDENCE'"
            )
        );
    }

    [Fact]
    public async Task A_handoff_for_an_unknown_purpose_is_refused_and_leaves_no_row()
    {
        var record = Handoff(purpose: "ANYTHING_ELSE");

        await Assert.ThrowsAnyAsync<Exception>(() =>
            _store.InsertAsync(record, CancellationToken.None)
        );

        Assert.Equal(
            0L,
            await fixture.ScalarAsync<long>(
                $"SELECT count(*) FROM business.workbench_handoffs WHERE handoff_ref='{record.HandoffRef}'"
            )
        );
    }
}
