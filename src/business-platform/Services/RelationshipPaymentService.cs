// Implements: architecture/reference/api-specs/business-platform.openapi.yaml §RelationshipCheckoutOutcome
// Constitutional basis: C-023, C-038, C-043, C-059, C-088

using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record PaymentProceedRequest(string BundleTier, long SubscriptionAmountInrPaise, long WalletSeedInrPaise, string ProceedConfirmation);
public sealed record ContractLinkedOnboardingOrderRequest(
    Guid TenantId, Guid CustomerId, Guid RelationshipId, Guid ContractId, int ContractVersion, string ContractHash,
    Guid ContractAcceptanceId, Guid PaymentConsentEvidenceId, string AgentType, string BundleTier,
    long SubscriptionAmountInrPaise, long WalletSeedInrPaise);
public sealed record HostedOnboardingOrder(
    string OrderId, long AmountInrPaise, string Currency, bool IsBypass,
    string CheckoutMode = "RAZORPAY_HOSTED");
public sealed record CheckoutProceedRequest(string ProceedConfirmation);
public sealed record ContractLinkedCheckoutRequest(
    Guid CheckoutIntentId, Guid TenantId, Guid CustomerId, Guid RelationshipId, Guid ContractId,
    int ContractVersion, string ContractHash, Guid ContractAcceptanceId, Guid PaymentConsentEvidenceId,
    string AgentType, string BundleTier, long GrossAmountInrPaise, long GstAmountInrPaise,
    string QuoteVersion, Guid IdempotencyKey);
public sealed record RelationshipCheckoutOutcome(
    string OutcomeKind, Guid CheckoutIntentId, Guid RelationshipId, int ContractVersion,
    DateTimeOffset ProducedAt, string? OrderId = null, string? PublicCheckoutKey = null,
    long? AmountInrPaise = null, string Currency = "INR", string? QuoteVersion = null,
    string? CheckoutSessionId = null, string? ProviderOrderReference = null,
    string? MerchantDisplayName = null, IReadOnlyList<string>? EnabledMethodFamilies = null,
    DateTimeOffset? ExpiresAt = null, string? ReconciliationTarget = null,
    string? PromotionVersion = null, long? ListPriceInrPaise = null,
    long? DiscountInrPaise = null, long? TaxInrPaise = null, long? PayableInrPaise = null,
    string? RenewalConsequence = null, string? CommercialOutcomeReference = null,
    Guid? CommercialEvidenceId = null, string? EvidenceState = null,
    string? ReasonCode = null, string? AccountableOwner = null,
    bool? Retryable = null, string? CustomerSafeNextAction = null);

public interface IRelationshipPaymentGateway
{
    Task<HostedOnboardingOrder> CreateOrderAsync(ContractLinkedOnboardingOrderRequest request, CancellationToken cancellationToken);
    Task<RelationshipCheckoutOutcome> CreateCheckoutAsync(
        ContractLinkedCheckoutRequest request,
        CancellationToken cancellationToken);
}

public sealed class PaymentOrderingException()
    : Exception("An exact accepted contract is required before payment.");
public sealed class PaymentConsentRequiredException()
    : Exception("Explicit Proceed to Razorpay confirmation is required.");
public sealed class PaymentItemizationMismatchException()
    : Exception("Payment itemization does not match the accepted contract total.");
public sealed class PaymentStepUpRequiredException()
    : Exception("Fresh Keycloak portal authentication is required before payment.");
public sealed class PaymentOwnerUnavailableException(string reason) : Exception(reason);

