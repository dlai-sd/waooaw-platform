// Implements: architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md §10.2, §25.2 WC120-P2, WC120-P4
// Constitutional basis: C-005, C-023, C-026, C-059, C-063

using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using OpenTelemetry;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed class WhatsAppCloudProviderAdapter(
    IHttpClientFactory clients,
    IWhatsAppProviderCredentials credentials,
    IWhatsAppCapabilityGate capability,
    IDbContextFactory<ConversationStoreDbContext> conversations,
    ConversationStopFence stopFence,
    WhatsAppOutboxService outboxService,
    WhatsAppTrafficBudget budget,
    TimeProvider clock,
    IOptionsMonitor<WhatsAppJourneyOptions> channelOptions,
    IOptions<Wc120ConversationOptions> conversationOptions
) : IWhatsAppProviderAdapter
{
    private static readonly JsonSerializerOptions CanonicalBlockJson = new()
    {
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
    };

    public async Task<WhatsAppDispatchObservation> DispatchAsync(
        WhatsAppProviderDispatchRequest request,
        CancellationToken cancellationToken
    )
    {
        RequireDispatchEnabled();
        var authority = capability.RequireActive(clock.GetUtcNow());
        if (request.Environment != authority.Environment || request.TenantId != authority.TenantId)
            throw new WhatsAppCapabilityUnavailableException("TENANT_DENIED");

        await using var db = await conversations.CreateDbContextAsync(cancellationToken);
        var outbox = await db
            .ConversationOutbox.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.OutboxId == request.OutboxId
                    && value.Environment == request.Environment
                    && value.TenantId == request.TenantId
                    && value.RelationshipId == request.RelationshipId
                    && value.ConversationId == request.ConversationId
                    && value.Sequence == request.Sequence
                    && value.PayloadReference == request.PayloadReference
                    && value.PayloadDigest == request.PayloadDigest
                    && value.AttemptNumber == request.AttemptNumber
                    && value.State == "DISPATCHING",
                cancellationToken
            );
        if (outbox is null || !Guid.TryParse(outbox.AggregateId, out var messageId))
            throw new WhatsAppCapabilityUnavailableException("CANONICAL_MESSAGE_REQUIRED");
        if (outbox.CreatedAt < authority.StartsAt || outbox.CreatedAt >= authority.ExpiresAt)
            throw new WhatsAppCapabilityUnavailableException("OUTBOUND_AUTHORITY_WINDOW_DENIED");
        capability.RequireRecipient(
            request.TenantId,
            outbox.RecipientBindingDigest,
            clock.GetUtcNow()
        );

        var message = await db
            .Messages.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.MessageId == messageId
                    && value.Environment == request.Environment
                    && value.TenantId == request.TenantId
                    && value.RelationshipId == request.RelationshipId
                    && value.ConversationId == request.ConversationId
                    && value.Sequence == request.Sequence,
                cancellationToken
            );
        if (message is null)
            throw new WhatsAppCapabilityUnavailableException("CANONICAL_MESSAGE_REQUIRED");
        string text;
        try
        {
            using var content = JsonDocument.Parse(message.ContentJson);
            if (
                content.RootElement.ValueKind != JsonValueKind.Array
                || content.RootElement.GetArrayLength() != 1
            )
                throw new WhatsAppCapabilityUnavailableException("MESSAGE_PROJECTION_DENIED");
            var block = content.RootElement[0];
            if (
                block.ValueKind != JsonValueKind.Object
                || block
                    .EnumerateObject()
                    .Select(property => property.Name)
                    .Distinct(StringComparer.Ordinal)
                    .Count() != block.EnumerateObject().Count()
            )
                throw new WhatsAppCapabilityUnavailableException("MESSAGE_PROJECTION_DENIED");
            var canonical = block.Deserialize<ConversationTextBlockV1>(CanonicalBlockJson);
            if (
                canonical is null
                || canonical.SchemaVersion != "1.0"
                || canonical.BlockType != "TEXT"
                || string.IsNullOrWhiteSpace(canonical.Text)
                || canonical.Text.Length > 4096
            )
                throw new WhatsAppCapabilityUnavailableException("MESSAGE_PROJECTION_DENIED");
            text = canonical.Text;
        }
        catch (JsonException)
        {
            throw new WhatsAppCapabilityUnavailableException("MESSAGE_PROJECTION_DENIED");
        }

        var protectedValues = await credentials.ReadAsync(cancellationToken);
        var configured = conversationOptions.Value;
        if (
            configured.Environment != request.Environment
            || configured.AppBindingDigest != Hash(protectedValues.Binding.AppId)
            || configured.WabaBindingDigest != Hash(protectedValues.Binding.WabaId)
            || configured.RecipientBindingDigest != Hash(protectedValues.Binding.PhoneNumberId)
        )
            throw new WhatsAppCapabilityUnavailableException("PROVIDER_BINDING_DENIED");
        WhatsAppTemplateProjection? template = null;
        string[] parameters = [];
        if (outbox.TemplateName is not null)
        {
            var options = channelOptions.CurrentValue;
            var identity = string.Join(
                ':',
                outbox.TemplateName,
                outbox.TemplateVersion,
                outbox.TemplateLocale,
                outbox.TemplateCategory
            );
            var candidates = options
                .TemplateProjections.Where(value =>
                    value.Name == outbox.TemplateName
                    && value.Version == outbox.TemplateVersion
                    && value.Locale == outbox.TemplateLocale
                    && value.Category == outbox.TemplateCategory
                )
                .ToArray();
            if (
                !options.ApprovedTemplates.Contains(identity, StringComparer.Ordinal)
                || candidates.Length != 1
            )
                throw new WhatsAppCapabilityUnavailableException("TEMPLATE_PROJECTION_REQUIRED");
            template = candidates[0];
            parameters = template.Project(text);
        }
        capability.RequireRecipient(
            request.TenantId,
            protectedValues.Binding.RecipientBindingDigest,
            clock.GetUtcNow()
        );
        await stopFence.ThrowIfLatchedAsync(
            request.TenantId,
            request.RelationshipId,
            cancellationToken
        );
        if (protectedValues.ValidUntil <= clock.GetUtcNow())
            throw new WhatsAppCapabilityUnavailableException("PROVIDER_AUTHORITY_EXPIRED");
        var reservedAuthority = await budget.ReserveAsync(
            request,
            protectedValues.Binding.RecipientBindingDigest,
            cancellationToken
        );

        using var suppression = SuppressInstrumentationScope.Begin();
        using var client = clients.CreateClient("WhatsAppProtected");
        using var submission = new HttpRequestMessage(
            HttpMethod.Post,
            $"https://graph.facebook.com/{protectedValues.Binding.ApiVersion}"
                + $"/{protectedValues.Binding.PhoneNumberId}/messages"
        );
        submission.Headers.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            protectedValues.AccessToken
        );
        submission.Content = template is null
            ? JsonContent.Create(
                new
                {
                    messaging_product = "whatsapp",
                    recipient_type = "individual",
                    to = protectedValues.Binding.RecipientPhoneNumber.TrimStart('+'),
                    type = "text",
                    text = new { preview_url = false, body = text },
                    biz_opaque_callback_data = request.OutboxId.ToString("D"),
                }
            )
            : JsonContent.Create(
                new
                {
                    messaging_product = "whatsapp",
                    recipient_type = "individual",
                    to = protectedValues.Binding.RecipientPhoneNumber.TrimStart('+'),
                    type = "template",
                    template = new
                    {
                        name = template.Name,
                        language = new { code = template.Locale },
                        components = parameters.Length == 0
                            ? Array.Empty<object>()
                            : new object[]
                            {
                                new
                                {
                                    type = "body",
                                    parameters = parameters
                                        .Select(value => new { type = "text", text = value })
                                        .ToArray(),
                                },
                            },
                    },
                    biz_opaque_callback_data = request.OutboxId.ToString("D"),
                }
            );
        // Re-evaluate the exact authority after protected reads and immediately before egress.
        RequireDispatchEnabled();
        capability.RequireRecipient(
            request.TenantId,
            protectedValues.Binding.RecipientBindingDigest,
            clock.GetUtcNow()
        );
        if (capability.RequireActive(clock.GetUtcNow()) != reservedAuthority)
            throw new WhatsAppCapabilityUnavailableException("ACTIVATION_CHANGED");
        await stopFence.ThrowIfLatchedAsync(
            request.TenantId,
            request.RelationshipId,
            cancellationToken
        );
        if (protectedValues.ValidUntil <= clock.GetUtcNow())
            throw new WhatsAppCapabilityUnavailableException("PROVIDER_AUTHORITY_EXPIRED");
        if (
            !await outboxService.IsCurrentlyEligibleAsync(
                outbox,
                clock.GetUtcNow(),
                cancellationToken
            )
        )
            throw new WhatsAppCapabilityUnavailableException("RECIPIENT_ELIGIBILITY_REVOKED");
        try
        {
            using var response = await WhatsAppKeyVaultCredentials.ReadJsonAsync(
                client,
                submission,
                cancellationToken
            );
            var root = response.RootElement;
            if (
                root.ValueKind != JsonValueKind.Object
                || !root.TryGetProperty("messages", out var messages)
                || messages.ValueKind != JsonValueKind.Array
                || messages.GetArrayLength() != 1
                || messages[0].ValueKind != JsonValueKind.Object
                || !messages[0].TryGetProperty("id", out var id)
                || id.ValueKind != JsonValueKind.String
                || string.IsNullOrWhiteSpace(id.GetString())
                || id.GetString()!.Length > 1024
            )
                return Observation(request, "UNKNOWN", "", clock.GetUtcNow());
            return Observation(request, "PROVIDER_ACCEPTED", id.GetString()!, clock.GetUtcNow());
        }
        catch (WhatsAppCapabilityUnavailableException)
        {
            return Observation(request, "UNKNOWN", "", clock.GetUtcNow());
        }
        catch (JsonException)
        {
            return Observation(request, "UNKNOWN", "", clock.GetUtcNow());
        }
        catch (HttpRequestException)
        {
            return Observation(request, "UNKNOWN", "", clock.GetUtcNow());
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            return Observation(request, "UNKNOWN", "", clock.GetUtcNow());
        }
    }

    public async Task<WhatsAppDispatchObservation> ReconcileAsync(
        WhatsAppProviderDispatchRequest request,
        CancellationToken cancellationToken
    )
    {
        capability.RequireActive(clock.GetUtcNow());
        await using var db = await conversations.CreateDbContextAsync(cancellationToken);
        var outbox =
            await db
                .ConversationOutbox.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.OutboxId == request.OutboxId
                        && value.Environment == request.Environment
                        && value.TenantId == request.TenantId
                        && value.RelationshipId == request.RelationshipId,
                    cancellationToken
                )
            ?? throw new WhatsAppCapabilityUnavailableException("CANONICAL_MESSAGE_REQUIRED");
        capability.RequireRecipient(
            request.TenantId,
            outbox.RecipientBindingDigest,
            clock.GetUtcNow()
        );
        if (!Guid.TryParse(outbox.AggregateId, out var messageId))
            throw new WhatsAppCapabilityUnavailableException("CANONICAL_MESSAGE_REQUIRED");
        var observations = await db
            .DeliveryObservations.AsNoTracking()
            .Where(value =>
                value.Environment == request.Environment
                && value.TenantId == request.TenantId
                && value.RelationshipId == request.RelationshipId
                && value.MessageId == messageId
                && value.Provider == "WHATSAPP"
            )
            .OrderByDescending(value => value.ObservedAt)
            .ToListAsync(cancellationToken);
        var delivered = observations.FirstOrDefault(value =>
            value.DeliveryState == "DELIVERED" || value.DeliveryState == "READ"
        );
        var terminal =
            delivered ?? observations.FirstOrDefault(value => value.DeliveryState == "FAILED");
        var latest = terminal ?? observations.FirstOrDefault();
        return new(
            delivered is not null ? "DELIVERED"
                : terminal is not null ? "REJECTED"
                : "UNKNOWN",
            latest?.ProviderReferenceDigest ?? Hash($"unresolved:{request.OutboxId:D}"),
            Hash($"reconciliation:{request.OutboxId:D}:{clock.GetUtcNow():O}"),
            clock.GetUtcNow()
        );
    }

    private static WhatsAppDispatchObservation Observation(
        WhatsAppProviderDispatchRequest request,
        string state,
        string providerMessageId,
        DateTimeOffset now
    ) =>
        new(
            state,
            Hash(
                string.IsNullOrEmpty(providerMessageId)
                    ? $"unknown:{request.OutboxId:D}"
                    : providerMessageId
            ),
            Hash($"{request.OutboxId:D}:{request.AttemptNumber}:{state}:{now:O}"),
            now
        );

    private static string Hash(string value) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));

    private void RequireDispatchEnabled()
    {
        if (
            !channelOptions.CurrentValue.DispatchEnabled
            || !conversationOptions.Value.Enabled
            || !conversationOptions.Value.DispatchEnabled
        )
            throw new WhatsAppCapabilityUnavailableException("DISPATCH_DISABLED");
    }
}
