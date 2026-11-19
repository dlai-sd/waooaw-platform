// Implements: work-contracts/WC-135-requirements.yaml WC135-R005, WC135-R006, WC135-R008, WC135-R009
// Constitutional basis: C-009, C-023, C-026, C-048, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Visitor;
using Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.VisitorConversation;

public sealed class VisitorPurgeTests
{
    private sealed class PgFactory(string connectionString)
        : IDbContextFactory<ConversationStoreDbContext>
    {
        public ConversationStoreDbContext CreateDbContext() =>
            new(
                new DbContextOptionsBuilder<ConversationStoreDbContext>()
                    .UseNpgsql(connectionString)
                    .Options
            );
    }

    [Fact]
    public async Task PurgeRemovesOnlyExpiredDataAndIsIdempotent()
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        var factory = new PgFactory(postgres.GetConnectionString());
        await using (var setup = factory.CreateDbContext())
            await setup.Database.EnsureCreatedAsync();

        var tenant = Guid.NewGuid();
        var now = new DateTimeOffset(2026, 11, 19, 6, 0, 0, TimeSpan.Zero);
        var oldLead = Guid.NewGuid();
        var recentLead = Guid.NewGuid();
        var oldSimulationLead = Guid.NewGuid();
        var convertedLead = Guid.NewGuid();
        var oldSession = Guid.NewGuid();
        var recentSession = Guid.NewGuid();
        var expiredReferenceOnRecentLead = new string('e', 64);
        var oldLeadReference = new string('a', 64);

        await using (var seed = factory.CreateDbContext())
        {
            VisitorLead MakeLead(Guid id, string channel, string status, int ageDays) =>
                new()
                {
                    LeadId = id,
                    TenantId = tenant,
                    SubjectHash = new string('c', 64),
                    SourceChannel = channel,
                    Status = status,
                    ConsentReference = Guid.NewGuid(),
                    CreatedAt = now.AddDays(-ageDays),
                    UpdatedAt = now.AddDays(-ageDays),
                };
            seed.VisitorLeads.AddRange(
                MakeLead(oldLead, VisitorChannels.WhatsApp, VisitorLeadStatus.Open, 100),
                MakeLead(recentLead, VisitorChannels.WhatsApp, VisitorLeadStatus.Intent, 10),
                MakeLead(oldSimulationLead, VisitorChannels.Simulation, VisitorLeadStatus.Open, 8),
                MakeLead(convertedLead, VisitorChannels.WhatsApp, VisitorLeadStatus.Converted, 200)
            );
            seed.VisitorHandoffReferences.AddRange(
                new VisitorHandoffReference
                {
                    ReferenceHash = oldLeadReference,
                    TenantId = tenant,
                    LeadId = oldLead,
                    CreatedAt = now.AddDays(-100),
                    ExpiresAt = now.AddDays(1),
                },
                new VisitorHandoffReference
                {
                    ReferenceHash = expiredReferenceOnRecentLead,
                    TenantId = tenant,
                    LeadId = recentLead,
                    CreatedAt = now.AddDays(-9),
                    ExpiresAt = now.AddDays(-1),
                }
            );
            VisitorSession MakeSession(Guid id, int ageDays) =>
                new()
                {
                    SessionId = id,
                    TenantId = tenant,
                    SubjectHash = Guid.NewGuid().ToString("N") + Guid.NewGuid().ToString("N"),
                    Channel = VisitorChannels.WhatsApp,
                    ContentVersion = "waooaw-demo@1.0.0",
                    CreatedAt = now.AddDays(-ageDays),
                    UpdatedAt = now.AddDays(-ageDays),
                };
            seed.VisitorSessions.AddRange(
                MakeSession(oldSession, 100),
                MakeSession(recentSession, 1)
            );
            seed.VisitorTurns.AddRange(
                new VisitorTurn
                {
                    SessionId = oldSession,
                    Sequence = 0,
                    TenantId = tenant,
                    MessageId = Guid.NewGuid(),
                    IdempotencyKey = Guid.NewGuid(),
                    RequestHash = new string('d', 64),
                    CreatedAt = now.AddDays(-100),
                },
                new VisitorTurn
                {
                    SessionId = recentSession,
                    Sequence = 0,
                    TenantId = tenant,
                    MessageId = Guid.NewGuid(),
                    IdempotencyKey = Guid.NewGuid(),
                    RequestHash = new string('d', 64),
                    CreatedAt = now.AddDays(-1),
                }
            );
            seed.VisitorRenderHints.AddRange(
                new VisitorRenderHint
                {
                    TenantId = tenant,
                    MessageId = Guid.NewGuid(),
                    CreatedAt = now.AddDays(-3),
                },
                new VisitorRenderHint
                {
                    TenantId = tenant,
                    MessageId = Guid.NewGuid(),
                    CreatedAt = now.AddHours(-1),
                }
            );
            await seed.SaveChangesAsync();
        }