public sealed class RelationshipPaymentService(
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
    IRelationshipConstitutionalGateway constitutionalGateway,
    IRelationshipPaymentGateway paymentGateway)
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    public async Task<RelationshipCheckoutOutcome?> GetCurrentCheckoutAsync(
        Guid tenantId, Guid relationshipId, Guid participantId, int contractVersion,
        CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        await RequireActiveParticipantAsync(db, tenantId, relationshipId, participantId, cancellationToken);
        var intent = await db.RelationshipCheckoutIntents.AsNoTracking()
            .Where(item => item.TenantId == tenantId && item.RelationshipId == relationshipId
                && item.ContractVersion == contractVersion)
            .OrderByDescending(item => item.CreatedAt)
            .FirstOrDefaultAsync(cancellationToken);
        return intent is null ? null : ToStoredOutcome(intent);
    }

    public async Task<RelationshipCheckoutOutcome> GetCheckoutIntentAsync(
        Guid tenantId, Guid relationshipId, Guid participantId, Guid checkoutIntentId,
        CancellationToken cancellationToken)
    {
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        await RequireActiveParticipantAsync(db, tenantId, relationshipId, participantId, cancellationToken);
        var intent = await db.RelationshipCheckoutIntents.AsNoTracking().SingleOrDefaultAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId
                && item.CheckoutIntentId == checkoutIntentId,
            cancellationToken) ?? throw new KeyNotFoundException("Checkout intent not found.");
        return ToStoredOutcome(intent);
    }

    public async Task<RelationshipCheckoutOutcome> CreateCheckoutAsync(
        Guid tenantId, Guid relationshipId, Guid participantId, int contractVersion,
        Guid idempotencyKey, CheckoutProceedRequest request, ContractPortalAssurance assurance,
        Guid correlationId, CancellationToken cancellationToken)
    {
        ValidateAssurance(assurance);
        if (!string.Equals(
                request.ProceedConfirmation,
                "CONFIRM_CHECKOUT_AND_RENEWAL_TERMS",
                StringComparison.Ordinal))
            throw new PaymentConsentRequiredException();

        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await db.EmploymentRelationships.AsNoTracking().SingleOrDefaultAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId,
            cancellationToken) ?? throw new KeyNotFoundException("Relationship not found.");
        if (relationship.State != EmploymentRelationshipState.ContractAcceptedPendingPayment
            || !relationship.AcceptedContractId.HasValue)
            throw new PaymentOrderingException();
        var employer = await db.RelationshipParticipants.AsNoTracking().AnyAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId
                && item.ParticipantId == participantId && item.Role == RelationshipParticipantRole.Employer
                && item.Status == "ACTIVE", cancellationToken);
        if (!employer)
            throw new ConstitutionalActionDeniedException(
                "Checkout requires an active same-tenant EMPLOYER binding.");
        var acceptance = await db.ContractAcceptances.AsNoTracking().SingleOrDefaultAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId
                && item.ContractId == relationship.AcceptedContractId
                && item.ContractVersion == contractVersion,
            cancellationToken) ?? throw new PaymentOrderingException();
        var contract = await db.EmploymentContractVersions.AsNoTracking().SingleAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId
                && item.ContractId == acceptance.ContractId && item.Version == acceptance.ContractVersion
                && item.ContractHash == acceptance.ContractHash, cancellationToken);
        var terms = JsonSerializer.Deserialize<EmploymentContractCommercialTerms>(
            contract.PriceTaxSummaryJson, JsonOptions)
            ?? throw new PaymentOwnerUnavailableException("Accepted commercial terms are invalid.");
        var materialHash = Hash(string.Join('|',
            tenantId, relationshipId, contract.ContractId, contract.Version, contract.ContractHash,
            acceptance.AcceptanceId, terms.OfferingId, terms.BundleTier, terms.QuoteVersion,
            request.ProceedConfirmation));

        var existing = await db.RelationshipCheckoutIntents.SingleOrDefaultAsync(
            item => item.TenantId == tenantId && item.IdempotencyKey == idempotencyKey,
            cancellationToken);
        if (existing is not null)
        {
            if (!string.Equals(existing.MaterialRequestHash, materialHash, StringComparison.Ordinal))
                return ConflictOutcome(existing.CheckoutIntentId, relationshipId, contractVersion);
            if (existing.OutcomeJson is not null)
                return JsonSerializer.Deserialize<RelationshipCheckoutOutcome>(existing.OutcomeJson, JsonOptions)
                    ?? throw new PaymentOwnerUnavailableException("Stored checkout outcome is invalid.");
            return UnresolvedOutcome(existing.CheckoutIntentId, relationshipId, contractVersion);
        }

        var intent = new RelationshipCheckoutIntent
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ContractId = contract.ContractId,
            ContractVersion = contract.Version,
            ContractHash = contract.ContractHash,
            IdempotencyKey = idempotencyKey,
            MaterialRequestHash = materialHash,
        };
        db.RelationshipCheckoutIntents.Add(intent);
        await db.SaveChangesAsync(cancellationToken);

        var evidenceId = await constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId, relationshipId, relationship.ProfessionalType, "CONFIRM_CHECKOUT", correlationId,
            new
            {
                checkout_intent_id = intent.CheckoutIntentId,
                contract_id = contract.ContractId,
                contract_version = contract.Version,
                contract_hash = contract.ContractHash,
                contract_acceptance_id = acceptance.AcceptanceId,
                terms.OfferingId,
                terms.BundleTier,
                terms.QuoteVersion,
                terms.GrossAmountInrPaise,
                terms.GstAmountInrPaise,
                terms.RenewalConsequence,
            }, cancellationToken);
        RelationshipCheckoutOutcome outcome;
        try
        {
            outcome = await paymentGateway.CreateCheckoutAsync(new ContractLinkedCheckoutRequest(
                intent.CheckoutIntentId, tenantId, relationship.InitiatingParticipantId,
                relationshipId, contract.ContractId, contract.Version, contract.ContractHash,
                acceptance.AcceptanceId, evidenceId, relationship.ProfessionalType,
                terms.BundleTier, terms.GrossAmountInrPaise, terms.GstAmountInrPaise,
                terms.QuoteVersion, idempotencyKey), cancellationToken);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            intent.Status = "UNRESOLVED";
            intent.OutcomeKind = "OUTCOME_UNRESOLVED";
            intent.OutcomeJson = JsonSerializer.Serialize(
                UnresolvedOutcome(intent.CheckoutIntentId, relationshipId, contractVersion), JsonOptions);
            intent.CompletedAt = intent.UpdatedAt = DateTimeOffset.UtcNow;
            await db.SaveChangesAsync(cancellationToken);
            throw new PaymentOwnerUnavailableException(exception.Message);
        }
        if (outcome.CheckoutIntentId != intent.CheckoutIntentId
            || outcome.RelationshipId != relationshipId
            || outcome.ContractVersion != contractVersion)
            throw new PaymentOwnerUnavailableException("WBE returned checkout identity inconsistent with BP.");
        intent.Status = outcome.OutcomeKind == "OUTCOME_UNRESOLVED" ? "UNRESOLVED" : "COMPLETED";
        intent.OutcomeKind = outcome.OutcomeKind;
        intent.OutcomeJson = JsonSerializer.Serialize(outcome, JsonOptions);
        intent.CompletedAt = intent.UpdatedAt = DateTimeOffset.UtcNow;
        await db.SaveChangesAsync(cancellationToken);
        return outcome;
    }

    public async Task<HostedOnboardingOrder> CreateOnboardingOrderAsync(
        Guid tenantId, Guid relationshipId, Guid participantId, int contractVersion,
        PaymentProceedRequest request, ContractPortalAssurance assurance, Guid correlationId,
        CancellationToken cancellationToken)
    {
        var authenticationAge = DateTimeOffset.UtcNow - assurance.AuthenticatedAt;
        if (!assurance.IsKeycloakPortal || authenticationAge > TimeSpan.FromMinutes(5)
            || authenticationAge < TimeSpan.FromSeconds(-30))
            throw new PaymentStepUpRequiredException();
        if (!string.Equals(request.ProceedConfirmation, "PROCEED_TO_RAZORPAY", StringComparison.Ordinal))
            throw new PaymentConsentRequiredException();
        if (request.SubscriptionAmountInrPaise <= 0 || request.WalletSeedInrPaise < 0)
            throw new ArgumentOutOfRangeException(nameof(request), "Payment amounts are invalid.");
        if (string.IsNullOrWhiteSpace(request.BundleTier))
            throw new ArgumentException("Bundle tier is required.", nameof(request));

        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await db.EmploymentRelationships.AsNoTracking().SingleOrDefaultAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId,
            cancellationToken) ?? throw new KeyNotFoundException("Relationship not found.");
        if (relationship.State != EmploymentRelationshipState.ContractAcceptedPendingPayment
            || !relationship.AcceptedContractId.HasValue)
            throw new PaymentOrderingException();
        var employer = await db.RelationshipParticipants.AsNoTracking().AnyAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId
                && item.ParticipantId == participantId && item.Role == RelationshipParticipantRole.Employer
                && item.Status == "ACTIVE", cancellationToken);
        if (!employer)
            throw new ConstitutionalActionDeniedException("Payment initiation requires an active same-tenant EMPLOYER binding.");
        var acceptance = await db.ContractAcceptances.AsNoTracking().SingleOrDefaultAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId
                && item.ContractId == relationship.AcceptedContractId && item.ContractVersion == contractVersion,
            cancellationToken) ?? throw new PaymentOrderingException();
        var contract = await db.EmploymentContractVersions.AsNoTracking().SingleAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId
                && item.ContractId == acceptance.ContractId && item.Version == acceptance.ContractVersion
                && item.ContractHash == acceptance.ContractHash, cancellationToken);
        using var priceDocument = JsonDocument.Parse(contract.PriceTaxSummaryJson);
        var price = priceDocument.RootElement;
        var currency = price.GetProperty("currency").GetString();
        var grossAmount = price.GetProperty("grossAmountInrPaise").GetInt64();
        var gstAmount = price.GetProperty("gstAmountInrPaise").GetInt64();
        var cadence = price.GetProperty("cadence").GetString();
        if (currency != "INR" || cadence != "MONTHLY"
            || request.SubscriptionAmountInrPaise + request.WalletSeedInrPaise != grossAmount)
            throw new PaymentItemizationMismatchException();

        var evidenceId = await constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId, relationshipId, relationship.ProfessionalType, "PROCEED_TO_RAZORPAY", correlationId,
            new
            {
                contract_id = contract.ContractId,
                contract_version = contract.Version,
                contract_hash = contract.ContractHash,
                contract_acceptance_id = acceptance.AcceptanceId,
                currency,
                gross_amount_inr_paise = grossAmount,
                gst_amount_inr_paise = gstAmount,
                subscription_amount_inr_paise = request.SubscriptionAmountInrPaise,
                wallet_seed_inr_paise = request.WalletSeedInrPaise,
                cadence,
                checkout = "RAZORPAY_HOSTED",
            }, cancellationToken);
        var order = await paymentGateway.CreateOrderAsync(new ContractLinkedOnboardingOrderRequest(
            tenantId, relationship.InitiatingParticipantId, relationshipId, contract.ContractId, contract.Version,
            contract.ContractHash, acceptance.AcceptanceId, evidenceId, relationship.ProfessionalType,
            request.BundleTier.Trim().ToUpperInvariant(), request.SubscriptionAmountInrPaise,
            request.WalletSeedInrPaise), cancellationToken);
        if (order.IsBypass || order.Currency != "INR" || order.AmountInrPaise != grossAmount)
            throw new PaymentOwnerUnavailableException("WBE returned an order inconsistent with the accepted contract.");
        return order;
    }

    private static void ValidateAssurance(ContractPortalAssurance assurance)
    {
        var authenticationAge = DateTimeOffset.UtcNow - assurance.AuthenticatedAt;
        if (!assurance.IsKeycloakPortal || authenticationAge > TimeSpan.FromMinutes(5)
            || authenticationAge < TimeSpan.FromSeconds(-30))
            throw new PaymentStepUpRequiredException();
    }

    private static async Task RequireActiveParticipantAsync(
        EmploymentRelationshipDbContext db, Guid tenantId, Guid relationshipId, Guid participantId,
        CancellationToken cancellationToken)
    {
        var authorized = await db.RelationshipParticipants.AsNoTracking().AnyAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId
                && item.ParticipantId == participantId && item.Status == "ACTIVE",
            cancellationToken);
        if (!authorized)
            throw new ConstitutionalActionDeniedException(
                "Checkout projection requires an active same-tenant participant binding.");
    }

    private static RelationshipCheckoutOutcome ToStoredOutcome(RelationshipCheckoutIntent intent) =>
        intent.OutcomeJson is null
            ? UnresolvedOutcome(intent.CheckoutIntentId, intent.RelationshipId, intent.ContractVersion)
            : JsonSerializer.Deserialize<RelationshipCheckoutOutcome>(intent.OutcomeJson, JsonOptions)
                ?? throw new PaymentOwnerUnavailableException("Stored checkout outcome is invalid.");

    private static string Hash(string value) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));

    private static RelationshipCheckoutOutcome ConflictOutcome(
        Guid intentId, Guid relationshipId, int contractVersion) =>
        new("COMMERCIAL_CONFLICT", intentId, relationshipId, contractVersion, DateTimeOffset.UtcNow,
            ReasonCode: "IDEMPOTENCY_CONFLICT",
            CustomerSafeNextAction: "Refresh the commercial offer and begin a new checkout.");

    private static RelationshipCheckoutOutcome UnresolvedOutcome(
        Guid intentId, Guid relationshipId, int contractVersion) =>
        new("OUTCOME_UNRESOLVED", intentId, relationshipId, contractVersion, DateTimeOffset.UtcNow,
            ReasonCode: "RECONCILIATION_PENDING", Retryable: true,
            CustomerSafeNextAction: "Wait while the existing checkout is reconciled.");
}

