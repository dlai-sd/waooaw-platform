// Implements: work-contracts/WC-059-goal005-ae01-contract-payment-activation.md §WC059-04
// constitutional_basis: C-023, C-038, C-043, C-059, C-088

using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class RelationshipPaymentServiceTests
{
    // CCT-AE01-PAY-ORDER
    [Fact]
    public async Task AcceptedContractAndExplicitProceedCreateContractLinkedHostedOrder()
    {
        var context = await CreateContextAsync(includeAcceptance: true);

        var result = await context.Service.CreateOnboardingOrderAsync(
            context.TenantId,
            context.RelationshipId,
            context.ParticipantId,
            context.Contract.Version,
            new PaymentProceedRequest("STARTER", 149900, 100000, "PROCEED_TO_RAZORPAY"),
            FreshPortalAssurance(),
            context.CorrelationId,
            CancellationToken.None);

        Assert.Equal("order_test_123", result.OrderId);
        Assert.Equal(249900, result.AmountInrPaise);
        Assert.Equal("RAZORPAY_HOSTED", result.CheckoutMode);
        Assert.Equal(1, context.Gateway.CallCount);
        Assert.NotNull(context.Wbe.LastRequest);
        Assert.Equal(context.RelationshipId, context.Wbe.LastRequest!.RelationshipId);
        Assert.Equal(context.Contract.ContractId, context.Wbe.LastRequest.ContractId);
        Assert.Equal(context.TenantId, context.Wbe.LastRequest.TenantId);
        Assert.Equal(context.AcceptanceId, context.Wbe.LastRequest.ContractAcceptanceId);
        Assert.NotEqual(Guid.Empty, context.Wbe.LastRequest.PaymentConsentEvidenceId);
    }

    [Fact]
    public async Task MissingAcceptanceOrWrongAmountNeverCallsEvidenceOrWbe()
    {
        var missing = await CreateContextAsync(includeAcceptance: false);
        await Assert.ThrowsAsync<PaymentOrderingException>(() => missing.Service.CreateOnboardingOrderAsync(
            missing.TenantId, missing.RelationshipId, missing.ParticipantId, missing.Contract.Version,
            new PaymentProceedRequest("STARTER", 149900, 100000, "PROCEED_TO_RAZORPAY"),
            FreshPortalAssurance(),
            missing.CorrelationId, CancellationToken.None));

        var mismatch = await CreateContextAsync(includeAcceptance: true);
        await Assert.ThrowsAsync<PaymentItemizationMismatchException>(() => mismatch.Service.CreateOnboardingOrderAsync(
            mismatch.TenantId, mismatch.RelationshipId, mismatch.ParticipantId, mismatch.Contract.Version,
            new PaymentProceedRequest("STARTER", 1, 2, "PROCEED_TO_RAZORPAY"),
            FreshPortalAssurance(),
            mismatch.CorrelationId, CancellationToken.None));

        Assert.Null(missing.Wbe.LastRequest);
        Assert.Null(mismatch.Wbe.LastRequest);
        Assert.Equal(0, missing.Gateway.CallCount);
        Assert.Equal(0, mismatch.Gateway.CallCount);
    }

    [Fact]
    public async Task MissingExplicitProceedOrEvidenceFailureNeverCallsWbe()
    {
        var context = await CreateContextAsync(includeAcceptance: true);
        await Assert.ThrowsAsync<PaymentConsentRequiredException>(() => context.Service.CreateOnboardingOrderAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId, context.Contract.Version,
            new PaymentProceedRequest("STARTER", 149900, 100000, ""),
            FreshPortalAssurance(),
            context.CorrelationId, CancellationToken.None));
        context.Gateway.FailNext = true;
        await Assert.ThrowsAsync<InvalidOperationException>(() => context.Service.CreateOnboardingOrderAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId, context.Contract.Version,
            new PaymentProceedRequest("STARTER", 149900, 100000, "PROCEED_TO_RAZORPAY"),
            FreshPortalAssurance(),
            context.CorrelationId, CancellationToken.None));

        Assert.Null(context.Wbe.LastRequest);
    }

    [Fact]
    public async Task StaleOrNonPortalAssuranceNeverCallsEvidenceOrWbe()
    {
        var context = await CreateContextAsync(includeAcceptance: true);

        await Assert.ThrowsAsync<PaymentStepUpRequiredException>(() => context.Service.CreateOnboardingOrderAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId, context.Contract.Version,
            new PaymentProceedRequest("STARTER", 149900, 100000, "PROCEED_TO_RAZORPAY"),
            new ContractPortalAssurance(false, DateTimeOffset.UtcNow),
            context.CorrelationId, CancellationToken.None));
        await Assert.ThrowsAsync<PaymentStepUpRequiredException>(() => context.Service.CreateOnboardingOrderAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId, context.Contract.Version,
            new PaymentProceedRequest("STARTER", 149900, 100000, "PROCEED_TO_RAZORPAY"),
            new ContractPortalAssurance(true, DateTimeOffset.UtcNow.AddMinutes(-6)),
            context.CorrelationId, CancellationToken.None));

        Assert.Equal(0, context.Gateway.CallCount);
        Assert.Null(context.Wbe.LastRequest);
    }

    [Fact]
    public async Task BypassOrderIsRejectedAsInconsistentWithAcceptedContract()
    {
        var context = await CreateContextAsync(includeAcceptance: true, isBypass: true);

        await Assert.ThrowsAsync<PaymentOwnerUnavailableException>(() => context.Service.CreateOnboardingOrderAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId, context.Contract.Version,
            new PaymentProceedRequest("STARTER", 149900, 100000, "PROCEED_TO_RAZORPAY"),
            FreshPortalAssurance(), context.CorrelationId, CancellationToken.None));
    }

    private static ContractPortalAssurance FreshPortalAssurance() =>
        new(true, DateTimeOffset.UtcNow);

    private static async Task<PaymentTestContext> CreateContextAsync(bool includeAcceptance, bool isBypass = false)
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var wbe = new RecordingPaymentGateway(isBypass);
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var acceptanceId = Guid.NewGuid();
        var contract = new EmploymentContractVersion
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            Version = 1,
            ContractHash = new string('a', 64),
            AeecVersion = "1.0",
            DomainScheduleHash = new string('b', 64),
            ConfigurationSnapshotJson = "{}",
            PriceTaxSummaryJson = "{\"currency\":\"INR\",\"grossAmountInrPaise\":249900,\"gstAmountInrPaise\":38120,\"cadence\":\"MONTHLY\",\"subscriptionTerms\":\"Monthly\",\"adSpendTreatment\":\"Separate approved wallet seed\",\"cancellationAndRefundTerms\":\"Cancel before renewal\"}",
            CreatedByParticipantId = participantId,
        };
        await using var db = factory.CreateDbContext();
        db.EmploymentRelationships.Add(new EmploymentRelationship
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ProfessionalType = "DMA",
            EvaluationIntentId = Guid.NewGuid(),
            InitiatingParticipantId = participantId,
            State = EmploymentRelationshipState.ContractAcceptedPendingPayment,
            AcceptedContractId = contract.ContractId,
        });
        db.RelationshipParticipants.Add(new RelationshipParticipant
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ParticipantId = participantId,
            Role = RelationshipParticipantRole.Employer,
            BoundEvidenceId = Guid.NewGuid(),
        });
        db.EmploymentContractVersions.Add(contract);
        if (includeAcceptance)
        {
            db.ContractAcceptances.Add(new ContractAcceptance
            {
                AcceptanceId = acceptanceId,
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ContractId = contract.ContractId,
                ContractVersion = contract.Version,
                ContractHash = contract.ContractHash,
                ParticipantId = participantId,
                ParticipantRole = RelationshipParticipantRole.Employer,
                AuthenticationAssurance = "AAL3_FRESH",
                AuthoritySnapshotId = Guid.NewGuid(),
                ScopeConfirmationHash = new string('c', 64),
                AcceptanceEvidenceId = Guid.NewGuid(),
            });
        }
        await db.SaveChangesAsync();
        return new PaymentTestContext(
            new RelationshipPaymentService(factory, gateway, wbe), factory, gateway, wbe,
            tenantId, relationshipId, participantId, acceptanceId, contract, Guid.NewGuid());
    }

    private sealed class RecordingPaymentGateway(bool isBypass) : IRelationshipPaymentGateway
    {
        public ContractLinkedOnboardingOrderRequest? LastRequest { get; private set; }

        public Task<HostedOnboardingOrder> CreateOrderAsync(
            ContractLinkedOnboardingOrderRequest request,
            CancellationToken cancellationToken)
        {
            LastRequest = request;
            return Task.FromResult(new HostedOnboardingOrder("order_test_123", 249900, "INR", isBypass));
        }
    }

    private sealed record PaymentTestContext(
        RelationshipPaymentService Service,
        InMemoryEmploymentRelationshipFactory Factory,
        RecordingRelationshipConstitutionalGateway Gateway,
        RecordingPaymentGateway Wbe,
        Guid TenantId,
        Guid RelationshipId,
        Guid ParticipantId,
        Guid AcceptanceId,
        EmploymentContractVersion Contract,
        Guid CorrelationId);
}