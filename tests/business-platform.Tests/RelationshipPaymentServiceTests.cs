// Implements: architecture/reference/api-specs/business-platform.openapi.yaml §RelationshipCheckoutOutcome
// Constitutional basis: C-023, C-038, C-043, C-059, C-088

using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class RelationshipPaymentServiceTests
{
    [Fact]
    public async Task ExactCheckoutReplayReturnsStoredOutcomeWithoutRepeatingOwnerMutation()
    {
        var context = await CreateContextAsync(includeAcceptance: true);
        var idempotencyKey = Guid.NewGuid();

        var first = await context.Service.CreateCheckoutAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            context.Contract.Version, idempotencyKey,
            new CheckoutProceedRequest("CONFIRM_CHECKOUT_AND_RENEWAL_TERMS"),
            FreshPortalAssurance(), context.CorrelationId, CancellationToken.None);
        var replay = await context.Service.CreateCheckoutAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            context.Contract.Version, idempotencyKey,
            new CheckoutProceedRequest("CONFIRM_CHECKOUT_AND_RENEWAL_TERMS"),
            FreshPortalAssurance(), Guid.NewGuid(), CancellationToken.None);

        Assert.Equal("FULLY_DISCOUNTED", first.OutcomeKind);
        Assert.Equal(first.CheckoutIntentId, replay.CheckoutIntentId);
        Assert.Equal(0, first.PayableInrPaise);
        Assert.Equal(1, context.Gateway.CallCount);
        Assert.Equal(1, context.Wbe.CheckoutCallCount);
    }

    [Fact]
    public async Task DivergentIdempotencyReuseReturnsCommercialConflictWithoutCallingOwners()
    {
        var context = await CreateContextAsync(includeAcceptance: true);
        var idempotencyKey = Guid.NewGuid();
        await using (var db = context.Factory.CreateDbContext())
        {
            db.RelationshipCheckoutIntents.Add(new RelationshipCheckoutIntent
            {
                TenantId = context.TenantId,
                RelationshipId = context.RelationshipId,
                ContractId = context.Contract.ContractId,
                ContractVersion = context.Contract.Version,
                ContractHash = context.Contract.ContractHash,
                IdempotencyKey = idempotencyKey,
                MaterialRequestHash = new string('f', 64),
            });
            await db.SaveChangesAsync();
        }

        var result = await context.Service.CreateCheckoutAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            context.Contract.Version, idempotencyKey,
            new CheckoutProceedRequest("CONFIRM_CHECKOUT_AND_RENEWAL_TERMS"),
            FreshPortalAssurance(), context.CorrelationId, CancellationToken.None);

        Assert.Equal("COMMERCIAL_CONFLICT", result.OutcomeKind);
        Assert.Equal("IDEMPOTENCY_CONFLICT", result.ReasonCode);
        Assert.Equal(0, context.Gateway.CallCount);
        Assert.Equal(0, context.Wbe.CheckoutCallCount);
    }

    [Fact]
    public async Task CheckoutReadsReturnStoredOutcomeOnlyToActiveSameTenantParticipant()
    {
        var context = await CreateContextAsync(includeAcceptance: true);
        var created = await context.Service.CreateCheckoutAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            context.Contract.Version, Guid.NewGuid(),
            new CheckoutProceedRequest("CONFIRM_CHECKOUT_AND_RENEWAL_TERMS"),
            FreshPortalAssurance(), context.CorrelationId, CancellationToken.None);

        var current = await context.Service.GetCurrentCheckoutAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            context.Contract.Version, CancellationToken.None);
        var exact = await context.Service.GetCheckoutIntentAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            created.CheckoutIntentId, CancellationToken.None);

        Assert.Equal(created, current);
        Assert.Equal(created, exact);
        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() =>
            context.Service.GetCheckoutIntentAsync(
                Guid.NewGuid(), context.RelationshipId, context.ParticipantId,
                created.CheckoutIntentId, CancellationToken.None));
    }

    [Fact]
    public async Task HostedCheckoutReconcilesExactOwnerCaptureBeforeActivationEligibility()
    {
        var context = await CreateContextAsync(includeAcceptance: true);
        context.Wbe.ReturnHostedCheckout = true;
        var created = await context.Service.CreateCheckoutAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            context.Contract.Version, Guid.NewGuid(),
            new CheckoutProceedRequest("CONFIRM_CHECKOUT_AND_RENEWAL_TERMS"),
            FreshPortalAssurance(), context.CorrelationId, CancellationToken.None);
        context.Wbe.ReconciledOutcome = new RelationshipCheckoutOutcome(
            "CAPTURED", created.CheckoutIntentId, context.RelationshipId, context.Contract.Version,
            DateTimeOffset.UtcNow, CommercialOutcomeReference: "pay_exact",
            CommercialEvidenceId: Guid.NewGuid(), EvidenceState: "COMMITTED");

        var captured = await context.Service.GetCheckoutIntentAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            created.CheckoutIntentId, CancellationToken.None);

        Assert.Equal("RAZORPAY_CHECKOUT_REQUIRED", created.OutcomeKind);
        Assert.Equal("CAPTURED", captured.OutcomeKind);
        Assert.Equal("pay_exact", captured.CommercialOutcomeReference);
        Assert.Equal(1, context.Wbe.ReconcileCallCount);
        await using var db = context.Factory.CreateDbContext();
        var stored = await db.RelationshipCheckoutIntents.SingleAsync();
        Assert.Equal("COMPLETED", stored.Status);
        Assert.NotNull(stored.PaymentConsentEvidenceId);
        Assert.Equal(context.AcceptanceId, stored.ContractAcceptanceId);
    }

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

    [Theory]
    [InlineData(true, 31, 149900, 100000, "STARTER", typeof(PaymentStepUpRequiredException))]
    [InlineData(true, 0, 0, 100000, "STARTER", typeof(ArgumentOutOfRangeException))]
    [InlineData(true, 0, 149900, -1, "STARTER", typeof(ArgumentOutOfRangeException))]
    [InlineData(true, 0, 149900, 100000, " ", typeof(ArgumentException))]
    public async Task InvalidOnboardingInputsFailBeforeEvidence(
        bool isPortal, int authenticatedSecondsInFuture, long subscriptionAmount, long walletSeed,
        string bundleTier, Type expectedException)
    {
        var context = await CreateContextAsync(includeAcceptance: true);

        await Assert.ThrowsAsync(expectedException, () => context.Service.CreateOnboardingOrderAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId, context.Contract.Version,
            new PaymentProceedRequest(bundleTier, subscriptionAmount, walletSeed, "PROCEED_TO_RAZORPAY"),
            new ContractPortalAssurance(isPortal, DateTimeOffset.UtcNow.AddSeconds(authenticatedSecondsInFuture)),
            context.CorrelationId, CancellationToken.None));

        Assert.Equal(0, context.Gateway.CallCount);
        Assert.Null(context.Wbe.LastRequest);
    }

    [Theory]
    [InlineData("USD", "MONTHLY")]
    [InlineData("INR", "ANNUAL")]
    public async Task ContractCurrencyAndCadenceMustMatchHostedPayment(string currency, string cadence)
    {
        var context = await CreateContextAsync(
            includeAcceptance: true, currency: currency, cadence: cadence);

        await Assert.ThrowsAsync<PaymentItemizationMismatchException>(() =>
            context.Service.CreateOnboardingOrderAsync(
                context.TenantId, context.RelationshipId, context.ParticipantId, context.Contract.Version,
                new PaymentProceedRequest("STARTER", 149900, 100000, "PROCEED_TO_RAZORPAY"),
                FreshPortalAssurance(), context.CorrelationId, CancellationToken.None));

        Assert.Equal(0, context.Gateway.CallCount);
        Assert.Null(context.Wbe.LastRequest);
    }

    [Theory]
    [InlineData("USD", 249900)]
    [InlineData("INR", 1)]
    public async Task InconsistentHostedOrderIsRejected(string currency, long amount)
    {
        var context = await CreateContextAsync(includeAcceptance: true);
        context.Wbe.OrderCurrency = currency;
        context.Wbe.OrderAmount = amount;

        await Assert.ThrowsAsync<PaymentOwnerUnavailableException>(() =>
            context.Service.CreateOnboardingOrderAsync(
                context.TenantId, context.RelationshipId, context.ParticipantId, context.Contract.Version,
                new PaymentProceedRequest("STARTER", 149900, 100000, "PROCEED_TO_RAZORPAY"),
                FreshPortalAssurance(), context.CorrelationId, CancellationToken.None));
    }

    [Theory]
    [InlineData("intent")]
    [InlineData("relationship")]
    [InlineData("version")]
    public async Task CheckoutRejectsEachOwnerIdentityMismatch(string mismatch)
    {
        var context = await CreateContextAsync(includeAcceptance: true);
        context.Wbe.CheckoutIdentityMismatch = mismatch;

        await Assert.ThrowsAsync<PaymentOwnerUnavailableException>(() => context.Service.CreateCheckoutAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            context.Contract.Version, Guid.NewGuid(),
            new CheckoutProceedRequest("CONFIRM_CHECKOUT_AND_RENEWAL_TERMS"),
            FreshPortalAssurance(), context.CorrelationId, CancellationToken.None));
    }

    [Theory]
    [InlineData("intent")]
    [InlineData("relationship")]
    [InlineData("version")]
    public async Task ReconciliationRejectsEachOwnerIdentityMismatch(string mismatch)
    {
        var context = await CreateContextAsync(includeAcceptance: true);
        context.Wbe.ReturnHostedCheckout = true;
        var created = await context.Service.CreateCheckoutAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            context.Contract.Version, Guid.NewGuid(),
            new CheckoutProceedRequest("CONFIRM_CHECKOUT_AND_RENEWAL_TERMS"),
            FreshPortalAssurance(), context.CorrelationId, CancellationToken.None);
        context.Wbe.ReconciledOutcome = new RelationshipCheckoutOutcome(
            "CAPTURED",
            mismatch == "intent" ? Guid.NewGuid() : created.CheckoutIntentId,
            mismatch == "relationship" ? Guid.NewGuid() : context.RelationshipId,
            mismatch == "version" ? context.Contract.Version + 1 : context.Contract.Version,
            DateTimeOffset.UtcNow);

        await Assert.ThrowsAsync<PaymentOwnerUnavailableException>(() =>
            context.Service.GetCheckoutIntentAsync(
                context.TenantId, context.RelationshipId, context.ParticipantId,
                created.CheckoutIntentId, CancellationToken.None));
    }

    [Theory]
    [InlineData("OUTCOME_UNRESOLVED", "UNRESOLVED")]
    [InlineData("INVALID", null)]
    public async Task ReconciliationOnlyAcceptsDefinedTransitions(string outcomeKind, string? storedStatus)
    {
        var context = await CreateContextAsync(includeAcceptance: true);
        context.Wbe.ReturnHostedCheckout = true;
        var created = await context.Service.CreateCheckoutAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            context.Contract.Version, Guid.NewGuid(),
            new CheckoutProceedRequest("CONFIRM_CHECKOUT_AND_RENEWAL_TERMS"),
            FreshPortalAssurance(), context.CorrelationId, CancellationToken.None);
        context.Wbe.ReconciledOutcome = new RelationshipCheckoutOutcome(
            outcomeKind, created.CheckoutIntentId, context.RelationshipId,
            context.Contract.Version, DateTimeOffset.UtcNow);

        if (storedStatus is null)
        {
            await Assert.ThrowsAsync<PaymentOwnerUnavailableException>(() =>
                context.Service.GetCheckoutIntentAsync(
                    context.TenantId, context.RelationshipId, context.ParticipantId,
                    created.CheckoutIntentId, CancellationToken.None));
            return;
        }

        var result = await context.Service.GetCheckoutIntentAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            created.CheckoutIntentId, CancellationToken.None);
        Assert.Equal(outcomeKind, result.OutcomeKind);
        await using var db = context.Factory.CreateDbContext();
        Assert.Equal(storedStatus, (await db.RelationshipCheckoutIntents.SingleAsync()).Status);
    }

    [Fact]
    public async Task CheckoutOwnerFailurePersistsUnresolvedOutcome()
    {
        var context = await CreateContextAsync(includeAcceptance: true);
        context.Wbe.FailCheckout = true;

        await Assert.ThrowsAsync<PaymentOwnerUnavailableException>(() => context.Service.CreateCheckoutAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            context.Contract.Version, Guid.NewGuid(),
            new CheckoutProceedRequest("CONFIRM_CHECKOUT_AND_RENEWAL_TERMS"),
            FreshPortalAssurance(), context.CorrelationId, CancellationToken.None));

        await using var db = context.Factory.CreateDbContext();
        var intent = await db.RelationshipCheckoutIntents.SingleAsync();
        Assert.Equal("UNRESOLVED", intent.Status);
        Assert.Equal("OUTCOME_UNRESOLVED", intent.OutcomeKind);
    }

    [Theory]
    [InlineData(false, 0)]
    [InlineData(true, -301)]
    [InlineData(true, 31)]
    public async Task CheckoutRejectsEachInvalidAssuranceBeforePersistence(
        bool isPortal, int authenticatedSecondsInFuture)
    {
        var context = await CreateContextAsync(includeAcceptance: true);

        await Assert.ThrowsAsync<PaymentStepUpRequiredException>(() => context.Service.CreateCheckoutAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            context.Contract.Version, Guid.NewGuid(),
            new CheckoutProceedRequest("CONFIRM_CHECKOUT_AND_RENEWAL_TERMS"),
            new ContractPortalAssurance(isPortal, DateTimeOffset.UtcNow.AddSeconds(authenticatedSecondsInFuture)),
            context.CorrelationId, CancellationToken.None));

        Assert.Equal(0, context.Gateway.CallCount);
        Assert.Equal(0, context.Wbe.CheckoutCallCount);
    }

    [Fact]
    public async Task CheckoutRejectsMissingConsentBeforePersistence()
    {
        var context = await CreateContextAsync(includeAcceptance: true);

        await Assert.ThrowsAsync<PaymentConsentRequiredException>(() => context.Service.CreateCheckoutAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            context.Contract.Version, Guid.NewGuid(), new CheckoutProceedRequest(""),
            FreshPortalAssurance(), context.CorrelationId, CancellationToken.None));

        Assert.Equal(0, context.Gateway.CallCount);
        Assert.Equal(0, context.Wbe.CheckoutCallCount);
    }

    [Fact]
    public async Task CheckoutRejectsMissingRelationshipEmployerAndAcceptance()
    {
        var context = await CreateContextAsync(includeAcceptance: false);
        var request = new CheckoutProceedRequest("CONFIRM_CHECKOUT_AND_RENEWAL_TERMS");

        await Assert.ThrowsAsync<KeyNotFoundException>(() => context.Service.CreateCheckoutAsync(
            context.TenantId, Guid.NewGuid(), context.ParticipantId,
            context.Contract.Version, Guid.NewGuid(), request,
            FreshPortalAssurance(), context.CorrelationId, CancellationToken.None));
        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() => context.Service.CreateCheckoutAsync(
            context.TenantId, context.RelationshipId, Guid.NewGuid(),
            context.Contract.Version, Guid.NewGuid(), request,
            FreshPortalAssurance(), context.CorrelationId, CancellationToken.None));
        await Assert.ThrowsAsync<PaymentOrderingException>(() => context.Service.CreateCheckoutAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            context.Contract.Version, Guid.NewGuid(), request,
            FreshPortalAssurance(), context.CorrelationId, CancellationToken.None));

        Assert.Equal(0, context.Gateway.CallCount);
        Assert.Equal(0, context.Wbe.CheckoutCallCount);
    }

    [Fact]
    public async Task CurrentCheckoutReturnsNullWhenNoIntentExists()
    {
        var context = await CreateContextAsync(includeAcceptance: true);

        var current = await context.Service.GetCurrentCheckoutAsync(
            context.TenantId, context.RelationshipId, context.ParticipantId,
            context.Contract.Version, CancellationToken.None);

        Assert.Null(current);
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

    private static async Task<PaymentTestContext> CreateContextAsync(
        bool includeAcceptance, bool isBypass = false, string currency = "INR", string cadence = "MONTHLY")
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
            PriceTaxSummaryJson =
                $"{{\"currency\":\"{currency}\",\"grossAmountInrPaise\":249900,\"gstAmountInrPaise\":38120,\"cadence\":\"{cadence}\",\"subscriptionTerms\":\"Monthly\",\"adSpendTreatment\":\"Separate approved wallet seed\",\"cancellationAndRefundTerms\":\"Cancel before renewal\"}}",
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
        public int CheckoutCallCount { get; private set; }
        public int ReconcileCallCount { get; private set; }
        public bool ReturnHostedCheckout { get; set; }
        public bool FailCheckout { get; set; }
        public string? CheckoutIdentityMismatch { get; set; }
        public string OrderCurrency { get; set; } = "INR";
        public long OrderAmount { get; set; } = 249900;
        public RelationshipCheckoutOutcome? ReconciledOutcome { get; set; }

        public Task<RelationshipCheckoutOutcome> CreateCheckoutAsync(
            ContractLinkedCheckoutRequest request,
            CancellationToken cancellationToken)
        {
            CheckoutCallCount++;
            if (FailCheckout)
                throw new InvalidOperationException("WBE unavailable.");
            var checkoutIntentId = CheckoutIdentityMismatch == "intent" ? Guid.NewGuid() : request.CheckoutIntentId;
            var relationshipId = CheckoutIdentityMismatch == "relationship" ? Guid.NewGuid() : request.RelationshipId;
            var contractVersion = CheckoutIdentityMismatch == "version"
                ? request.ContractVersion + 1
                : request.ContractVersion;
            if (ReturnHostedCheckout)
            {
                return Task.FromResult(new RelationshipCheckoutOutcome(
                    "RAZORPAY_CHECKOUT_REQUIRED", checkoutIntentId, relationshipId,
                    contractVersion, DateTimeOffset.UtcNow,
                    PublicCheckoutKey: "rzp_test_public", AmountInrPaise: request.GrossAmountInrPaise,
                    CheckoutSessionId: "checkout-session", ProviderOrderReference: "order_exact",
                    MerchantDisplayName: "WAOOAW", EnabledMethodFamilies: ["UPI", "CREDIT_CARD"],
                    ExpiresAt: DateTimeOffset.UtcNow.AddMinutes(10),
                    ReconciliationTarget: $"/checkout-intents/{request.CheckoutIntentId:D}"));
            }
            return Task.FromResult(new RelationshipCheckoutOutcome(
                "FULLY_DISCOUNTED", checkoutIntentId, relationshipId,
                contractVersion, DateTimeOffset.UtcNow,
                QuoteVersion: request.QuoteVersion,
                PromotionVersion: "demo-100-v1",
                ListPriceInrPaise: request.GrossAmountInrPaise,
                DiscountInrPaise: request.GrossAmountInrPaise,
                TaxInrPaise: request.GstAmountInrPaise,
                PayableInrPaise: 0,
                RenewalConsequence: "Renews at the accepted monthly price.",
                CommercialOutcomeReference: $"zero-price:{request.CheckoutIntentId}",
                CommercialEvidenceId: Guid.NewGuid(),
                EvidenceState: "COMMITTED"));
        }

        public Task<RelationshipCheckoutOutcome> ReconcileCheckoutAsync(
            ContractLinkedCheckoutReconciliation request,
            CancellationToken cancellationToken)
        {
            ReconcileCallCount++;
            return Task.FromResult(ReconciledOutcome
                ?? throw new PaymentOwnerUnavailableException("No reconciliation outcome configured."));
        }

        public Task<HostedOnboardingOrder> CreateOrderAsync(
            ContractLinkedOnboardingOrderRequest request,
            CancellationToken cancellationToken)
        {
            LastRequest = request;
            return Task.FromResult(new HostedOnboardingOrder(
                "order_test_123", OrderAmount, OrderCurrency, isBypass));
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