        var options = new VisitorLeadOptions
        {
            RetentionDays = 90,
            SimulationRetentionDays = 7,
            PurgeBatchSize = 1,
        };
        var purger = new VisitorLeadPurger(
            factory,
            new StaticOptionsMonitor<VisitorLeadOptions>(options),
            new VisitorClock { Now = now },
            NullLogger<VisitorLeadPurger>.Instance
        );

        var first = await purger.PurgeAsync(tenant, CancellationToken.None);
        Assert.True(first.Ran);
        Assert.Equal(2, first.Leads);
        Assert.Equal(1, first.Sessions);
        Assert.Equal(1, first.HandoffReferences);

        await using (var verify = factory.CreateDbContext())
        {
            Assert.Equal(
                new[] { convertedLead, recentLead }.Order(),
                (await verify.VisitorLeads.Select(lead => lead.LeadId).ToListAsync()).Order()
            );
            Assert.Equal(recentSession, (await verify.VisitorSessions.SingleAsync()).SessionId);
            Assert.Equal(recentSession, (await verify.VisitorTurns.SingleAsync()).SessionId);
            Assert.Empty(await verify.VisitorHandoffReferences.ToListAsync());
            Assert.Equal(1, await verify.VisitorRenderHints.CountAsync());
        }

        var second = await purger.PurgeAsync(tenant, CancellationToken.None);
        Assert.Equal(new VisitorPurgeResult(true, 0, 0, 0), second);

        // A shorter retention takes effect at the next run without any restart.
        options.RetentionDays = 5;
        options.TenantRetentionDays[tenant] = 5;
        Assert.Equal(1, (await purger.PurgeAsync(tenant, CancellationToken.None)).Leads);
    }
}

public sealed class VisitorContentProviderTests
{
    private static FileVisitorContentProvider Provider(VisitorConversationOptions options) =>
        new(
            new StaticOptionsMonitor<VisitorConversationOptions>(options),
            NullLogger<FileVisitorContentProvider>.Instance
        );

    [Fact]
    public void ShippedContentLoadsOnceAndIsCached()
    {
        var provider = Provider(new VisitorConversationOptions { Mode = VisitorMode.V2 });
        var first = provider.Get(Guid.NewGuid());
        Assert.Equal("waooaw-demo", first.ContentId);
        Assert.Same(first, provider.Get(Guid.NewGuid()));
    }

    [Theory]
    [InlineData("Not-Valid", "CONTENT_ID_INVALID")]
    [InlineData("../escape", "CONTENT_ID_INVALID")]
    [InlineData("does-not-exist", "CONTENT_NOT_FOUND")]
    public void BadContentIdsFailClosed(string id, string reason)
    {
        var tenant = Guid.NewGuid();
        var provider = Provider(
            new VisitorConversationOptions
            {
                Mode = VisitorMode.V2,
                TenantContentIds = new() { [tenant] = id },
            }
        );
        Assert.Equal(
            reason,
            Assert.Throws<VisitorContentException>(() => provider.Get(tenant)).Reason
        );
    }
}

