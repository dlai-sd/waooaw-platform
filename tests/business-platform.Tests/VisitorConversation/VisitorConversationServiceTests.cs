// Implements: work-contracts/WC-135-requirements.yaml WC135-R001, WC135-R003, WC135-R007, WC135-R009, WC135-R010, WC135-R011, WC135-R014, WC135-R016
// Constitutional basis: C-009, C-023, C-026, C-048, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Visitor;
using Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.VisitorConversation;

internal sealed class VisitorClock : TimeProvider
{
    public DateTimeOffset Now { get; set; } = new(2026, 11, 19, 8, 0, 0, TimeSpan.Zero); // 13:30 IST, open

    public override DateTimeOffset GetUtcNow() => Now;
}

internal sealed class CountingEvidence : IWhatsAppRegistrationEvidenceGateway
{
    public int Consents { get; private set; }

    public Task<Guid> RecordGuestAdmissionAsync(
        Guid tenantId,
        string admissionId,
        string bindingDigest,
        DateTimeOffset occurredAt,
        CancellationToken cancellationToken
    ) => Task.FromResult(Guid.NewGuid());

    public Task<Guid> RecordGuestConsentAsync(
        Guid tenantId,
        string messageId,
        string bindingDigest,
        string noticeVersion,
        DateTimeOffset occurredAt,
        CancellationToken cancellationToken
    )
    {
        Consents++;
        return Task.FromResult(Guid.NewGuid());
    }

    public Task RecordAsync(
        Guid tenantId,
        string messageId,
        string phoneHmac,
        DateTimeOffset occurredAt,
        CancellationToken cancellationToken
    ) => throw new InvalidOperationException("Not used.");
}

internal sealed class FixedContent(VisitorContentSet? content) : IVisitorContentProvider
{
    public VisitorContentSet Get(Guid tenantId) =>
        content ?? throw new VisitorContentException("CONTENT_NOT_FOUND");
}

internal sealed class RecordingLogger<T> : ILogger<T>
{
    public List<string> Lines { get; } = [];

    public IDisposable? BeginScope<TState>(TState state)
        where TState : notnull => null;

    public bool IsEnabled(LogLevel logLevel) => true;

    public void Log<TState>(
        LogLevel logLevel,
        EventId eventId,
        TState state,
        Exception? exception,
        Func<TState, Exception?, string> formatter
    ) => Lines.Add(formatter(state, exception));
}

internal sealed class VisitorHarness
{
    public static readonly Guid Tenant = Guid.Parse("65797d6b-dc09-5e94-987b-02f365d457ef");

    public ConversationFitnessDbFactory Db { get; } = new($"visitor-{Guid.NewGuid():N}");
    public VisitorClock Clock { get; } = new();
    public CountingEvidence Evidence { get; } = new();
    public VisitorConversationOptions Options { get; }
    public VisitorLeadOptions LeadOptions { get; } = new();
    public RecordingLogger<VisitorTelemetry> TelemetryLog { get; } = new();
    public RecordingLogger<VisitorConversationService> ServiceLog { get; } = new();
    public VisitorFieldProtector Protector { get; }
    public VisitorConversationService Service { get; }

    public VisitorHarness(
        VisitorContentSet? content = null,
        Action<VisitorConversationOptions>? configure = null,
        bool noContent = false
    )
    {
        Options = new VisitorConversationOptions
        {
            Mode = VisitorMode.V2,
            SimulatorEnabled = true,
            SimulatorSecret = new string('s', 40),
            LocalKeys = new() { ["k1"] = new string('a', 40), ["k2"] = new string('b', 40) },
            LocalCurrentKeyVersion = "k1",
        };
        configure?.Invoke(Options);
        var monitor = new StaticOptionsMonitor<VisitorConversationOptions>(Options);
        Protector = new VisitorFieldProtector(new ConfigurationVisitorKeyRing(monitor));
        Service = new VisitorConversationService(
            Db,
            new FixedContent(noContent ? null : content ?? VisitorTestContent.Shipped()),
            Protector,
            monitor,
            new StaticOptionsMonitor<VisitorLeadOptions>(LeadOptions),
            Evidence,
            new VisitorTelemetry(TelemetryLog),
            Clock,
            ServiceLog
        );
    }

