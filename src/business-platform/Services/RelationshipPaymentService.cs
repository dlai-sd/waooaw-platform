// Implements: work-contracts/WC-059-goal005-ae01-contract-payment-activation.md §WC059-04
// constitutional_basis: C-023, C-038, C-043, C-059, C-088

using System.Net.Http.Json;
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

public interface IRelationshipPaymentGateway
{
    Task<HostedOnboardingOrder> CreateOrderAsync(ContractLinkedOnboardingOrderRequest request, CancellationToken cancellationToken);
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
}

public sealed class HttpRelationshipPaymentGateway(IHttpClientFactory httpClientFactory) : IRelationshipPaymentGateway
{
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