[Collection("VisitorGuestCopy")]
public sealed class GuestCopyTests
{
    [Fact]
    public async Task InitializerAppliesV2ContentOnlyInV2AndResetsOtherwise()
    {
        var content = VisitorTestContent.Shipped();
        var v2 = new StaticOptionsMonitor<VisitorConversationOptions>(
            new() { Mode = VisitorMode.V2 }
        );
        var legacy = new StaticOptionsMonitor<VisitorConversationOptions>(
            new() { Mode = VisitorMode.Legacy }
        );
        var leads = new StaticOptionsMonitor<VisitorLeadOptions>(new() { RetentionDays = 45 });
        try
        {
            await new VisitorGuestCopyInitializer(
                new FixedContent(content),
                v2,
                leads,
                NullLogger<VisitorGuestCopyInitializer>.Instance
            ).StartAsync(CancellationToken.None);
            var active = GuestCopyRegistry.Current;
            Assert.True(active.IsV2);
            Assert.Contains("45 days", active.Notice);
            Assert.Equal(content.Consent.NoticeVersion, WhatsAppGuestConsent.ActiveNoticeVersion);
            Assert.True(WhatsAppGuestConsent.IsPreConsentNotice(active.ResumeNotice));
            Assert.True(WhatsAppGuestConsent.IsAcceptance(active.YesLabel, null));
            Assert.True(WhatsAppGuestConsent.IsAcceptance("ignored", VisitorChoiceIds.ConsentYes));
            Assert.True(
                WhatsAppGuestOperatingHours.IsOpen(
                    new DateTimeOffset(2026, 11, 19, 6, 0, 0, TimeSpan.Zero)
                )
            );
            Assert.False(
                WhatsAppGuestOperatingHours.IsOpen(
                    new DateTimeOffset(2026, 11, 19, 17, 0, 0, TimeSpan.Zero)
                )
            );

            await new VisitorGuestCopyInitializer(
                new FixedContent(content),
                legacy,
                leads,
                NullLogger<VisitorGuestCopyInitializer>.Instance
            ).StartAsync(CancellationToken.None);
            Assert.False(GuestCopyRegistry.Current.IsV2);
            Assert.Equal(WhatsAppGuestConsent.Notice, GuestCopyRegistry.Current.Notice);
            Assert.False(WhatsAppGuestConsent.IsAcceptance("ignored", VisitorChoiceIds.ConsentYes));

            await Assert.ThrowsAsync<VisitorContentException>(() =>
                new VisitorGuestCopyInitializer(
                    new FixedContent(null),
                    v2,
                    leads,
                    NullLogger<VisitorGuestCopyInitializer>.Instance
                ).StartAsync(CancellationToken.None)
            );
        }
        finally
        {
            GuestCopyRegistry.Reset();
        }
    }

    [Fact]
    public void ListRepliesRenderWithinWhatsAppLimitsAndOtherwiseFallBack()
    {
        var rows = Enumerable
            .Range(1, 3)
            .Select(index => new VisitorListRow($"r{index}", $"Row {index}", "Short description"))
            .ToArray();
        var reply = new VisitorReply
        {
            Blocks =
            [
                VisitorReplyBlock.TextBlock("Pick one"),
                new VisitorReplyBlock
                {
                    Type = "LIST",
                    ListTitle = "Choose",
                    Rows = rows,
                },
            ],
        };
        var rendered = System.Text.Json.JsonSerializer.SerializeToNode(
            VisitorWhatsAppRenderer.Interactive(reply)
        )!;
        Assert.Equal("list", rendered["interactive"]!["type"]!.GetValue<string>());
        Assert.Equal(
            3,
            rendered["interactive"]!["action"]!["sections"]![0]!["rows"]!.AsArray().Count
        );

        var tooLongBody = reply with
        {
            Blocks = [VisitorReplyBlock.TextBlock(new string('x', 1100)), reply.Blocks[1]],
        };
        Assert.Null(VisitorWhatsAppRenderer.Interactive(tooLongBody));
        Assert.Null(
            VisitorWhatsAppRenderer.Interactive(VisitorReply.Empty(VisitorStates.Discover, "x"))
        );
        Assert.Null(VisitorWhatsAppRenderer.ParseReply("not json"));
        var insecure = new VisitorReply
        {
            Blocks =
            [
                VisitorReplyBlock.TextBlock("Go"),
                new VisitorReplyBlock
                {
                    Type = "LINK",
                    Label = "Open",
                    Url = "http://example.test",
                },
            ],
        };
        Assert.Null(VisitorWhatsAppRenderer.Interactive(insecure));
    }
}