    public async Task<VisitorSessionView> OpenSimAsync(string subject = "sim-test-0001") =>
        await Service.OpenSessionAsync(
            Tenant,
            VisitorChannels.Simulation,
            subject,
            CancellationToken.None
        );

    public Task<VisitorTurnResult> SendAsync(Guid session, VisitorInput input, Guid? key = null) =>
        Service.SendAsync(Tenant, session, key ?? Guid.NewGuid(), input, CancellationToken.None);

    public async Task<VisitorTurnResult> JourneyToHandoffAsync(Guid session)
    {
        await SendAsync(session, VisitorInput.FromChoice(VisitorChoiceIds.ConsentYes));
        await SendAsync(session, VisitorInput.FromText("I run a dental clinic in Pune"));
        await SendAsync(session, VisitorInput.FromChoice("goal_more_bookings"));
        return await SendAsync(session, VisitorInput.FromChoice(VisitorChoiceIds.StartTrial));
    }
}

public sealed class VisitorConversationServiceTests
{
    [Fact]
    public async Task OpeningASimulationSessionReturnsTheConsentPromptAndResumesTheSameSubject()
    {
        var h = new VisitorHarness();
        var first = await h.OpenSimAsync();
        Assert.True(first.Created);
        Assert.Equal(VisitorStates.ConsentPending, first.State);
        Assert.Contains(first.Reply!.Blocks, block => block.Type == "CHOICES");
        var second = await h.OpenSimAsync();
        Assert.False(second.Created);
        Assert.Equal(first.SessionId, second.SessionId);
        Assert.NotEqual(first.SessionId, (await h.OpenSimAsync("sim-test-0002")).SessionId);
    }

    [Fact]
    public async Task OnlyEndpointChannelsCanOpenAndSimulationNeedsASubject()
    {
        var h = new VisitorHarness();
        var bad = await Assert.ThrowsAsync<VisitorConversationException>(() =>
            h.Service.OpenSessionAsync(
                VisitorHarness.Tenant,
                VisitorChannels.WhatsApp,
                "x",
                CancellationToken.None
            )
        );
        Assert.Equal(400, bad.Status);
        var missing = await Assert.ThrowsAsync<VisitorConversationException>(() =>
            h.Service.OpenSessionAsync(
                VisitorHarness.Tenant,
                VisitorChannels.Simulation,
                null,
                CancellationToken.None
            )
        );
        Assert.Equal("VISITOR_REQUEST_INVALID", missing.Code);
        var web1 = await h.Service.OpenSessionAsync(
            VisitorHarness.Tenant,
            VisitorChannels.Web,
            null,
            CancellationToken.None
        );
        var web2 = await h.Service.OpenSessionAsync(
            VisitorHarness.Tenant,
            VisitorChannels.Web,
            null,
            CancellationToken.None
        );
        Assert.NotEqual(web1.SessionId, web2.SessionId);
    }

    [Fact]
    public async Task AJourneyCapturesTheLeadAndStoresPersonalDataOnlyInProtectedForm()
    {
        var h = new VisitorHarness();
        var session = (await h.OpenSimAsync()).SessionId;
        var handoff = await h.JourneyToHandoffAsync(session);
        Assert.Equal(VisitorStates.Handoff, handoff.State);
        Assert.Equal(VisitorOutcomes.Lead, handoff.Outcome);
        Assert.Equal("dental_clinic", handoff.Captured.BusinessDomain);
        Assert.Equal("Pune", handoff.Captured.City);
        Assert.Equal("more_bookings", handoff.Captured.GoalCode);

        var contact = await h.SendAsync(
            session,
            VisitorInput.FromText("Rupali Khandge rupali@example.com")
        );
        Assert.True(contact.Captured.HasName && contact.Captured.HasEmail);

        await using var db = h.Db.CreateDbContext();
        var lead = await db.VisitorLeads.SingleAsync();
        Assert.StartsWith("v2.k1.", lead.ContactEmailProtected, StringComparison.Ordinal);
        Assert.StartsWith("v2.k1.", lead.ContactNameProtected, StringComparison.Ordinal);
        Assert.DoesNotContain(
            "rupali",
            lead.ContactEmailProtected,
            StringComparison.OrdinalIgnoreCase
        );
        Assert.DoesNotContain("Khandge", lead.ContactNameProtected, StringComparison.Ordinal);
        Assert.Equal(VisitorChannels.Simulation, lead.SourceChannel);
        Assert.Equal(0, h.Evidence.Consents);
        var turns = await db.VisitorTurns.Where(value => value.Sequence > 0).ToListAsync();
        Assert.All(
            turns.Where(turn => turn.VisitorTextProtected is not null),
            turn => Assert.StartsWith("v2.", turn.VisitorTextProtected, StringComparison.Ordinal)
        );
    }

