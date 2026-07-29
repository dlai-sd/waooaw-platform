using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Grpc.Net.Client;
using Grpc.Core;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace Waooaw.BusinessPlatform.Services;

/// <summary>
/// Implements the Employment Manager component for customer registration and agent hire.
/// Constitutional basis: C-023 (Evidence First), C-038 (Pro-rata billing), C-059 (Traceability).
/// Every mutating operation calls CE.ValidateAction BEFORE execution and CE.RecordEvidence
/// BEFORE returning success. CE calls are pre-conditions — never inside a DB transaction.
/// </summary>
public sealed class EmploymentService
{
    private readonly IConfiguration _config;
    private readonly ILogger<EmploymentService> _logger;

    // C-038: Pro-rata billing anchor — billing start is the moment the hire record is created.
    private const string ActionTypeRegisterCustomer  = "REGISTER_CUSTOMER";
    private const string ActionTypeHireAgent          = "HIRE_AGENT";
    private const string EvidenceTypeCustomerCreated  = "CUSTOMER_REGISTERED";
    private const string EvidenceTypeContractFormed   = "EMPLOYMENT_CONTRACT_FORMED";
    private const int    DecisionSpaceVersionDefault  = 1;
    private const int    CeCallTimeoutSeconds         = 10; // ERROR HANDLING RULE 4

