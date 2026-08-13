// Implements: work-contracts/WC-059-goal005-ae01-contract-payment-activation.md §WC059-05
// constitutional_basis: C-002, C-023, C-026, C-059, C-088

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Temporalio.Testing;
using Temporalio.Worker;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Workflows;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class ActivationOrchestrationServiceTests
{
    [Fact]
    public async Task CanonicalTupleHasStableTemporalWorkflowIdentity()
    {
        var context = await CreateContextAsync();

        Assert.Equal(
            ActivationWorkflow.WorkflowIdFor(context.Request),
            ActivationWorkflow.WorkflowIdFor(context.Request with { PaymentEvidenceId = Guid.NewGuid() }));
    }

    // CCT-AE01-ACT-01
    [Fact]
    public async Task ValidCanonicalTupleActivatesBillingThenRelationshipExactlyOnce()
    {
        var context = await CreateContextAsync();
        var request = context.Request;

        var first = await context.Service.ActivateAsync(request, CancellationToken.None);
        var replay = await context.Service.ActivateAsync(request, CancellationToken.None);

        Assert.Equal("SUCCEEDED", first.Status);
        Assert.Equal(first.ActivationIntentId, replay.ActivationIntentId);
        Assert.Equal(first.SubscriptionId, replay.SubscriptionId);
        Assert.Equal(1, context.Billing.CallCount);
        Assert.Equal(request.CorrelationId, context.Billing.LastCorrelationId);
        await using var db = context.Factory.CreateDbContext();
        Assert.Single(await db.ActivationIntents.ToListAsync());
        var relationship = await db.EmploymentRelationships.SingleAsync();
        Assert.Equal(EmploymentRelationshipState.Active, relationship.State);
        Assert.Equal(first.ActivationIntentId, relationship.ActivationId);
        Assert.Single(await db.RelationshipStateHistory.Where(value =>
            value.ToState == EmploymentRelationshipState.ActivationPending).ToListAsync());
        Assert.Single(await db.RelationshipStateHistory.Where(value =>
            value.ToState == EmploymentRelationshipState.Active).ToListAsync());
    }

    // CCT-AE01-ACT-01
    [Fact]
    public async Task ConcurrentCanonicalTupleActivatesBillingAndRelationshipExactlyOnce()
    {
        var context = await CreateContextAsync();
        context.Billing.HoldCalls = true;

        var firstCall = context.Service.ActivateAsync(context.Request, CancellationToken.None);
        await context.Billing.FirstCallEntered;
        var secondCall = context.Service.ActivateAsync(context.Request, CancellationToken.None);
        context.Billing.ReleaseCalls();
        var outcomes = await Task.WhenAll(firstCall, secondCall);

        Assert.Equal(outcomes[0], outcomes[1]);
        Assert.Equal(1, context.Billing.CallCount);
        await using var db = context.Factory.CreateDbContext();
        Assert.Single(await db.ActivationIntents.ToListAsync());
        Assert.Single(await db.RelationshipStateHistory.Where(value =>
            value.ToState == EmploymentRelationshipState.Active).ToListAsync());
    }

    // CCT-AE01-ACT-CONFLICT
    [Fact]
    public async Task DivergentMaterialForCanonicalTupleRecordsConflictWithoutOwnerCall()
    {
        var context = await CreateContextAsync();
        await context.Service.ActivateAsync(context.Request, CancellationToken.None);

        await Assert.ThrowsAsync<ActivationConflictException>(() => context.Service.ActivateAsync(
            context.Request with { PaymentEvidenceId = Guid.NewGuid() }, CancellationToken.None));

        Assert.Equal(1, context.Billing.CallCount);
        await using var db = context.Factory.CreateDbContext();
        Assert.Equal("SUCCEEDED", (await db.ActivationIntents.SingleAsync()).Status);
    }

    // CCT-AE01-ACT-FAIL
    [Fact]
    public async Task BillingUncertaintyLeavesSameIntentRetryableAndRelationshipPreActive()
    {
        var context = await CreateContextAsync();
        context.Billing.FailNext = true;

        await Assert.ThrowsAsync<ActivationOwnerUnavailableException>(() =>
            context.Service.ActivateAsync(context.Request, CancellationToken.None));

        await using var db = context.Factory.CreateDbContext();
        var intent = await db.ActivationIntents.SingleAsync();
        Assert.Equal("FAILED_RETRYABLE", intent.Status);
        Assert.Equal(EmploymentRelationshipState.ActivationPending,
            (await db.EmploymentRelationships.SingleAsync()).State);
        Assert.Null(intent.OutcomeSubscriptionId);

        var retry = await context.Service.ActivateAsync(context.Request, CancellationToken.None);
        Assert.Equal(intent.ActivationIntentId, retry.ActivationIntentId);
        Assert.Equal(2, context.Billing.CallCount);
        Assert.Equal(context.Request.CorrelationId, context.Billing.LastCorrelationId);
    }

    [Fact]
    public async Task EvidenceUncertaintyAfterBillingSuccessRemainsRetryableAndPreActive()
    {
        var context = await CreateContextAsync();
        context.Constitutional.FailOnCall = 2;

        await Assert.ThrowsAsync<ActivationOwnerUnavailableException>(() =>
            context.Service.ActivateAsync(context.Request, CancellationToken.None));

        await using var db = context.Factory.CreateDbContext();
        Assert.Equal("FAILED_RETRYABLE", (await db.ActivationIntents.SingleAsync()).Status);
        Assert.Equal(EmploymentRelationshipState.ActivationPending,
            (await db.EmploymentRelationships.SingleAsync()).State);
        Assert.Equal(1, context.Billing.CallCount);
    }

    [Fact]
    public async Task ActivationCommandDerivesCanonicalMaterialFromRelationshipState()
    {
        var context = await CreateContextAsync();
        var starter = new RecordingActivationWorkflowStarter();
        var dispatch = new ActivationWorkflowDispatchService(context.Factory, context.Service, starter);
        var paymentEvidenceId = Guid.NewGuid();
        var command = new StartPaidActivationRequest(" pay_verified_123 ", paymentEvidenceId);
        var assurance = new ContractPortalAssurance(true, DateTimeOffset.UtcNow);

        await dispatch.StartAsync(
            context.Request.TenantId, context.Request.RelationshipId, context.Request.ActorParticipantId,
            command, assurance, CancellationToken.None);
        await dispatch.StartAsync(
            context.Request.TenantId, context.Request.RelationshipId, context.Request.ActorParticipantId,
            command, assurance, CancellationToken.None);

        Assert.Equal(2, starter.Requests.Count);
        var activation = starter.Requests[0];
        Assert.Equal(context.Request.AcceptedContractId, activation.AcceptedContractId);
        Assert.Equal(context.Request.ContractAcceptanceId, activation.ContractAcceptanceId);
        Assert.Equal(context.Request.AuthoritySnapshotId, activation.AuthoritySnapshotId);
        Assert.Equal(paymentEvidenceId, activation.PaymentEvidenceId);
        Assert.Equal("pay_verified_123", activation.PaymentReference);
        Assert.Equal(activation.CorrelationId, starter.Requests[1].CorrelationId);
        Assert.Equal(ActivationWorkflow.WorkflowIdFor(activation),
            ActivationWorkflow.WorkflowIdFor(starter.Requests[1]));
    }

    [Fact]
    public async Task ActivationCommandRejectsStalePortalAssuranceBeforeWorkflowStart()
    {
        var context = await CreateContextAsync();
        var starter = new RecordingActivationWorkflowStarter();
        var dispatch = new ActivationWorkflowDispatchService(context.Factory, context.Service, starter);

        await Assert.ThrowsAsync<PaymentStepUpRequiredException>(() => dispatch.StartAsync(
            context.Request.TenantId,
            context.Request.RelationshipId,
            context.Request.ActorParticipantId,
            new StartPaidActivationRequest(context.Request.PaymentReference, context.Request.PaymentEvidenceId),
            new ContractPortalAssurance(true, DateTimeOffset.UtcNow.AddMinutes(-6)),
            CancellationToken.None));

        Assert.Empty(starter.Requests);
    }

    [Fact]
    public async Task ActivationCommandRejectsNonEmployerBeforeWorkflowStart()
    {
        var context = await CreateContextAsync();
        var starter = new RecordingActivationWorkflowStarter();
        var dispatch = new ActivationWorkflowDispatchService(context.Factory, context.Service, starter);

        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() => dispatch.StartAsync(
            context.Request.TenantId,
            context.Request.RelationshipId,
            Guid.NewGuid(),
            new StartPaidActivationRequest(context.Request.PaymentReference, context.Request.PaymentEvidenceId),
            new ContractPortalAssurance(true, DateTimeOffset.UtcNow),
            CancellationToken.None));

        Assert.Empty(starter.Requests);
    }

    [Fact]
    public async Task ActivationCommandRejectsDivergentMaterialBeforeWorkflowJoin()
    {
        var context = await CreateContextAsync();
        var starter = new RecordingActivationWorkflowStarter();
        var dispatch = new ActivationWorkflowDispatchService(context.Factory, context.Service, starter);
        var assurance = new ContractPortalAssurance(true, DateTimeOffset.UtcNow);

        await dispatch.StartAsync(
            context.Request.TenantId, context.Request.RelationshipId, context.Request.ActorParticipantId,
            new StartPaidActivationRequest(context.Request.PaymentReference, context.Request.PaymentEvidenceId),
            assurance, CancellationToken.None);

        await Assert.ThrowsAsync<ActivationConflictException>(() => dispatch.StartAsync(
            context.Request.TenantId, context.Request.RelationshipId, context.Request.ActorParticipantId,
            new StartPaidActivationRequest(context.Request.PaymentReference, Guid.NewGuid()),
            assurance, CancellationToken.None));

        Assert.Single(starter.Requests);
    }

    [Fact]
    public async Task ActivationCommandReturnsStoredSuccessWithoutWorkflowStart()
    {
        var context = await CreateContextAsync();
        var starter = new RecordingActivationWorkflowStarter();
        var dispatch = new ActivationWorkflowDispatchService(context.Factory, context.Service, starter);
        var command = new StartPaidActivationRequest(context.Request.PaymentReference, context.Request.PaymentEvidenceId);
        var assurance = new ContractPortalAssurance(true, DateTimeOffset.UtcNow);

        await dispatch.StartAsync(
            context.Request.TenantId, context.Request.RelationshipId, context.Request.ActorParticipantId,
            command, assurance, CancellationToken.None);
        var completed = await context.Service.ActivateAsync(starter.Requests.Single(), CancellationToken.None);

        var replay = await dispatch.StartAsync(
            context.Request.TenantId, context.Request.RelationshipId, context.Request.ActorParticipantId,
            command, assurance, CancellationToken.None);

        Assert.Equal(completed, replay);
        Assert.Single(starter.Requests);
    }

    [Fact]
    public async Task TemporalFailedExecutionRestartsSameDurableIntentExactlyOnce()
    {
        var context = await CreateContextAsync();
        context.Billing.FailuresRemaining = 5;
        await using var environment = await WorkflowEnvironment.StartTimeSkippingAsync();
        using var worker = new TemporalWorker(
            environment.Client,
            new TemporalWorkerOptions("bp-trial-worker")
                .AddWorkflow<ActivationWorkflow>()
                .AddAllActivities(new ActivationActivities(context.Service)));
        var starter = new TemporalActivationWorkflowStarter(environment.Client);

        await worker.ExecuteAsync(async () =>
        {
            await Assert.ThrowsAnyAsync<Exception>(() =>
                starter.StartOrJoinAsync(context.Request, CancellationToken.None));
            await using (var failedDb = context.Factory.CreateDbContext())
            {
                var failedIntent = await failedDb.ActivationIntents.SingleAsync();
                Assert.Equal("FAILED_RETRYABLE", failedIntent.Status);
                Assert.Equal(EmploymentRelationshipState.ActivationPending,
                    (await failedDb.EmploymentRelationships.SingleAsync()).State);
            }

            var outcome = await starter.StartOrJoinAsync(context.Request, CancellationToken.None);

            await using var completedDb = context.Factory.CreateDbContext();
            Assert.Equal("SUCCEEDED", outcome.Status);
            Assert.Equal(outcome.ActivationIntentId,
                (await completedDb.ActivationIntents.SingleAsync()).ActivationIntentId);
            Assert.Equal(EmploymentRelationshipState.Active,
                (await completedDb.EmploymentRelationships.SingleAsync()).State);
            Assert.Equal(6, context.Billing.CallCount);
            Assert.Single(await completedDb.RelationshipStateHistory.Where(value =>
                value.ToState == EmploymentRelationshipState.Active).ToListAsync());
        });
    }

    [Fact]
    public async Task TemporalRunningReplayJoinsOneCanonicalExecution()
    {
        var context = await CreateContextAsync();
        context.Billing.HoldCalls = true;
        await using var environment = await WorkflowEnvironment.StartTimeSkippingAsync();
        using var worker = new TemporalWorker(
            environment.Client,
            new TemporalWorkerOptions("bp-trial-worker")
                .AddWorkflow<ActivationWorkflow>()
                .AddAllActivities(new ActivationActivities(context.Service)));
        var starter = new TemporalActivationWorkflowStarter(environment.Client);

        await worker.ExecuteAsync(async () =>
        {
            var first = starter.StartOrJoinAsync(context.Request, CancellationToken.None);
            await context.Billing.FirstCallEntered;
            var replay = starter.StartOrJoinAsync(context.Request, CancellationToken.None);
            context.Billing.ReleaseCalls();
            var outcomes = await Task.WhenAll(first, replay);

            Assert.Equal(outcomes[0], outcomes[1]);
            Assert.Equal(1, context.Billing.CallCount);
            await using var db = context.Factory.CreateDbContext();
            Assert.Single(await db.ActivationIntents.ToListAsync());
            Assert.Single(await db.RelationshipStateHistory.Where(value =>
                value.ToState == EmploymentRelationshipState.Active).ToListAsync());
        });
    }

    private static async Task<ActivationTestContext> CreateContextAsync()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var constitutional = new RecordingRelationshipConstitutionalGateway();
        var billing = new RecordingActivationBillingGateway();
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var contractId = Guid.NewGuid();
        var acceptanceId = Guid.NewGuid();
        var authoritySnapshotId = Guid.NewGuid();
        await using var db = factory.CreateDbContext();
        db.EmploymentRelationships.Add(new EmploymentRelationship
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ProfessionalType = "DMA",
            EvaluationIntentId = Guid.NewGuid(),
            InitiatingParticipantId = participantId,
            AcceptedContractId = contractId,
            AuthoritySnapshotId = authoritySnapshotId,
            State = EmploymentRelationshipState.ContractAcceptedPendingPayment,
            StateVersion = 5,
        });
        db.RelationshipParticipants.Add(new RelationshipParticipant
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ParticipantId = participantId,
            Role = RelationshipParticipantRole.Employer,
            BoundEvidenceId = Guid.NewGuid(),
        });
        db.EmploymentContractVersions.Add(new EmploymentContractVersion
        {
            TenantId = tenantId, RelationshipId = relationshipId, ContractId = contractId,
            Version = 1, ContractHash = new string('a', 64), AeecVersion = "1.0",
            DomainScheduleHash = new string('b', 64), CreatedByParticipantId = participantId,
        });
        db.ContractAcceptances.Add(new ContractAcceptance
        {
            TenantId = tenantId, RelationshipId = relationshipId, ContractId = contractId,
            ContractVersion = 1, ContractHash = new string('a', 64), AcceptanceId = acceptanceId,
            ParticipantId = participantId, ParticipantRole = RelationshipParticipantRole.Employer,
            AuthenticationAssurance = "AAL3_FRESH", AuthoritySnapshotId = authoritySnapshotId,
            ScopeConfirmationHash = new string('c', 64), AcceptanceEvidenceId = Guid.NewGuid(),
        });
        await db.SaveChangesAsync();
        var relationships = new EmploymentRelationshipService(
            factory, constitutional, NullLogger<EmploymentRelationshipService>.Instance);
        var service = new ActivationOrchestrationService(
            factory, relationships, constitutional, billing, new AllowOfferabilityGuard());
        var request = new ActivationRequest(
            tenantId, relationshipId, participantId, contractId, 1, acceptanceId,
            "pay_verified_123", Guid.NewGuid(), authoritySnapshotId, Guid.NewGuid());
        return new ActivationTestContext(service, factory, constitutional, billing, request);
    }

    private sealed class RecordingActivationBillingGateway : IActivationBillingGateway
    {
        private readonly TaskCompletionSource _firstCallEntered = new(TaskCreationOptions.RunContinuationsAsynchronously);
        private readonly TaskCompletionSource _releaseCalls = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public int CallCount { get; private set; }
        public bool FailNext { get; set; }
        public int FailuresRemaining { get; set; }
        public bool HoldCalls { get; set; }
        public Guid LastCorrelationId { get; private set; }
        public Task FirstCallEntered => _firstCallEntered.Task;

        public void ReleaseCalls() => _releaseCalls.TrySetResult();

        public async Task<ActivationBillingOutcome> ActivatePaidSubscriptionAsync(
            ActivationBillingRequest request, CancellationToken cancellationToken)
        {
            CallCount++;
            LastCorrelationId = request.CorrelationId;
            _firstCallEntered.TrySetResult();
            if (HoldCalls) await _releaseCalls.Task.WaitAsync(cancellationToken);
            if (FailNext || FailuresRemaining > 0)
            {
                FailNext = false;
                if (FailuresRemaining > 0) FailuresRemaining--;
                throw new ActivationOwnerUnavailableException("WBE unresolved.");
            }
            return new ActivationBillingOutcome(Guid.NewGuid(), "ACTIVE");
        }
    }

    private sealed class AllowOfferabilityGuard : IOfferabilityGuard
    {
        public Task RequireEligibleAsync(
            Guid tenantId, Guid relationshipId, CancellationToken cancellationToken) => Task.CompletedTask;
    }

    private sealed record ActivationTestContext(
        ActivationOrchestrationService Service,
        InMemoryEmploymentRelationshipFactory Factory,
        RecordingRelationshipConstitutionalGateway Constitutional,
        RecordingActivationBillingGateway Billing,
        ActivationRequest Request);

    private sealed class RecordingActivationWorkflowStarter : IActivationWorkflowStarter
    {
        public List<ActivationRequest> Requests { get; } = [];

        public Task<ActivationOutcome> StartOrJoinAsync(
            ActivationRequest request, CancellationToken cancellationToken)
        {
            Requests.Add(request);
            return Task.FromResult(new ActivationOutcome(
                Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), "SUCCEEDED"));
        }
    }
}