    [Fact]
    public async Task RepeatedIdempotencyKeyReplaysAndAChangedBodyConflicts()
    {
        var h = new VisitorHarness();
        var session = (await h.OpenSimAsync()).SessionId;
        var key = Guid.NewGuid();
        var first = await h.SendAsync(
            session,
            VisitorInput.FromChoice(VisitorChoiceIds.ConsentYes),
            key
        );
        var replay = await h.SendAsync(
            session,
            VisitorInput.FromChoice(VisitorChoiceIds.ConsentYes),
            key
        );
        Assert.False(first.Replayed);
        Assert.True(replay.Replayed);
        Assert.Equal(first.MessageId, replay.MessageId);
        Assert.Equal(first.Reply.ToJson(), replay.Reply.ToJson());
        var conflict = await Assert.ThrowsAsync<VisitorConversationException>(() =>
            h.SendAsync(session, VisitorInput.FromText("something else"), key)
        );
        Assert.Equal(409, conflict.Status);
        await using var db = h.Db.CreateDbContext();
        Assert.Equal(1, (await db.VisitorSessions.SingleAsync()).TurnCount);
    }

    [Fact]
    public async Task TranscriptListsBothSidesInOrderAndDecryptsTheVisitorText()
    {
        var h = new VisitorHarness();
        var session = (await h.OpenSimAsync()).SessionId;
        await h.SendAsync(session, VisitorInput.FromChoice(VisitorChoiceIds.ConsentYes));
        await h.SendAsync(session, VisitorInput.FromText("I run a salon in Nashik"));
        var page = await h.Service.ListAsync(
            VisitorHarness.Tenant,
            session,
            null,
            100,
            CancellationToken.None
        );
        Assert.Equal(
            Enumerable
                .Range(1, page.Items.Count)
                .Select(index => (long)index)
                .Where(index => index > 0)
                .Count(),
            page.Items.Count
        );
        Assert.Equal("WAOOAW", page.Items[0].Role);
        Assert.Contains(
            page.Items,
            item => item.Role == "VISITOR" && item.Content?.Text == "I run a salon in Nashik"
        );
        var paged = await h.Service.ListAsync(
            VisitorHarness.Tenant,
            session,
            null,
            2,
            CancellationToken.None
        );
        Assert.NotNull(paged.NextCursor);
        var rest = await h.Service.ListAsync(
            VisitorHarness.Tenant,
            session,
            paged.NextCursor,
            100,
            CancellationToken.None
        );
        Assert.Equal(page.Items.Count, paged.Items.Count + rest.Items.Count);
        var bad = await Assert.ThrowsAsync<VisitorConversationException>(() =>
            h.Service.ListAsync(
                VisitorHarness.Tenant,
                session,
                "not-a-cursor",
                10,
                CancellationToken.None
            )
        );
        Assert.Equal(400, bad.Status);
    }

    [Fact]
    public async Task PerVisitorRateLimitReturnsRetryAfter()
    {
        var h = new VisitorHarness(configure: options => options.MessagesPerVisitorPerMinute = 2);
        var session = (await h.OpenSimAsync()).SessionId;
        await h.SendAsync(session, VisitorInput.FromChoice(VisitorChoiceIds.ConsentYes));
        await h.SendAsync(session, VisitorInput.FromText("a dental clinic in Pune"));
        var limited = await Assert.ThrowsAsync<VisitorConversationException>(() =>
            h.SendAsync(session, VisitorInput.FromChoice("goal_more_bookings"))
        );
        Assert.Equal(429, limited.Status);
        Assert.NotNull(limited.RetryAfterSeconds);
        h.Clock.Now = h.Clock.Now.AddMinutes(2);
        await h.SendAsync(session, VisitorInput.FromChoice("goal_more_bookings"));
    }