public sealed class HttpRelationshipPaymentGateway(IHttpClientFactory httpClientFactory) : IRelationshipPaymentGateway
{
    public async Task<RelationshipCheckoutOutcome> CreateCheckoutAsync(
        ContractLinkedCheckoutRequest request, CancellationToken cancellationToken)
    {
        using var response = await httpClientFactory.CreateClient("WBE").PostAsJsonAsync(
            "/payments/relationship-checkout", request, JsonOptions, cancellationToken);
        if (!response.IsSuccessStatusCode)
            throw new PaymentOwnerUnavailableException(
                $"WBE relationship checkout returned {(int)response.StatusCode}.");
        return await response.Content.ReadFromJsonAsync<RelationshipCheckoutOutcome>(JsonOptions, cancellationToken)
            ?? throw new PaymentOwnerUnavailableException("WBE returned an empty checkout outcome.");
    }

    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
    };

    public async Task<HostedOnboardingOrder> CreateOrderAsync(
        ContractLinkedOnboardingOrderRequest request, CancellationToken cancellationToken)
    {
        using var response = await httpClientFactory.CreateClient("WBE").PostAsJsonAsync(
            "/payments/onboarding-order",
            new WbeOrderRequest(
                request.TenantId, request.CustomerId, request.RelationshipId, request.ContractId, request.ContractVersion,
                request.ContractHash, request.ContractAcceptanceId, request.PaymentConsentEvidenceId,
                request.AgentType, request.BundleTier, request.SubscriptionAmountInrPaise,
                request.WalletSeedInrPaise), cancellationToken);
        if (!response.IsSuccessStatusCode)
            throw new PaymentOwnerUnavailableException($"WBE onboarding order returned {(int)response.StatusCode}.");
        var result = await response.Content.ReadFromJsonAsync<WbeOrderResult>(cancellationToken)
            ?? throw new PaymentOwnerUnavailableException("WBE returned an empty onboarding order.");
        return new HostedOnboardingOrder(result.OrderId, result.AmountPaise, result.Currency, result.IsBypass);
    }

    private sealed record WbeOrderRequest(
        [property: JsonPropertyName("tenant_id")] Guid TenantId,
        [property: JsonPropertyName("customer_id")] Guid CustomerId,
        [property: JsonPropertyName("relationship_id")] Guid RelationshipId,
        [property: JsonPropertyName("contract_id")] Guid ContractId,
        [property: JsonPropertyName("contract_version")] int ContractVersion,
        [property: JsonPropertyName("contract_hash")] string ContractHash,
        [property: JsonPropertyName("contract_acceptance_id")] Guid ContractAcceptanceId,
        [property: JsonPropertyName("payment_consent_evidence_id")] Guid PaymentConsentEvidenceId,
        [property: JsonPropertyName("agent_type")] string AgentType,
        [property: JsonPropertyName("bundle_tier")] string BundleTier,
        [property: JsonPropertyName("subscription_amount_paise")] long SubscriptionAmountPaise,
        [property: JsonPropertyName("wallet_seed_paise")] long WalletSeedPaise);
    private sealed record WbeOrderResult(
        [property: JsonPropertyName("order_id")] string OrderId,
        [property: JsonPropertyName("amount_paise")] long AmountPaise,
        [property: JsonPropertyName("currency")] string Currency,
        [property: JsonPropertyName("is_bypass")] bool IsBypass);
}