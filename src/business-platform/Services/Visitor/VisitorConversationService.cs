// Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R001, WC135-R002, WC135-R003, WC135-R007, WC135-R009, WC135-R010, WC135-R011, WC135-R014
// Constitutional basis: C-009, C-023, C-026, C-039, C-048, C-049, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services.Visitor;

public sealed class VisitorConversationException(
    string code,
    int status,
    int? retryAfterSeconds = null
) : Exception(code)
{
    public string Code { get; } = code;
    public int Status { get; } = status;
    public int? RetryAfterSeconds { get; } = retryAfterSeconds;
}

public sealed record VisitorCaptured(
    string? BusinessDomain,
    string? City,
    string? GoalCode,
    bool HasName,
    bool HasEmail
);

public sealed record VisitorSessionView(
    Guid SessionId,
    string Channel,
    string State,
    string Outcome,
    VisitorCaptured Captured,
    VisitorReply? Reply,
    bool Created
);

public sealed record VisitorTurnResult(
    Guid SessionId,
    Guid MessageId,
    string Cursor,
    string State,
    string Outcome,
    VisitorCaptured Captured,
    VisitorReply Reply,
    bool Replayed
);

public sealed record VisitorTranscriptEntry(
    long Sequence,
    string Role,
    VisitorInput? Content,
    VisitorReply? Reply,
    DateTimeOffset At
);

public sealed record VisitorTranscriptPage(
    IReadOnlyList<VisitorTranscriptEntry> Items,
    string? NextCursor
);

/// <summary>What the WhatsApp adapter needs back from one inbound visitor message.</summary>
public sealed record VisitorWhatsAppResult(
    VisitorReply Reply,
    string Event,
    string State,
    string Outcome
);

public sealed record VisitorDataRightsResult(int Leads, int Sessions, int Turns);