    [Fact]
    public async Task SimulatorCapsLimitTurnsPerSessionAndSessionsPerDay()
    {
        var h = new VisitorHarness(configure: options =>
        {
            options.SimulatorMaxTurnsPerSession = 2;
            options.SimulatorMaxSessionsPerDay = 2;
            options.MessagesPerVisitorPerMinute = 100;
        });
        var session = (await h.OpenSimAsync("sim-cap-0001")).SessionId;
        await h.SendAsync(session, VisitorInput.FromChoice(VisitorChoiceIds.ConsentYes));
        await h.SendAsync(session, VisitorInput.FromText("a dental clinic in Pune"));
        var turns = await Assert.ThrowsAsync<VisitorConversationException>(() =>
            h.SendAsync(session, VisitorInput.FromText("more"))
        );
        Assert.Equal(429, turns.Status);
        await h.OpenSimAsync("sim-cap-0002");
        var days = await Assert.ThrowsAsync<VisitorConversationException>(() =>
            h.OpenSimAsync("sim-cap-0003")
        );
        Assert.Equal(429, days.Status);
    }

    [Fact]
    public async Task StopThenStartRequiresConsentAgainAndStoppedVisitorsGetNoReply()
    {
        var h = new VisitorHarness();
        var session = (await h.OpenSimAsync()).SessionId;
        await h.SendAsync(session, VisitorInput.FromChoice(VisitorChoiceIds.ConsentYes));
        var stop = await h.SendAsync(session, VisitorInput.FromText("STOP"));
        Assert.Equal(VisitorStates.Stopped, stop.State);
        Assert.Equal(VisitorOutcomes.OptOut, stop.Outcome);
        var silent = await h.SendAsync(session, VisitorInput.FromText("hello?"));
        Assert.Empty(silent.Reply.Blocks);
        var resume = await h.SendAsync(session, VisitorInput.FromText("START"));
        Assert.Equal(VisitorStates.ConsentPending, resume.State);
        Assert.Contains(resume.Reply.Blocks, block => block.Type == "CHOICES");
        var back = await h.SendAsync(session, VisitorInput.FromChoice(VisitorChoiceIds.ConsentYes));
        Assert.Equal(VisitorStates.Discover, back.State);
    }

    [Fact]
    public async Task HandoffReferenceIsOpaqueSingleUseAndTurnsTheLeadIntoFullSuccess()
    {
        var h = new VisitorHarness();
        var session = (await h.OpenSimAsync()).SessionId;
        var handoff = await h.JourneyToHandoffAsync(session);
        var link = Assert.Single(handoff.Reply.Blocks, block => block.Type == "LINK");
        Assert.StartsWith(
            "https://cp.demo.waooaw.com/register?lead=",
            link.Url,
            StringComparison.Ordinal
        );
        var reference = link.Url![(link.Url!.IndexOf("lead=", StringComparison.Ordinal) + 5)..];
        Assert.DoesNotContain("dental", reference, StringComparison.OrdinalIgnoreCase);
        Assert.True(reference.Length >= 40);

        await using (var db = h.Db.CreateDbContext())
        {
            var stored = await db.VisitorHandoffReferences.SingleAsync();
            Assert.NotEqual(reference, stored.ReferenceHash);
            Assert.Equal(64, stored.ReferenceHash.Length);
        }
        Assert.True(
            await h.Service.TapHandoffAsync(
                VisitorHarness.Tenant,
                reference,
                CancellationToken.None
            )
        );
        Assert.False(
            await h.Service.TapHandoffAsync(
                VisitorHarness.Tenant,
                reference,
                CancellationToken.None
            )
        );
        Assert.False(
            await h.Service.TapHandoffAsync(
                VisitorHarness.Tenant,
                "unknown-reference-value",
                CancellationToken.None
            )
        );
        var view = await h.Service.GetSessionAsync(
            VisitorHarness.Tenant,
            session,
            CancellationToken.None
        );
        Assert.Equal(VisitorOutcomes.FullSuccess, view.Outcome);
        await using var after = h.Db.CreateDbContext();
        Assert.Equal(VisitorLeadStatus.Intent, (await after.VisitorLeads.SingleAsync()).Status);
    }