    public EmploymentService(IConfiguration config, ILogger<EmploymentService> logger)
    {
        _config = config ?? throw new ArgumentNullException(nameof(config));
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    // ─── RegisterCustomer ─────────────────────────────────────────────────────

    /// <summary>
    /// Registers a new customer (tenant).
    /// Pre-condition: CE.ValidateAction ALLOW required (C-023).
    /// Post-condition: CE.RecordEvidence written before response returned (AD-002).
    /// </summary>
    public async Task<RegisterCustomerResponse> RegisterCustomerAsync(
        RegisterCustomerRequest request,
        string tenantId,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(request);

        var ceGrpcUrl = _config["ConstitutionalEngine:GrpcUrl"]
            ?? throw new InvalidOperationException("ConstitutionalEngine:GrpcUrl is not configured.");

        // ── Step 1: CE.ValidateAction — MUST precede execution (C-023) ──────────
        // ⛔ Do NOT call CE inside a DB transaction.
        using var channel = GrpcChannel.ForAddress(ceGrpcUrl);
        var ceClient = new ConstitutionalService.ConstitutionalServiceClient(channel);

        ValidateActionResponse validateResponse;
        try
        {
            using var validateCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            validateCts.CancelAfter(TimeSpan.FromSeconds(CeCallTimeoutSeconds));

            var validateRequest = new ValidateActionRequest
            {
                ContractId           = tenantId,
                ActionType           = ActionTypeRegisterCustomer,
                ActionParameters     = $"{{\"display_name\":\"{request.DisplayName}\",\"email\":\"{request.Email}\"}}",
                DecisionSpaceVersion = DecisionSpaceVersionDefault,
            };

            var validateHeaders = new Metadata { { "x-tenant-id", tenantId } };
            validateResponse = await ceClient.ValidateActionAsync(
                validateRequest,
                validateHeaders,
                deadline: DateTime.UtcNow.AddSeconds(CeCallTimeoutSeconds),
                validateCts.Token);
        }
        catch (RpcException ex)
        {
            // ERROR HANDLING RULE 3: map gRPC exceptions to StatusCode
            _logger.LogError(ex, "CE.ValidateAction failed for RegisterCustomer: {TenantId}", tenantId);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1: never swallow silently
            _logger.LogError(ex, "Unexpected error during CE.ValidateAction for RegisterCustomer: {TenantId}", tenantId);
            throw;
        }

        if (validateResponse.Decision != PolicyDecision.Permit)
        {
            _logger.LogWarning(
                "CE denied RegisterCustomer for tenant {TenantId}. Reason: {Reason}",
                tenantId,
                validateResponse.Reason);
            throw new InvalidOperationException(
                $"Constitutional Engine denied registration: {validateResponse.Reason}");
        }

        // ── Step 2: Execute — synthesise the customer record ─────────────────
        var customerId   = Guid.NewGuid();
        var registeredAt = DateTimeOffset.UtcNow;

        _logger.LogInformation(
            "RegisterCustomer: tenant={TenantId} customerId={CustomerId}", tenantId, customerId);

        // ── Step 3: CE.RecordEvidence — Evidence First (AD-002, C-023) ───────
        // Only return success AFTER evidence is confirmed durable.
        RecordEvidenceResponse evidenceResponse;
        try
        {
            using var evCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            evCts.CancelAfter(TimeSpan.FromSeconds(CeCallTimeoutSeconds));

            var evidenceRequest = new RecordEvidenceRequest
            {
                ActionInstanceId     = customerId.ToString(),
                ContractId           = customerId.ToString(),
                ProfessionalId       = "system",
                ActionType           = EvidenceTypeCustomerCreated,
                State                = EvidenceState.Executed,
                ExecutedContent      = $"{{\"customer_id\":\"{customerId}\",\"email\":\"{request.Email}\"}}",
                IsScopeBoundary      = false,
                DecisionSpaceVersion = DecisionSpaceVersionDefault,
                ConstitutionalBasis  = "C-023,C-038,C-059",
            };

            var evidenceHeaders = new Metadata { { "x-tenant-id", tenantId } };
            evidenceResponse = await ceClient.RecordEvidenceAsync(
                evidenceRequest,
                evidenceHeaders,
                deadline: DateTime.UtcNow.AddSeconds(CeCallTimeoutSeconds),
                evCts.Token);
        }
        catch (RpcException ex)
        {
            // ERROR HANDLING RULE 3
            _logger.LogError(ex, "CE.RecordEvidence failed for RegisterCustomer: {CustomerId}", customerId);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1
            _logger.LogError(ex, "Unexpected error during CE.RecordEvidence for RegisterCustomer: {CustomerId}", customerId);
            throw;
        }

        _logger.LogInformation(
            "RegisterCustomer evidence recorded: evidenceId={EvidenceId} customerId={CustomerId}",
            evidenceResponse.EvidenceRecordId,
            customerId);

        // Return only after evidence is durable (Evidence First — AD-002).
        return new RegisterCustomerResponse(
            customerId,
            request.DisplayName,
            request.Email,
            request.OrganisationName,
            registeredAt);
    }

    // ─── HireAgent ────────────────────────────────────────────────────────────

    /// <summary>
    /// Hires an agent by forming an employment contract.
    /// Pre-condition: CE.ValidateAction ALLOW required (C-023).
    /// Post-condition: CE.RecordEvidence written before response returned (AD-002).
    /// C-038: ProRataBillingStartDate is set to the instant the contract record is created —
    ///        never back-dated, never deferred.
    /// </summary>
    public async Task<HireAgentResponse> HireAgentAsync(
        HireAgentRequest request,
        string tenantId,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(request);

        var ceGrpcUrl = _config["ConstitutionalEngine:GrpcUrl"]
            ?? throw new InvalidOperationException("ConstitutionalEngine:GrpcUrl is not configured.");

        // ── Step 1: CE.ValidateAction — MUST precede execution (C-023) ──────────
        // ⛔ Do NOT call CE inside a DB transaction.
        using var channel = GrpcChannel.ForAddress(ceGrpcUrl);
        var ceClient = new ConstitutionalService.ConstitutionalServiceClient(channel);

        ValidateActionResponse validateResponse;
        try
        {
            using var validateCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            validateCts.CancelAfter(TimeSpan.FromSeconds(CeCallTimeoutSeconds));

            var validateRequest = new ValidateActionRequest
            {
                ContractId           = request.ContractId.ToString(),
                ActionType           = ActionTypeHireAgent,
                ActionParameters     = $"{{\"professional_type\":\"{request.ProfessionalType}\"," +
                                       $"\"skill_id\":\"{request.SkillId}\"," +
                                       $"\"approved_budget_inr_paise\":{request.ApprovedBudgetInrPaise}}}",
                DecisionSpaceVersion = DecisionSpaceVersionDefault,
            };

            var validateHeaders = new Metadata { { "x-tenant-id", tenantId } };
            validateResponse = await ceClient.ValidateActionAsync(
                validateRequest,
                validateHeaders,
                deadline: DateTime.UtcNow.AddSeconds(CeCallTimeoutSeconds),
                validateCts.Token);
        }
        catch (RpcException ex)
        {
            // ERROR HANDLING RULE 3
            _logger.LogError(ex, "CE.ValidateAction failed for HireAgent: tenantId={TenantId} contractId={ContractId}",
                tenantId, request.ContractId);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1
            _logger.LogError(ex, "Unexpected error during CE.ValidateAction for HireAgent: tenantId={TenantId} contractId={ContractId}",
                tenantId, request.ContractId);
            throw;
        }

        if (validateResponse.Decision != PolicyDecision.Permit)
        {
            _logger.LogWarning(
                "CE denied HireAgent for tenant {TenantId} contractId={ContractId}. Reason: {Reason}",
                tenantId,
                request.ContractId,
                validateResponse.Reason);
            throw new InvalidOperationException(
                $"Constitutional Engine denied hire: {validateResponse.Reason}");
        }

        // ── Step 2: Execute — synthesise the contract record ─────────────────
        // C-038: Pro-rata billing start is the instant of contract creation.
        // This timestamp is captured BEFORE CE.RecordEvidence so that evidence
        // carries the authoritative billing anchor.
        var proRataBillingStartDate = DateTimeOffset.UtcNow;
        var actionInstanceId        = Guid.NewGuid().ToString();
        const string initialState   = "EVALUATION";

        _logger.LogInformation(
            "HireAgent: tenant={TenantId} contractId={ContractId} skill={SkillId} billingStart={BillingStart:O}",
            tenantId,
            request.ContractId,
            request.SkillId,
            proRataBillingStartDate);

        // ── Step 3: CE.RecordEvidence — Evidence First (AD-002, C-023) ───────
        // Return success ONLY after evidence is confirmed durable.
        RecordEvidenceResponse evidenceResponse;
        try
        {
            using var evCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            evCts.CancelAfter(TimeSpan.FromSeconds(CeCallTimeoutSeconds));

            var evidenceRequest = new RecordEvidenceRequest
            {
                ActionInstanceId     = actionInstanceId,
                ContractId           = request.ContractId.ToString(),
                ProfessionalId       = request.ProfessionalType,
                ActionType           = EvidenceTypeContractFormed,
                State                = EvidenceState.Executed,
                ExecutedContent      = $"{{\"contract_id\":\"{request.ContractId}\"," +
                                       $"\"professional_type\":\"{request.ProfessionalType}\"," +
                                       $"\"skill_id\":\"{request.SkillId}\"," +
                                       $"\"approved_budget_inr_paise\":{request.ApprovedBudgetInrPaise}," +
                                       $"\"pro_rata_billing_start_date\":\"{proRataBillingStartDate:O}\"," +
                                       $"\"state\":\"{initialState}\"}}",
                IsScopeBoundary      = false,
                DecisionSpaceVersion = DecisionSpaceVersionDefault,
                ConstitutionalBasis  = "C-023,C-038,C-059",
            };

            var evidenceHeaders = new Metadata { { "x-tenant-id", tenantId } };
            evidenceResponse = await ceClient.RecordEvidenceAsync(
                evidenceRequest,
                evidenceHeaders,
                deadline: DateTime.UtcNow.AddSeconds(CeCallTimeoutSeconds),
                evCts.Token);
        }
        catch (RpcException ex)
        {
            // ERROR HANDLING RULE 3
            _logger.LogError(ex, "CE.RecordEvidence failed for HireAgent: contractId={ContractId}", request.ContractId);
            throw new RpcException(new Status(StatusCode.Internal, ex.Message));
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1
            _logger.LogError(ex, "Unexpected error during CE.RecordEvidence for HireAgent: contractId={ContractId}", request.ContractId);
            throw;
        }

        _logger.LogInformation(
            "HireAgent evidence recorded: evidenceId={EvidenceId} contractId={ContractId} billingStart={BillingStart:O}",
            evidenceResponse.EvidenceRecordId,
            request.ContractId,
            proRataBillingStartDate);

        // Return only after evidence is durable (Evidence First — AD-002).
        // C-038: ProRataBillingStartDate is the authoritative billing anchor captured above.
        return new HireAgentResponse(
            request.ContractId,
            request.ProfessionalType,
            request.SkillId,
            request.ApprovedBudgetInrPaise,
            proRataBillingStartDate,
            initialState,
            evidenceResponse.EvidenceRecordId);
    }
}