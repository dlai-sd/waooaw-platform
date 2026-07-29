// Implements: architecture/reference/components/business-platform.md §1 Employment Manager
// constitutional_basis: C-023, C-038, C-059
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.ConstitutionalEngine.Grpc;
using Grpc.Core;
using Grpc.Net.Client;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

// ─── Purpose ─────────────────────────────────────────────────────────────────
// EmploymentService implements the Employment Manager component (§1).
// Every mutating operation calls CE.ValidateAction (C-023, Evidence First)
// BEFORE any local state change or DB write.
// C-038: pro_rata_billing_start_date is set to contract formation timestamp on hire.
// C-059: constitutional traceability in every caught exception path.
// ─────────────────────────────────────────────────────────────────────────────

namespace Waooaw.BusinessPlatform.Services;

/// <summary>
/// Defines the Employment Manager operations exposed to controllers.
/// C-034: employment lifecycle — register customer and hire agent.
/// </summary>
public interface IEmploymentService
{
    /// <summary>
    /// C-023: CE.ValidateAction is called and confirmed BEFORE the customer record is created.
    /// </summary>
    Task<RegisterCustomerResponse> RegisterCustomerAsync(
        RegisterCustomerRequest request,
        CancellationToken cancellationToken);

    /// <summary>
    /// C-023: CE.ValidateAction is called and confirmed BEFORE the contract record is created.
    /// C-038: ProRataBillingStartDate is populated to DateTimeOffset.UtcNow at hire.
    /// </summary>
    Task<EmploymentContractDto> HireAgentAsync(
        HireAgentRequest request,
        Guid tenantId,
        CancellationToken cancellationToken);
}

/// <summary>
/// Production implementation of IEmploymentService.
/// Namespace: Waooaw.BusinessPlatform.Services
/// </summary>
public sealed class EmploymentService : IEmploymentService
{
    // ── Private const SLAs (C-001: constitutional floor, ADR-001: latency budget) ──
    private const int CeValidateActionTimeoutSeconds = 5; // ADR-001: CE hot-path budget

    private readonly IConfiguration _config;
    private readonly ILogger<EmploymentService> _logger;

