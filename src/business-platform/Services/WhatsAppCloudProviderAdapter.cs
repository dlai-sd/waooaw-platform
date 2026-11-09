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
    IOptions<Wc120ConversationOptions> conversationOptions,
    IWhatsAppWebhookCredentials? webhookCredentials = null,
    WhatsAppTenantExecutionScope? execution = null,
    WhatsAppRelationshipRouting? relationshipRouting = null
) : IWhatsAppProviderAdapter
{
    private static readonly JsonSerializerOptions CanonicalBlockJson = new(
        JsonSerializerDefaults.Web
    )
    {
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
    };

    private WhatsAppCurrentRelationshipRoute RequireCustomerRoute(
        WhatsAppProviderDispatchRequest request
    )
    {
        if (execution is null || relationshipRouting is null)
            throw new WhatsAppCapabilityUnavailableException("CUSTOMER_EGRESS_OWNER_UNAVAILABLE");
        var route = execution.RequireConfirmedRelationshipRoute();
        if (
            route.TenantId != request.TenantId
            || route.Environment != request.Environment
            || route.RelationshipId != request.RelationshipId
            || route.ConversationId != request.ConversationId
        )
            throw new WhatsAppCapabilityUnavailableException("CUSTOMER_EGRESS_ROUTE_DENIED");
        return route;
    }

    private void RequireRecipient(
        WhatsAppProviderDispatchRequest request,
        string senderHash,
        WhatsAppCurrentRelationshipRoute? route
    )
    {
        if (route is null)
            capability.RequireRecipient(request.TenantId, senderHash, clock.GetUtcNow());
        else
        {
            execution!.RequireRelationshipRoute(route);
            if (senderHash != route.SenderHash)
                throw new WhatsAppCapabilityUnavailableException("CUSTOMER_EGRESS_ROUTE_DENIED");
        }
    }

    public async Task<WhatsAppDispatchObservation> DispatchAsync(
        WhatsAppProviderDispatchRequest request,
        CancellationToken cancellationToken
    )
    {
        RequireDispatchEnabled();
        var authority = capability.RequireActive(clock.GetUtcNow());
        WhatsAppCurrentRelationshipRoute? customerRoute = null;
        if (request.Environment != authority.Environment)
            throw new WhatsAppCapabilityUnavailableException("TENANT_DENIED");
        if (request.TenantId != authority.TenantId)
        {
            customerRoute = RequireCustomerRoute(request);
            await relationshipRouting!.RequireCurrentEgressRouteAsync(
                customerRoute,
                cancellationToken
            );
        }

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
        if (
            outbox.TemplateName is not null
            || outbox.TemplateVersion is not null
            || outbox.TemplateLocale is not null
            || outbox.TemplateCategory is not null
        )
            throw new WhatsAppCapabilityUnavailableException("PROACTIVE_MESSAGING_DISABLED");
        if (outbox.CreatedAt < authority.StartsAt || outbox.CreatedAt >= authority.ExpiresAt)
            throw new WhatsAppCapabilityUnavailableException("OUTBOUND_AUTHORITY_WINDOW_DENIED");
        string contentJson;
        string? protectedDestination = null;
        if (outbox.PortalContextId is { } contextId)
        {
            var admissionLimitNotice = outbox.Purpose == "WHATSAPP_GUEST_SESSION_LIMIT_NOTICE";
            if (admissionLimitNotice && !authority.AllowPublicAdmission)
                throw new WhatsAppCapabilityUnavailableException("GUEST_ADMISSION_DENIED");
            if (
                request.RelationshipId is not null
                || request.ConversationId is not null
                || outbox.Purpose
                    is not ("WHATSAPP_GUEST_DISCOVERY" or "WHATSAPP_GUEST_SESSION_LIMIT_NOTICE")
                || !authority.AllowProvisionalOnboarding
            )
                throw new WhatsAppCapabilityUnavailableException(
                    "GUEST_DISCOVERY_AUTHORITY_DENIED"
                );
            var guide = await db
                .PortalInteractionMessages.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == request.TenantId
                        && value.ContextId == contextId
                        && value.MessageId == messageId
                        && value.Sequence == request.Sequence
                        && value.Actor == "GUIDE",
                    cancellationToken
                );
            contentJson =
                guide?.ContentJson
                ?? throw new WhatsAppCapabilityUnavailableException("CANONICAL_MESSAGE_REQUIRED");
            var guestContext = await db.PortalInteractionContexts.SingleOrDefaultAsync(
                value => value.TenantId == request.TenantId && value.ContextId == contextId,
                cancellationToken
            );
            if (admissionLimitNotice)
            {
                if (
                    guestContext is null
                    || await db.Set<WhatsAppGuestSession>()
                        .AnyAsync(
                            value =>
                                value.TenantId == request.TenantId
                                && value.BindingDigest == outbox.RecipientBindingDigest,
                            cancellationToken
                        )
                )
                    throw new WhatsAppCapabilityUnavailableException("GUEST_ADMISSION_DENIED");
                protectedDestination =
                    outbox.ProtectedRecipientDestination
                    ?? throw new WhatsAppCapabilityUnavailableException(
                        "PHONE_DESTINATION_UNAVAILABLE"
                    );
            }
            else
            {
                var guest = guestContext is null
                    ? null
                    : await db.Set<WhatsAppGuestSession>()
                        .SingleOrDefaultAsync(
                            value =>
                                value.TenantId == request.TenantId
                                && value.BindingDigest == outbox.RecipientBindingDigest
                                && value.ParticipantId == guestContext.ParticipantId,
                            cancellationToken
                        );
                protectedDestination =
                    guest?.ProtectedDestination
                    ?? throw new WhatsAppCapabilityUnavailableException(
                        "PHONE_DESTINATION_UNAVAILABLE"
                    );
            }
        }
        else
        {
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
            contentJson = message.ContentJson;
            protectedDestination = await outboxService.ResolveRelationshipDestinationAsync(
                outbox,
                clock.GetUtcNow(),
                cancellationToken
            );
        }
        string text;
        try
        {
            using var content = JsonDocument.Parse(contentJson);
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
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .Count() != block.EnumerateObject().Count()
            )
                throw new WhatsAppCapabilityUnavailableException("MESSAGE_PROJECTION_DENIED");
            var canonical = block.Deserialize<ConversationTextBlockV1>(
                outbox.PortalContextId is null
                    ? CanonicalBlockJson
                    : new JsonSerializerOptions(JsonSerializerDefaults.Web)
                    {
                        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
                    }
            );
            if (
                canonical is null
                || canonical.SchemaVersion != "1.0"
                || canonical.BlockType != "TEXT"
                || string.IsNullOrWhiteSpace(canonical.Text)
                || canonical.Text.Contains('\0')
                || canonical.Text.Length > 4096
            )
                throw new WhatsAppCapabilityUnavailableException("MESSAGE_PROJECTION_DENIED");
            text = canonical.Text;
            if (
                outbox.Purpose == "WHATSAPP_GUEST_SESSION_LIMIT_NOTICE"
                && text != WhatsAppGuestTrafficBudget.SessionLimitNotice
            )
                throw new WhatsAppCapabilityUnavailableException("MESSAGE_PROJECTION_DENIED");
            if (
                outbox.PortalContextId is not null
                && Hash(
                    JsonSerializer.Serialize(
                        new[] { canonical },
                        new JsonSerializerOptions(JsonSerializerDefaults.Web)
                    )
                ) != outbox.PayloadDigest
            )
                throw new WhatsAppCapabilityUnavailableException("MESSAGE_PROJECTION_DENIED");
        }
        catch (JsonException)
        {
            throw new WhatsAppCapabilityUnavailableException("MESSAGE_PROJECTION_DENIED");
        }

        if (customerRoute is not null && protectedDestination is null)
            throw new WhatsAppCapabilityUnavailableException("PHONE_DESTINATION_UNAVAILABLE");
        var protectedValues = await credentials.ReadAsync(cancellationToken);
        var configured = conversationOptions.Value;
        if (
            configured.Environment != request.Environment
            || configured.AppBindingDigest != Hash(protectedValues.Binding.AppId)
            || configured.WabaBindingDigest != Hash(protectedValues.Binding.WabaId)
            || configured.RecipientBindingDigest != Hash(protectedValues.Binding.PhoneNumberId)
        )
            throw new WhatsAppCapabilityUnavailableException("PROVIDER_BINDING_DENIED");
        if (
            protectedDestination is null
            && outbox.RecipientBindingDigest != protectedValues.Binding.RecipientBindingDigest
        )
            throw new WhatsAppCapabilityUnavailableException("RECIPIENT_DESTINATION_MISMATCH");
        var recipientPhoneNumber = protectedValues.Binding.RecipientPhoneNumber;
        string? phoneSubjectKey = null;
        if (protectedDestination is not null)
        {
            if (webhookCredentials is null)
                throw new WhatsAppCapabilityUnavailableException("PHONE_DESTINATION_UNAVAILABLE");
            phoneSubjectKey = await webhookCredentials.ReadPhoneSubjectKeyAsync(cancellationToken);
            recipientPhoneNumber = WhatsAppPhoneDestinationProtector.Unprotect(
                phoneSubjectKey,
                protectedDestination,
                outbox.RecipientBindingDigest
            );
        }
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
        if (
            !await outboxService.IsCurrentlyEligibleAsync(
                outbox,
                clock.GetUtcNow(),
                cancellationToken
            )
        )
            throw new WhatsAppCapabilityUnavailableException("RECIPIENT_ELIGIBILITY_REVOKED");
        RequireRecipient(request, outbox.RecipientBindingDigest, customerRoute);
        if (request.RelationshipId is { } relationshipId)
            await stopFence.ThrowIfLatchedAsync(
                request.TenantId,
                relationshipId,
                cancellationToken
            );
        if (protectedValues.ValidUntil <= clock.GetUtcNow())
            throw new WhatsAppCapabilityUnavailableException("PROVIDER_AUTHORITY_EXPIRED");
        var reservedAuthority = customerRoute is null
            ? await budget.ReserveAsync(request, outbox.RecipientBindingDigest, cancellationToken)
            : await budget.ReserveRelationshipOutboundAsync(
                request,
                customerRoute,
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
                    to = recipientPhoneNumber.TrimStart('+'),
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
                    to = recipientPhoneNumber.TrimStart('+'),
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
        RequireRecipient(request, outbox.RecipientBindingDigest, customerRoute);
        if (capability.RequireActive(clock.GetUtcNow()) != reservedAuthority)
            throw new WhatsAppCapabilityUnavailableException("ACTIVATION_CHANGED");
        if (
            outbox.PortalContextId is null
            && protectedDestination
                != await outboxService.ResolveRelationshipDestinationAsync(
                    outbox,
                    clock.GetUtcNow(),
                    cancellationToken
                )
        )
            throw new WhatsAppCapabilityUnavailableException("RECIPIENT_DESTINATION_CHANGED");
        if (
            !await outboxService.IsCurrentlyEligibleAsync(
                outbox,
                clock.GetUtcNow(),
                cancellationToken
            )
        )
            throw new WhatsAppCapabilityUnavailableException("RECIPIENT_ELIGIBILITY_REVOKED");
        if (request.RelationshipId is { } currentRelationshipId)
            await stopFence.ThrowIfLatchedAsync(
                request.TenantId,
                currentRelationshipId,
                cancellationToken
            );
        if (
            !await outboxService.IsCurrentlyEligibleAsync(
                outbox,
                clock.GetUtcNow(),
                cancellationToken
            )
        )
            throw new WhatsAppCapabilityUnavailableException("RECIPIENT_ELIGIBILITY_REVOKED");
        if (outbox.Purpose == "WHATSAPP_GUEST_DISCOVERY")
        {
            var currentDestination = await (
                from context in db.PortalInteractionContexts.AsNoTracking()
                join guest in db.Set<WhatsAppGuestSession>().AsNoTracking()
                    on new { context.TenantId, context.ParticipantId } equals new
                    {
                        guest.TenantId,
                        guest.ParticipantId,
                    }
                where
                    context.TenantId == request.TenantId
                    && context.ContextId == outbox.PortalContextId
                    && guest.BindingDigest == outbox.RecipientBindingDigest
                select guest.ProtectedDestination
            ).SingleOrDefaultAsync(cancellationToken);
            if (
                currentDestination is null
                || phoneSubjectKey is null
                || WhatsAppPhoneDestinationProtector.Unprotect(
                    phoneSubjectKey,
                    currentDestination,
                    outbox.RecipientBindingDigest
                ) != recipientPhoneNumber
            )
                throw new WhatsAppCapabilityUnavailableException("RECIPIENT_DESTINATION_CHANGED");
        }
        if (protectedValues.ValidUntil <= clock.GetUtcNow())
            throw new WhatsAppCapabilityUnavailableException("PROVIDER_AUTHORITY_EXPIRED");
        if (!await outboxService.AuthorizeRuntimeEgressAsync(outbox, clock, cancellationToken))
            throw new WhatsAppCapabilityUnavailableException("RECIPIENT_ELIGIBILITY_REVOKED");
        RequireDispatchEnabled();
        if (customerRoute is not null)
        {
            await relationshipRouting!.RequireCurrentEgressRouteAsync(
                customerRoute,
                cancellationToken
            );
            RequireRecipient(request, outbox.RecipientBindingDigest, customerRoute);
            if (
                protectedDestination
                != await outboxService.ResolveRelationshipDestinationAsync(
                    outbox,
                    clock.GetUtcNow(),
                    cancellationToken
                )
            )
                throw new WhatsAppCapabilityUnavailableException("RECIPIENT_DESTINATION_CHANGED");
            await stopFence.ThrowIfLatchedAsync(
                customerRoute.TenantId,
                customerRoute.RelationshipId,
                cancellationToken
            );
            var finalNow = clock.GetUtcNow();
            if (
                !await db
                    .ConversationOutbox.AsNoTracking()
                    .AnyAsync(
                        value =>
                            value.OutboxId == request.OutboxId
                            && value.TenantId == request.TenantId
                            && value.Environment == request.Environment
                            && value.RelationshipId == request.RelationshipId
                            && value.ConversationId == request.ConversationId
                            && value.Sequence == request.Sequence
                            && value.PayloadReference == request.PayloadReference
                            && value.PayloadDigest == request.PayloadDigest
                            && value.RecipientBindingDigest == customerRoute.SenderHash
                            && value.AttemptNumber == request.AttemptNumber
                            && value.State == "DISPATCHING"
                            && value.LeaseExpiresAt > finalNow
                            && value.LeaseOwner == outbox.LeaseOwner,
                        cancellationToken
                    )
            )
                throw new WhatsAppCapabilityUnavailableException("OUTBOUND_LEASE_EXPIRED");
        }
        if (
            capability.RequireActive(clock.GetUtcNow()) != reservedAuthority
            || protectedValues.ValidUntil <= clock.GetUtcNow()
        )
            throw new WhatsAppCapabilityUnavailableException("PROVIDER_AUTHORITY_EXPIRED");
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
        var authority = capability.RequireActive(clock.GetUtcNow());
        var customerRoute =
            request.TenantId == authority.TenantId ? null : RequireCustomerRoute(request);
        if (request.Environment != authority.Environment)
            throw new WhatsAppCapabilityUnavailableException("TENANT_DENIED");
        await using var db = await conversations.CreateDbContextAsync(cancellationToken);
        var outbox =
            await db
                .ConversationOutbox.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.OutboxId == request.OutboxId
                        && value.Environment == request.Environment
                        && value.TenantId == request.TenantId
                        && value.RelationshipId == request.RelationshipId
                        && (
                            customerRoute == null
                            || (
                                value.ConversationId == request.ConversationId
                                && value.Sequence == request.Sequence
                                && value.PayloadDigest == request.PayloadDigest
                                && value.PayloadReference == request.PayloadReference
                                && value.AttemptNumber == request.AttemptNumber
                                && value.RecipientBindingDigest == customerRoute.SenderHash
                            )
                        ),
                    cancellationToken
                )
            ?? throw new WhatsAppCapabilityUnavailableException("CANONICAL_MESSAGE_REQUIRED");
        RequireRecipient(request, outbox.RecipientBindingDigest, customerRoute);
        if (!Guid.TryParse(outbox.AggregateId, out var messageId))
            throw new WhatsAppCapabilityUnavailableException("CANONICAL_MESSAGE_REQUIRED");
        var observations = await db
            .DeliveryObservations.AsNoTracking()
            .Where(value =>
                value.Environment == request.Environment
                && value.TenantId == request.TenantId
                && value.RelationshipId == request.RelationshipId
                && value.PortalContextId == outbox.PortalContextId
                && (
                    outbox.PortalContextId == null
                        ? value.MessageId == messageId
                        : value.PortalMessageId == messageId
                )
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