/// <summary>
/// The channel-neutral visitor conversation core (WC-135). WhatsApp, the visitor API and simulated customers
/// all go through the same state machine, lead capture and handoff logic.
/// </summary>
public sealed class VisitorConversationService(
    IDbContextFactory<ConversationStoreDbContext> factory,
    IVisitorContentProvider contents,
    VisitorFieldProtector protector,
    IOptionsMonitor<VisitorConversationOptions> options,
    IOptionsMonitor<VisitorLeadOptions> leadOptions,
    IWhatsAppRegistrationEvidenceGateway evidence,
    VisitorTelemetry telemetry,
    TimeProvider clock,
    ILogger<VisitorConversationService> logger
)
{
    private static readonly TimeSpan Minute = TimeSpan.FromMinutes(1);

    // ── Endpoint channels ───────────────────────────────────────────────────────────────────────

    public async Task<VisitorSessionView> OpenSessionAsync(
        Guid tenantId,
        string channel,
        string? subjectKey,
        CancellationToken ct
    )
    {
        if (!VisitorChannels.IsEndpointChannel(channel))
            throw new VisitorConversationException("VISITOR_REQUEST_INVALID", 400);
        var opts = options.CurrentValue;
        var content = ResolveContent(tenantId);
        var now = clock.GetUtcNow();
        var subjectHash =
            channel == VisitorChannels.Simulation
                ? SubjectHash(
                    "sim",
                    subjectKey
                        ?? throw new VisitorConversationException("VISITOR_REQUEST_INVALID", 400)
                )
                : SubjectHash(channel.ToLowerInvariant(), Guid.NewGuid().ToString("N"));

        await using var db = await factory.CreateDbContextAsync(ct);
        var existing = await db.VisitorSessions.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.SubjectHash == subjectHash,
            ct
        );
        if (existing is not null)
            return await ViewAsync(db, existing, created: false, ct);

        if (channel == VisitorChannels.Simulation)
        {
            var dayStart = now.UtcDateTime.Date;
            var today = await db.VisitorSessions.CountAsync(
                value =>
                    value.TenantId == tenantId
                    && value.Channel == VisitorChannels.Simulation
                    && value.CreatedAt >= dayStart,
                ct
            );
            if (today >= opts.SimulatorMaxSessionsPerDay)
                throw new VisitorConversationException("VISITOR_RATE_LIMITED", 429, 3_600);
        }

        var snapshot = new VisitorSnapshot();
        var retention = RetentionDays(tenantId, channel);
        var transition = VisitorStateMachine.Start(content, snapshot, retention);
        var session = new VisitorSession
        {
            SessionId = Guid.NewGuid(),
            TenantId = tenantId,
            SubjectHash = subjectHash,
            Channel = channel,
            State = transition.Next.State,
            Outcome = VisitorOutcomes.None,
            ContentVersion = content.VersionLabel,
            CreatedAt = now,
            UpdatedAt = now,
        };
        db.VisitorSessions.Add(session);
        var reply = Finalize(transition.Reply, opts, handoffUrl: null);
        db.VisitorTurns.Add(
            new VisitorTurn
            {
                SessionId = session.SessionId,
                Sequence = 0,
                TenantId = tenantId,
                MessageId = Guid.NewGuid(),
                IdempotencyKey = Guid.NewGuid(),
                RequestHash = Sha256Hex("open"),
                VisitorContentType = VisitorInput.TextKind,
                ReplyJson = reply.ToJson(),
                StateAfter = session.State,
                OutcomeAfter = session.Outcome,
                CreatedAt = now,
            }
        );
        try
        {
            await db.SaveChangesAsync(ct);
        }
        catch (DbUpdateException)
        {
            db.ChangeTracker.Clear();
            var raced = await db.VisitorSessions.SingleOrDefaultAsync(
                value => value.TenantId == tenantId && value.SubjectHash == subjectHash,
                ct
            );
            if (raced is not null)
                return await ViewAsync(db, raced, created: false, ct);
            throw;
        }
        return new VisitorSessionView(
            session.SessionId,
            channel,
            session.State,
            session.Outcome,
            new VisitorCaptured(null, null, null, false, false),
            reply,
            true
        );
    }

    public async Task<VisitorTurnResult> SendAsync(
        Guid tenantId,
        Guid sessionId,
        Guid idempotencyKey,
        VisitorInput input,
        CancellationToken ct
    )
    {
        var started = TimeProvider.System.GetTimestamp();
        var opts = options.CurrentValue;
        var content = ResolveContent(tenantId);
        var now = clock.GetUtcNow();
        await using var db = await factory.CreateDbContextAsync(ct);
        await using var transaction = db.Database.IsRelational()
            ? await db.Database.BeginTransactionAsync(ct)
            : null;
        await LockAsync(db, $"visitor:{sessionId:D}", ct);
        var session =
            await db.VisitorSessions.SingleOrDefaultAsync(
                value => value.TenantId == tenantId && value.SessionId == sessionId,
                ct
            ) ?? throw new VisitorConversationException("VISITOR_SESSION_NOT_FOUND", 404);

        var requestHash = Sha256Hex(CanonicalRequest(input));
        var prior = await db.VisitorTurns.SingleOrDefaultAsync(
            value => value.SessionId == sessionId && value.IdempotencyKey == idempotencyKey,
            ct
        );
        if (prior is not null)
        {
            if (!string.Equals(prior.RequestHash, requestHash, StringComparison.Ordinal))
                throw new VisitorConversationException("VISITOR_IDEMPOTENCY_CONFLICT", 409);
            var lead = await LoadLeadAsync(db, session, ct);
            return new VisitorTurnResult(
                sessionId,
                prior.MessageId,
                Cursor(prior.Sequence),
                prior.StateAfter,
                prior.OutcomeAfter,
                Captured(lead),
                VisitorReply.FromJson(prior.ReplyJson),
                true
            );
        }

        await EnforceLimitsAsync(db, session, opts, now, ct);
        var priorState = session.State;
        var currentLead = await LoadLeadAsync(db, session, ct);
        VisitorTransition transition;
        string reason;
        if (
            session.Channel is VisitorChannels.Web or VisitorChannels.Mobile
            && !VisitorHours.IsOpen(content.Hours, now)
        )
        {
            transition = new VisitorTransition(
                Snapshot(session, currentLead),
                new VisitorReply
                {
                    State = session.State,
                    ContentVersion = content.VersionLabel,
                    Blocks = [VisitorReplyBlock.TextBlock(content.Fixed.ClosedNotice)],
                },
                new VisitorLeadUpdate(),
                false,
                "CLOSED_HOURS"
            );
            reason = "CLOSED_HOURS";
        }
        else
        {
            transition = VisitorStateMachine.Step(
                content,
                opts,
                Snapshot(session, currentLead),
                input,
                RetentionDays(tenantId, session.Channel)
            );
            reason = transition.Event;
        }

        var messageId = Guid.NewGuid();
        var sequence = (session.TurnCount) + 1L;
        var (reply, leadAfter) = await ApplyAsync(
            db,
            session,
            currentLead,
            transition,
            content,
            opts,
            messageId,
            rawPhone: null,
            ct
        );
        db.VisitorTurns.Add(
            new VisitorTurn
            {
                SessionId = sessionId,
                Sequence = sequence,
                TenantId = tenantId,
                MessageId = messageId,
                IdempotencyKey = idempotencyKey,
                RequestHash = requestHash,
                VisitorContentType =
                    input.Kind == VisitorInput.ChoiceKind
                        ? VisitorInput.ChoiceKind
                        : VisitorInput.TextKind,
                VisitorTextProtected = string.IsNullOrWhiteSpace(input.Text)
                    ? null
                    : await protector.ProtectAsync(
                        input.Text,
                        tenantId,
                        "visitor_text",
                        messageId,
                        ct
                    ),
                VisitorChoiceId = input.ChoiceId,
                ReplyJson = reply.ToJson(),
                StateAfter = session.State,
                OutcomeAfter = session.Outcome,
                CreatedAt = now,
            }
        );
        await db.SaveChangesAsync(ct);
        if (transaction is not null)
            await transaction.CommitAsync(ct);

        if (input.ChoiceId is { } choice)
            telemetry.ChoiceTap(choice);
        EmitTelemetry(session, priorState, reason, started, 200);
        return new VisitorTurnResult(
            sessionId,
            messageId,
            Cursor(sequence),
            session.State,
            session.Outcome,
            Captured(leadAfter),
            reply,
            false
        );
    }

    public async Task<VisitorSessionView> GetSessionAsync(
        Guid tenantId,
        Guid sessionId,
        CancellationToken ct
    )
    {
        await using var db = await factory.CreateDbContextAsync(ct);
        var session =
            await db
                .VisitorSessions.AsNoTracking()
                .SingleOrDefaultAsync(
                    value => value.TenantId == tenantId && value.SessionId == sessionId,
                    ct
                )
            ?? throw new VisitorConversationException("VISITOR_SESSION_NOT_FOUND", 404);
        return await ViewAsync(db, session, created: false, ct);
    }

    public async Task<VisitorTranscriptPage> ListAsync(
        Guid tenantId,
        Guid sessionId,
        string? cursor,
        int limit,
        CancellationToken ct
    )
    {
        if (limit is < 1 or > 100)
            throw new VisitorConversationException("VISITOR_REQUEST_INVALID", 400);
        long after = -1;
        if (cursor is not null && !TryParseCursor(cursor, out after))
            throw new VisitorConversationException("VISITOR_REQUEST_INVALID", 400);
        await using var db = await factory.CreateDbContextAsync(ct);
        if (
            !await db.VisitorSessions.AnyAsync(
                value => value.TenantId == tenantId && value.SessionId == sessionId,
                ct
            )
        )
            throw new VisitorConversationException("VISITOR_SESSION_NOT_FOUND", 404);
        var turns = await db
            .VisitorTurns.AsNoTracking()
            .Where(value => value.SessionId == sessionId && value.Sequence > after)
            .OrderBy(value => value.Sequence)
            .Take(limit + 1)
            .ToListAsync(ct);
        var page = turns.Take(limit).ToList();
        var items = new List<VisitorTranscriptEntry>();
        foreach (var turn in page)
        {
            if (turn.Sequence > 0)
            {
                var text = turn.VisitorTextProtected is null
                    ? null
                    : await protector.UnprotectAsync(
                        turn.VisitorTextProtected,
                        tenantId,
                        "visitor_text",
                        turn.MessageId,
                        ct
                    );
                items.Add(
                    new VisitorTranscriptEntry(
                        turn.Sequence * 2 - 1,
                        "VISITOR",
                        new VisitorInput(turn.VisitorContentType, text, turn.VisitorChoiceId),
                        null,
                        turn.CreatedAt
                    )
                );
            }
            items.Add(
                new VisitorTranscriptEntry(
                    turn.Sequence * 2,
                    "WAOOAW",
                    null,
                    VisitorReply.FromJson(turn.ReplyJson),
                    turn.CreatedAt
                )
            );
        }
        return new VisitorTranscriptPage(
            items,
            turns.Count > limit ? Cursor(page[^1].Sequence) : null
        );
    }

    // ── WhatsApp channel (consent, STOP, hours and traffic are owned by the guest session) ─────

    public async Task<VisitorWhatsAppResult> HandleWhatsAppAsync(
        Guid tenantId,
        string subjectHash,
        string? rawPhone,
        Guid consentEvidenceId,
        VisitorInput input,
        CancellationToken ct
    )
    {
        var started = TimeProvider.System.GetTimestamp();
        var opts = options.CurrentValue;
        var content = ResolveContent(tenantId);
        var now = clock.GetUtcNow();
        await using var db = await factory.CreateDbContextAsync(ct);
        await using var transaction = db.Database.IsRelational()
            ? await db.Database.BeginTransactionAsync(ct)
            : null;
        await LockAsync(db, $"visitor:wa:{tenantId:D}:{subjectHash}", ct);
        var session = await db.VisitorSessions.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.SubjectHash == subjectHash,
            ct
        );
        if (session is null)
        {
            session = new VisitorSession
            {
                SessionId = Guid.NewGuid(),
                TenantId = tenantId,
                SubjectHash = subjectHash,
                Channel = VisitorChannels.WhatsApp,
                State = VisitorStates.Discover,
                ContentVersion = content.VersionLabel,
                ConsentAt = now,
                ConsentNoticeVersion = content.Consent.NoticeVersion,
                ConsentEvidenceId = consentEvidenceId,
                CreatedAt = now,
                UpdatedAt = now,
            };
            db.VisitorSessions.Add(session);
        }
        else if (
            session.State
            is VisitorStates.New
                or VisitorStates.ConsentPending
                or VisitorStates.Stopped
        )
        {
            session.State = VisitorStates.Discover;
            session.ConsentAt = now;
            session.ConsentNoticeVersion = content.Consent.NoticeVersion;
            session.ConsentEvidenceId = consentEvidenceId;
        }

        var priorState = session.State;
        var lead = await LoadLeadAsync(db, session, ct);
        var transition = VisitorStateMachine.Step(
            content,
            opts,
            Snapshot(session, lead) with
            {
                ConsentGiven = true,
            },
            input,
            RetentionDays(tenantId, VisitorChannels.WhatsApp)
        );
        var (reply, _) = await ApplyAsync(
            db,
            session,
            lead,
            transition,
            content,
            opts,
            Guid.NewGuid(),
            rawPhone,
            ct
        );
        await db.SaveChangesAsync(ct);
        if (transaction is not null)
            await transaction.CommitAsync(ct);
        if (input.ChoiceId is { } choice)
            telemetry.ChoiceTap(choice);
        EmitTelemetry(session, priorState, transition.Event, started, 200);
        return new VisitorWhatsAppResult(reply, transition.Event, session.State, session.Outcome);
    }

    /// <summary>Marks a WhatsApp visitor as stopped (the guest session owns the STOP semantics).</summary>
    public async Task RecordWhatsAppStopAsync(
        Guid tenantId,
        string subjectHash,
        CancellationToken ct
    )
    {
        await using var db = await factory.CreateDbContextAsync(ct);
        var session = await db.VisitorSessions.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.SubjectHash == subjectHash,
            ct
        );
        if (session is null || session.State == VisitorStates.Stopped)
            return;
        session.State = VisitorStates.Stopped;
        session.Outcome = VisitorOutcomes.OptOut;
        session.UpdatedAt = clock.GetUtcNow();
        await db.SaveChangesAsync(ct);
        telemetry.Outcome(VisitorOutcomes.OptOut, VisitorChannels.WhatsApp);
    }

    // ── Handoff ─────────────────────────────────────────────────────────────────────────────────

    /// <summary>Records INTENT for an opened handoff reference. Unknown, expired or reused references record nothing.</summary>
    public async Task<bool> TapHandoffAsync(Guid tenantId, string reference, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(reference) || reference.Length > 512)
            return false;
        var hash = Sha256Hex(reference);
        var now = clock.GetUtcNow();
        await using var db = await factory.CreateDbContextAsync(ct);
        var row = await db.VisitorHandoffReferences.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.ReferenceHash == hash,
            ct
        );
        if (row is null || row.ExpiresAt <= now || row.TappedAt is not null)
            return false;
        var lead = await db.VisitorLeads.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.LeadId == row.LeadId,
            ct
        );
        if (lead is null)
            return false;
        row.TappedAt = now;
        if (lead.Status == VisitorLeadStatus.Open)
            lead.Status = VisitorLeadStatus.Intent;
        lead.UpdatedAt = now;
        var session = await db.VisitorSessions.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.SubjectHash == lead.SubjectHash,
            ct
        );
        if (session is not null)
        {
            session.Outcome = Snapshot(session, lead).Outcome;
            session.UpdatedAt = now;
            telemetry.Outcome(session.Outcome, session.Channel);
        }
        await db.SaveChangesAsync(ct);
        return true;
    }

    // ── Data rights ─────────────────────────────────────────────────────────────────────────────

    /// <summary>Deletes every visitor record for a subject: lead (and its references), session and transcript.</summary>
    public async Task<VisitorDataRightsResult> DeleteSubjectDataAsync(
        Guid tenantId,
        string subjectHash,
        CancellationToken ct
    )
    {
        await using var db = await factory.CreateDbContextAsync(ct);
        var leads = await db
            .VisitorLeads.Where(value =>
                value.TenantId == tenantId && value.SubjectHash == subjectHash
            )
            .ToListAsync(ct);
        var sessions = await db
            .VisitorSessions.Where(value =>
                value.TenantId == tenantId && value.SubjectHash == subjectHash
            )
            .ToListAsync(ct);
        var sessionIds = sessions.Select(value => value.SessionId).ToList();
        var turns = await db
            .VisitorTurns.Where(value => sessionIds.Contains(value.SessionId))
            .ToListAsync(ct);
        var leadIds = leads.Select(value => value.LeadId).ToList();
        db.VisitorHandoffReferences.RemoveRange(
            await db
                .VisitorHandoffReferences.Where(value => leadIds.Contains(value.LeadId))
                .ToListAsync(ct)
        );
        db.VisitorTurns.RemoveRange(turns);
        db.VisitorSessions.RemoveRange(sessions);
        db.VisitorLeads.RemoveRange(leads);
        await db.SaveChangesAsync(ct);
        logger.LogInformation(
            "visitor.data_rights.deleted leads={Leads} sessions={Sessions} turns={Turns}",
            leads.Count,
            sessions.Count,
            turns.Count
        );
        return new VisitorDataRightsResult(leads.Count, sessions.Count, turns.Count);
    }

    /// <summary>Returns the stored values for one subject in clear text for a data-rights export.</summary>
    public async Task<IReadOnlyDictionary<string, string?>> ExportSubjectLeadAsync(
        Guid tenantId,
        string subjectHash,
        CancellationToken ct
    )
    {
        await using var db = await factory.CreateDbContextAsync(ct);
        var lead = await db
            .VisitorLeads.AsNoTracking()
            .FirstOrDefaultAsync(
                value => value.TenantId == tenantId && value.SubjectHash == subjectHash,
                ct
            );
        if (lead is null)
            return new Dictionary<string, string?>();
        return new Dictionary<string, string?>
        {
            ["businessDomain"] = lead.BusinessDomain,
            ["businessText"] = lead.BusinessText,
            ["city"] = lead.City,
            ["goalCode"] = lead.GoalCode,
            ["status"] = lead.Status,
            ["phone"] = lead.PhoneProtected is null
                ? null
                : await protector.UnprotectAsync(
                    lead.PhoneProtected,
                    tenantId,
                    "phone",
                    lead.LeadId,
                    ct
                ),
            ["name"] = lead.ContactNameProtected is null
                ? null
                : await protector.UnprotectAsync(
                    lead.ContactNameProtected,
                    tenantId,
                    "name",
                    lead.LeadId,
                    ct
                ),
            ["email"] = lead.ContactEmailProtected is null
                ? null
                : await protector.UnprotectAsync(
                    lead.ContactEmailProtected,
                    tenantId,
                    "email",
                    lead.LeadId,
                    ct
                ),
        };
    }

    // ── Core application of a transition ────────────────────────────────────────────────────────

    private async Task<(VisitorReply Reply, VisitorLead? Lead)> ApplyAsync(
        ConversationStoreDbContext db,
        VisitorSession session,
        VisitorLead? lead,
        VisitorTransition transition,
        VisitorContentSet content,
        VisitorConversationOptions opts,
        Guid messageId,
        string? rawPhone,
        CancellationToken ct
    )
    {
        var now = clock.GetUtcNow();
        var update = transition.Lead;
        var consentReference = session.ConsentEvidenceId ?? Guid.NewGuid();

        if (transition.Event == "CONSENT_RECORDED" && session.ConsentAt is null)
        {
            session.ConsentAt = now;
            session.ConsentNoticeVersion = content.Consent.NoticeVersion;
            session.ConsentEvidenceId = await RecordConsentEvidenceAsync(session, content, now, ct);
            consentReference = session.ConsentEvidenceId!.Value;
        }

        var needsLead =
            lead is null
            && (!update.IsEmpty || transition.WantsHandoffReference)
            && session.ConsentEvidenceId is not null;
        if (needsLead)
        {
            lead = new VisitorLead
            {
                LeadId = Guid.NewGuid(),
                TenantId = session.TenantId,
                SubjectHash = session.SubjectHash,
                SourceChannel = session.Channel,
                ConsentReference = consentReference,
                CreatedAt = now,
                UpdatedAt = now,
            };
            if (rawPhone is not null)
                lead.PhoneProtected = await protector.ProtectAsync(
                    rawPhone,
                    session.TenantId,
                    "phone",
                    lead.LeadId,
                    ct
                );
            db.VisitorLeads.Add(lead);
            session.LeadId = lead.LeadId;
        }
        if (lead is not null && !update.IsEmpty)
        {
            lead.BusinessDomain = update.Domain ?? lead.BusinessDomain;
            lead.BusinessText = update.BusinessText ?? lead.BusinessText;
            lead.City = update.City ?? lead.City;
            lead.GoalCode = update.Goal ?? lead.GoalCode;
            if (update.Name is not null)
                lead.ContactNameProtected = await protector.ProtectAsync(
                    update.Name,
                    session.TenantId,
                    "name",
                    lead.LeadId,
                    ct
                );
            if (update.Email is not null)
                lead.ContactEmailProtected = await protector.ProtectAsync(
                    update.Email,
                    session.TenantId,
                    "email",
                    lead.LeadId,
                    ct
                );
            lead.UpdatedAt = now;
        }
        if (lead is not null && rawPhone is not null && lead.PhoneProtected is null)
            lead.PhoneProtected = await protector.ProtectAsync(
                rawPhone,
                session.TenantId,
                "phone",
                lead.LeadId,
                ct
            );

        string? handoffUrl = null;
        if (transition.WantsHandoffReference && lead is not null)
            handoffUrl = await IssueHandoffReferenceAsync(db, lead, opts, now);

        var next = transition.Next;
        var priorOutcome = session.Outcome;
        session.State = next.State;
        session.TurnCount += 1;
        session.Nudges = next.Nudges;
        session.UpdatedAt = now;
        session.ContentVersion = content.VersionLabel;
        if (next.TurnsToFirstValue is { } first && session.TurnsToFirstValue is null)
        {
            session.TurnsToFirstValue = first;
            telemetry.TurnsToFirstValue(first);
        }
        session.Outcome = Snapshot(session, lead).Outcome;
        if (!string.Equals(priorOutcome, session.Outcome, StringComparison.Ordinal))
            telemetry.Outcome(session.Outcome, session.Channel);

        var reply = Finalize(transition.Reply, opts, handoffUrl);
        var problems = VisitorReplyValidator.Validate(reply, opts);
        if (problems.Count > 0)
        {
            logger.LogError(
                "visitor.reply.invalid state={State} contentVersion={ContentVersion} problems={Problems}",
                reply.State,
                reply.ContentVersion,
                string.Join(",", problems.Take(8))
            );
            foreach (var problem in problems.Take(3))
                telemetry.PolicyViolation(problem);
            throw new VisitorConversationException("VISITOR_CONTENT_UNAVAILABLE", 503);
        }
        _ = messageId;
        return (reply, lead);
    }

    private async Task<Guid> RecordConsentEvidenceAsync(
        VisitorSession session,
        VisitorContentSet content,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        if (session.Channel == VisitorChannels.Simulation)
            return Guid.NewGuid();
        var id = await evidence.RecordGuestConsentAsync(
            session.TenantId,
            session.SessionId.ToString("N"),
            session.SubjectHash,
            content.Consent.NoticeVersion,
            now,
            ct
        );
        if (id == Guid.Empty)
            throw new VisitorConversationException("VISITOR_UNAVAILABLE", 503);
        return id;
    }

    private async Task<string> IssueHandoffReferenceAsync(
        ConversationStoreDbContext db,
        VisitorLead lead,
        VisitorConversationOptions opts,
        DateTimeOffset now
    )
    {
        var token = Base64Url(RandomNumberGenerator.GetBytes(32));
        db.VisitorHandoffReferences.Add(
            new VisitorHandoffReference
            {
                ReferenceHash = Sha256Hex(token),
                TenantId = lead.TenantId,
                LeadId = lead.LeadId,
                CreatedAt = now,
                ExpiresAt = now.AddMinutes(opts.HandoffReferenceMinutes),
            }
        );
        await Task.CompletedTask;
        if (opts.HandoffOpenBaseUrl.Length > 0)
            return $"{opts.HandoffOpenBaseUrl.TrimEnd('/')}/{token}/open";
        var separator = opts.HandoffBaseUrl.Contains('?') ? '&' : '?';
        return $"{opts.HandoffBaseUrl}{separator}lead={token}";
    }

    private static VisitorReply Finalize(
        VisitorReply reply,
        VisitorConversationOptions opts,
        string? handoffUrl
    )
    {
        _ = opts;
        var blocks = reply
            .Blocks.Select(block =>
                block.Type == "LINK" && block.Url == VisitorStateMachine.HandoffUrlToken
                    ? block with
                    {
                        Url = handoffUrl ?? string.Empty,
                    }
                    : block
            )
            .Where(block => !(block.Type == "LINK" && string.IsNullOrEmpty(block.Url)))
            .ToList();
        return reply with { Blocks = blocks };
    }

    // ── Helpers ─────────────────────────────────────────────────────────────────────────────────

    private VisitorContentSet ResolveContent(Guid tenantId)
    {
        try
        {
            return contents.Get(tenantId);
        }
        catch (VisitorContentException exception)
        {
            logger.LogError("visitor.content.unavailable reason={Reason}", exception.Reason);
            throw new VisitorConversationException("VISITOR_CONTENT_UNAVAILABLE", 503);
        }
    }

    private int RetentionDays(Guid tenantId, string channel)
    {
        var lead = leadOptions.CurrentValue;
        return channel == VisitorChannels.Simulation
            ? lead.SimulationRetentionDays
            : lead.RetentionDaysFor(tenantId);
    }

    private async Task EnforceLimitsAsync(
        ConversationStoreDbContext db,
        VisitorSession session,
        VisitorConversationOptions opts,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        if (
            session.Channel == VisitorChannels.Simulation
            && session.TurnCount >= opts.SimulatorMaxTurnsPerSession
        )
            throw new VisitorConversationException("VISITOR_RATE_LIMITED", 429, 3_600);
        var windowStart = now - Minute;
        var recent = await db.VisitorTurns.CountAsync(
            value =>
                value.SessionId == session.SessionId
                && value.CreatedAt > windowStart
                && value.Sequence > 0,
            ct
        );
        if (recent >= opts.MessagesPerVisitorPerMinute)
            throw new VisitorConversationException("VISITOR_RATE_LIMITED", 429, 30);
        var tenantRecent = await db.VisitorTurns.CountAsync(
            value =>
                value.TenantId == session.TenantId
                && value.CreatedAt > windowStart
                && value.Sequence > 0,
            ct
        );
        if (tenantRecent >= opts.MessagesPerTenantPerMinute)
            throw new VisitorConversationException("VISITOR_RATE_LIMITED", 429, 30);
    }

    private async Task<VisitorSessionView> ViewAsync(
        ConversationStoreDbContext db,
        VisitorSession session,
        bool created,
        CancellationToken ct
    )
    {
        var lead = await LoadLeadAsync(db, session, ct);
        var last = await db
            .VisitorTurns.AsNoTracking()
            .Where(value => value.SessionId == session.SessionId)
            .OrderByDescending(value => value.Sequence)
            .FirstOrDefaultAsync(ct);
        return new VisitorSessionView(
            session.SessionId,
            session.Channel,
            session.State,
            session.Outcome,
            Captured(lead),
            last is null ? null : VisitorReply.FromJson(last.ReplyJson),
            created
        );
    }

    private static async Task<VisitorLead?> LoadLeadAsync(
        ConversationStoreDbContext db,
        VisitorSession session,
        CancellationToken ct
    ) =>
        await db.VisitorLeads.FirstOrDefaultAsync(
            value =>
                value.TenantId == session.TenantId
                && value.SubjectHash == session.SubjectHash
                && value.Status != VisitorLeadStatus.Converted,
            ct
        );

    private static VisitorSnapshot Snapshot(VisitorSession session, VisitorLead? lead) =>
        new()
        {
            State = session.State,
            Domain = lead?.BusinessDomain,
            BusinessText = lead?.BusinessText,
            City = lead?.City,
            Goal = lead?.GoalCode,
            HasName = lead?.ContactNameProtected is not null,
            HasEmail = lead?.ContactEmailProtected is not null,
            ConsentGiven = session.ConsentAt is not null,
            Tapped = lead is { Status: VisitorLeadStatus.Intent or VisitorLeadStatus.Converted },
            Turns = session.TurnCount,
            TurnsToFirstValue = session.TurnsToFirstValue,
            Nudges = session.Nudges,
        };

    private static VisitorCaptured Captured(VisitorLead? lead) =>
        new(
            lead?.BusinessDomain,
            lead?.City,
            lead?.GoalCode,
            lead?.ContactNameProtected is not null,
            lead?.ContactEmailProtected is not null
        );

    private void EmitTelemetry(
        VisitorSession session,
        string priorState,
        string reason,
        long startedTimestamp,
        int status
    ) =>
        telemetry.Response(
            session.Channel,
            status,
            reason,
            session.State,
            priorState,
            session.ContentVersion,
            TimeProvider.System.GetElapsedTime(startedTimestamp).TotalMilliseconds,
            Guid.NewGuid()
        );

    private static async Task LockAsync(
        ConversationStoreDbContext db,
        string key,
        CancellationToken ct
    )
    {
        if (db.Database.IsNpgsql())
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT pg_advisory_xact_lock(hashtextextended({key}, 0))",
                ct
            );
    }

    public static string SubjectHash(string scope, string subject) =>
        Sha256Hex($"waooaw-visitor:{scope}:{subject}");

    public static string CanonicalRequest(VisitorInput input) =>
        JsonSerializer.Serialize(
            new
            {
                kind = input.Kind,
                text = input.Text?.Trim(),
                choice = input.ChoiceId,
            }
        );

    public static string Cursor(long sequence) =>
        Base64Url(Encoding.UTF8.GetBytes($"vc1:{sequence}"));

    public static bool TryParseCursor(string cursor, out long sequence)
    {
        sequence = 0;
        try
        {
            var text = Encoding.UTF8.GetString(FromBase64Url(cursor));
            return text.StartsWith("vc1:", StringComparison.Ordinal)
                && long.TryParse(text.AsSpan(4), out sequence)
                && sequence >= 0;
        }
        catch (FormatException)
        {
            return false;
        }
    }

    private static string Sha256Hex(string value) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));

    private static string Base64Url(byte[] bytes) =>
        Convert.ToBase64String(bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_');

    private static byte[] FromBase64Url(string value)
    {
        var padded = value.Replace('-', '+').Replace('_', '/');
        padded = padded.PadRight(padded.Length + ((4 - padded.Length % 4) % 4), '=');
        return Convert.FromBase64String(padded);
    }
}

public static class VisitorHours
{
    public static bool IsOpen(VisitorHoursContent hours, DateTimeOffset instant)
    {
        var zone = TimeZoneInfo.FindSystemTimeZoneById(hours.TimeZone);
        var local = TimeZoneInfo.ConvertTime(instant, zone).TimeOfDay;
        return local
                >= TimeSpan.Parse(hours.OpensAt, System.Globalization.CultureInfo.InvariantCulture)
            && local
                < TimeSpan.Parse(hours.ClosesAt, System.Globalization.CultureInfo.InvariantCulture);
    }
}