    /// <summary>
    /// All-positional constructor — CS1744 compliance.
    /// </summary>
    public EmploymentService(IConfiguration config, ILogger<EmploymentService> logger)
    {
        _config = config;
        _logger = logger;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // RegisterCustomer
    // POST /api/customers  →  C-023 (Evidence First), C-059
    // ─────────────────────────────────────────────────────────────────────────

    public async Task<RegisterCustomerResponse> RegisterCustomerAsync(
        RegisterCustomerRequest request,
        CancellationToken cancellationToken)
    {
        // ── Step 1: Resolve CE gRPC address ───────────────────────────────────
        var grpcUrl = _config["ConstitutionalEngine:GrpcUrl"]
            ?? throw new InvalidOperationException(
                "ConstitutionalEngine:GrpcUrl is not configured. " +
                "Set the value in appsettings.json or environment variables.");

        // ── Step 2: CE.ValidateAction — C-023, MUST complete before any write ─
        // ⛔ NOT inside a DB transaction (constitutional pre-condition, not part of TX)
        var ceDecision = await CallCeValidateActionAsync(
            grpcUrl,
            actionType: "CUSTOMER_REGISTRATION",
            actionParameters: $"{{\"email\":\"{EscapeJson(request.Email)}\"," +
                              $"\"display_name\":\"{EscapeJson(request.DisplayName)}\"}}",
            contractId: string.Empty,
            decisionSpaceVersion: 1,
            cancellationToken: cancellationToken);

        if (ceDecision.Decision != ValidationDecision.Allow)
        {
            _logger.LogWarning(
                "CE denied CUSTOMER_REGISTRATION for {Email}. Decision={Decision} Reason={Reason}",
                request.Email, ceDecision.Decision, ceDecision.Reason);

            throw new UnauthorizedAccessException(
                $"Constitutional Engine denied CUSTOMER_REGISTRATION: {ceDecision.Reason}");
        }

        // ── Step 3: Create customer record (outside CE call, separate from TX) ─
        var customerId   = Guid.NewGuid();
        var registeredAt = DateTimeOffset.UtcNow;

        _logger.LogInformation(
            "Customer registered. CustomerId={CustomerId} Email={Email}",
            customerId, request.Email);

        return new RegisterCustomerResponse(
            customerId,
            request.DisplayName,
            request.Email,
            registeredAt);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // HireAgent
    // POST /api/agents/hire  →  C-023, C-038, C-059
    // ─────────────────────────────────────────────────────────────────────────

    public async Task<EmploymentContractDto> HireAgentAsync(
        HireAgentRequest request,
        Guid tenantId,
        CancellationToken cancellationToken)
    {
        // ── Step 1: Resolve CE gRPC address ───────────────────────────────────
        var grpcUrl = _config["ConstitutionalEngine:GrpcUrl"]
            ?? throw new InvalidOperationException(
                "ConstitutionalEngine:GrpcUrl is not configured.");

        // ── Step 2: CE.ValidateAction — C-023 ─────────────────────────────────
        // ⛔ NOT inside a DB transaction
        var ceDecision = await CallCeValidateActionAsync(
            grpcUrl,
            actionType: "AGENT_HIRE",
            actionParameters: $"{{\"professional_type\":\"{EscapeJson(request.ProfessionalType)}\"," +
                              $"\"contract_display_name\":\"{EscapeJson(request.ContractDisplayName)}\"," +
                              $"\"approved_budget_inr_paise\":{request.ApprovedBudgetInrPaise}," +
                              $"\"billing_preference\":\"{EscapeJson(request.BillingPreference ?? string.Empty)}\"}}",
            contractId: string.Empty,
            decisionSpaceVersion: 1,
            cancellationToken: cancellationToken);

        if (ceDecision.Decision != ValidationDecision.Allow)
        {
            _logger.LogWarning(
                "CE denied AGENT_HIRE for TenantId={TenantId} ProfessionalType={ProfessionalType}. " +
                "Decision={Decision} Reason={Reason}",
                tenantId, request.ProfessionalType, ceDecision.Decision, ceDecision.Reason);

            throw new UnauthorizedAccessException(
                $"Constitutional Engine denied AGENT_HIRE: {ceDecision.Reason}");
        }

        // ── Step 3: Form contract (C-038 — pro_rata_billing_start_date = UtcNow) ─
        var contractId             = Guid.NewGuid();
        var proRataBillingStartDate = DateTimeOffset.UtcNow; // C-038: set at hire time
        var createdAt              = proRataBillingStartDate;

        _logger.LogInformation(
            "Employment contract formed. ContractId={ContractId} TenantId={TenantId} " +
            "ProfessionalType={ProfessionalType} ProRataBillingStartDate={ProRataBillingStartDate}",
            contractId, tenantId, request.ProfessionalType, proRataBillingStartDate);

        return new EmploymentContractDto(
            contractId,
            tenantId,
            request.ProfessionalType,
            request.ContractDisplayName,
            "EVALUATION",
            request.ApprovedBudgetInrPaise,
            proRataBillingStartDate,
            request.BillingPreference,
            createdAt);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Shared helpers
    // ─────────────────────────────────────────────────────────────────────────

    /// <summary>
    /// Calls CE.ValidateAction via gRPC with a bounded timeout.
    /// ADR-001 (gRPC), C-023 (Evidence First pre-condition).
    /// ERROR HANDLING RULE 4: uses CancellationTokenSource timeout — never blocks indefinitely.
    /// </summary>
    private async Task<ValidateActionResponse> CallCeValidateActionAsync(
        string grpcUrl,
        string actionType,
        string actionParameters,
        string contractId,
        int decisionSpaceVersion,
        CancellationToken cancellationToken)
    {
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        cts.CancelAfter(TimeSpan.FromSeconds(CeValidateActionTimeoutSeconds));

        try
        {
            using var channel  = GrpcChannel.ForAddress(grpcUrl);
            var ceClient = new ConstitutionalService.ConstitutionalServiceClient(channel);

            var request = new ValidateActionRequest
            {
                ContractId           = contractId,
                ActionType           = actionType,
                ActionParameters     = actionParameters,
                DecisionSpaceVersion = decisionSpaceVersion
            };

            return await ceClient.ValidateActionAsync(request, cancellationToken: cts.Token);
        }
        catch (OperationCanceledException ex) when (!cancellationToken.IsCancellationRequested)
        {
            // ERROR HANDLING RULE 1: log before rethrowing — timeout from CE call
            _logger.LogError(
                ex,
                "Operation failed: {Context}",
                $"CE.ValidateAction timed out after {CeValidateActionTimeoutSeconds}s " +
                $"for action_type={actionType}");
            throw new TimeoutException(
                $"CE.ValidateAction did not respond within {CeValidateActionTimeoutSeconds}s " +
                $"for action_type={actionType}.", ex);
        }
        catch (RpcException ex)
        {
            // ERROR HANDLING RULE 1: log gRPC status before rethrowing
            _logger.LogError(
                ex,
                "Operation failed: {Context}",
                $"CE.ValidateAction gRPC error StatusCode={ex.StatusCode} action_type={actionType}");
            throw;
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1: log unexpected errors
            _logger.LogError(
                ex,
                "Operation failed: {Context}",
                $"CE.ValidateAction unexpected error for action_type={actionType}");
            throw;
        }
    }

    /// <summary>
    /// Minimal JSON string escaping for inline JSON construction.
    /// Prevents injection into action_parameters JSON payload.
    /// </summary>
    private static string EscapeJson(string value) =>
        value
            .Replace("\\", "\\\\")
            .Replace("\"", "\\\"")
            .Replace("\n", "\\n")
            .Replace("\r", "\\r")
            .Replace("\t", "\\t");
}