    [Fact]
    public async Task ExpiredHandoffReferenceRecordsNothing()
    {
        var h = new VisitorHarness(configure: options => options.HandoffReferenceMinutes = 10);
        var session = (await h.OpenSimAsync()).SessionId;
        var handoff = await h.JourneyToHandoffAsync(session);
        var url = handoff.Reply.Blocks.Single(block => block.Type == "LINK").Url!;
        h.Clock.Now = h.Clock.Now.AddMinutes(11);
        Assert.False(
            await h.Service.TapHandoffAsync(
                VisitorHarness.Tenant,
                url[(url.IndexOf("lead=", StringComparison.Ordinal) + 5)..],
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task DataRightsExportDecryptsAndDeletionRemovesEverything()
    {
        var h = new VisitorHarness();
        var session = (await h.OpenSimAsync()).SessionId;
        await h.JourneyToHandoffAsync(session);
        await h.SendAsync(session, VisitorInput.FromText("Rupali Khandge rupali@example.com"));
        var subject = VisitorConversationService.SubjectHash("sim", "sim-test-0001");
        var export = await h.Service.ExportSubjectLeadAsync(
            VisitorHarness.Tenant,
            subject,
            CancellationToken.None
        );
        Assert.Equal("rupali@example.com", export["email"]);
        Assert.Equal("Rupali Khandge", export["name"]);
        Assert.Equal("Pune", export["city"]);
        var deleted = await h.Service.DeleteSubjectDataAsync(
            VisitorHarness.Tenant,
            subject,
            CancellationToken.None
        );
        Assert.Equal(1, deleted.Leads);
        Assert.Equal(1, deleted.Sessions);
        Assert.True(deleted.Turns >= 4);
        await using var db = h.Db.CreateDbContext();
        Assert.Empty(db.VisitorLeads);
        Assert.Empty(db.VisitorSessions);
        Assert.Empty(db.VisitorTurns);
        Assert.Empty(db.VisitorHandoffReferences);
        Assert.Empty(
            await h.Service.ExportSubjectLeadAsync(
                VisitorHarness.Tenant,
                subject,
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task MissingContentFailsClosedWithoutAnyHardcodedFallback()
    {
        var h = new VisitorHarness(noContent: true);
        var failure = await Assert.ThrowsAsync<VisitorConversationException>(() =>
            h.OpenSimAsync()
        );
        Assert.Equal("VISITOR_CONTENT_UNAVAILABLE", failure.Code);
        Assert.Equal(503, failure.Status);
    }

    [Fact]
    public async Task InvalidReplyDefinitionFailsClosed()
    {
        var content = VisitorTestContent.Shipped();
        var broken = content with
        {
            ShowValue = content.ShowValue with { StartTrialLabel = "This label is much too long" },
        };
        var h = new VisitorHarness(broken);
        var session = (await h.OpenSimAsync()).SessionId;
        await h.SendAsync(session, VisitorInput.FromChoice(VisitorChoiceIds.ConsentYes));
        await h.SendAsync(session, VisitorInput.FromText("a dental clinic in Pune"));
        var failure = await Assert.ThrowsAsync<VisitorConversationException>(() =>
            h.SendAsync(session, VisitorInput.FromChoice("goal_more_bookings"))
        );
        Assert.Equal("VISITOR_CONTENT_UNAVAILABLE", failure.Code);
    }

    [Fact]
    public async Task WebChannelRecordsConsentEvidenceAndRespectsOpeningHours()
    {
        var h = new VisitorHarness();
        var session = (
            await h.Service.OpenSessionAsync(
                VisitorHarness.Tenant,
                VisitorChannels.Web,
                null,
                CancellationToken.None
            )
        ).SessionId;
        h.Clock.Now = new DateTimeOffset(2026, 11, 19, 20, 0, 0, TimeSpan.Zero); // 01:30 IST, closed
        var closed = await h.SendAsync(
            session,
            VisitorInput.FromChoice(VisitorChoiceIds.ConsentYes)
        );
        Assert.Equal(VisitorTestContent.Shipped().Fixed.ClosedNotice, closed.Reply.PlainText());
        Assert.Equal(VisitorStates.ConsentPending, closed.State);
        Assert.Equal(0, h.Evidence.Consents);
        h.Clock.Now = new DateTimeOffset(2026, 11, 19, 8, 0, 0, TimeSpan.Zero);
        var open = await h.SendAsync(session, VisitorInput.FromChoice(VisitorChoiceIds.ConsentYes));
        Assert.Equal(VisitorStates.Discover, open.State);
        Assert.Equal(1, h.Evidence.Consents);
    }

    [Fact]
    public async Task LogsAndMetricsNeverContainMessageTextOrPersonalData()
    {
        var h = new VisitorHarness();
        var session = (await h.OpenSimAsync()).SessionId;
        await h.JourneyToHandoffAsync(session);
        await h.SendAsync(session, VisitorInput.FromText("Rupali Khandge rupali@example.com"));
        var everything = string.Join("\n", h.TelemetryLog.Lines.Concat(h.ServiceLog.Lines));
        Assert.NotEmpty(h.TelemetryLog.Lines);
        Assert.Contains("visitor.response", everything, StringComparison.Ordinal);
        foreach (
            var secret in new[] { "rupali", "Khandge", "dental clinic in Pune", "sim-test-0001" }
        )
            Assert.DoesNotContain(secret, everything, StringComparison.OrdinalIgnoreCase);
        Assert.Matches(@"status=200 reason=\w+ state=\w+ priorState=\w+", h.TelemetryLog.Lines[0]);
    }

    [Fact]
    public async Task WhatsAppMessagesShareTheSameCoreAndKeepTheRawPhoneOnlyInProtectedForm()
    {
        var h = new VisitorHarness();
        var subject = VisitorConversationService.SubjectHash("wa", "919876543210");
        var consent = Guid.NewGuid();
        var first = await h.Service.HandleWhatsAppAsync(
            VisitorHarness.Tenant,
            subject,
            "+919876543210",
            consent,
            VisitorInput.FromText("1"),
            CancellationToken.None
        );
        Assert.Equal(VisitorStates.ProfessionalCard, first.State);
        Assert.Contains("Digital Marketing Professional", first.Reply.PlainText(), StringComparison.Ordinal);
        var second = await h.Service.HandleWhatsAppAsync(
            VisitorHarness.Tenant,
            subject,
            "+919876543210",
            consent,
            VisitorInput.FromText("2"),
            CancellationToken.None
        );
        Assert.Equal(VisitorStates.Handoff, second.State);
        var trial = second;
        Assert.Contains(
            trial.Reply.Blocks,
            block =>
                block.Type == "LINK" && block.Url!.StartsWith("https://", StringComparison.Ordinal)
        );

        await using var db = h.Db.CreateDbContext();
        var lead = await db.VisitorLeads.SingleAsync();
        Assert.Equal(consent, lead.ConsentReference);
        Assert.StartsWith("v2.k1.", lead.PhoneProtected, StringComparison.Ordinal);
        Assert.DoesNotContain("9876543210", lead.PhoneProtected, StringComparison.Ordinal);
        Assert.Empty(db.VisitorTurns);
        var export = await h.Service.ExportSubjectLeadAsync(
            VisitorHarness.Tenant,
            subject,
            CancellationToken.None
        );
        Assert.Equal("+919876543210", export["phone"]);

        await h.Service.RecordWhatsAppStopAsync(
            VisitorHarness.Tenant,
            subject,
            CancellationToken.None
        );
        await using var stopped = h.Db.CreateDbContext();
        Assert.Equal(VisitorOutcomes.OptOut, (await stopped.VisitorSessions.SingleAsync()).Outcome);
    }
}
