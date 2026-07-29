// Implements: architecture/reference/components/business-platform.md §1 Employment Manager
// constitutional_basis: C-023, C-038, C-059
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.ConstitutionalEngine.Grpc;
using Grpc.Net.Client;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace Waooaw.BusinessPlatform.Services;

// C-023: Evidence First — CE.ValidateAction must be called and confirmed BEFORE any state mutation.
// C-038: Pro-rata billing start date is stamped at the moment of hire.
// C-059: Every caught exception is logged; nothing is swallowed silently.

/// <summary>
/// Result returned by <see cref="EmploymentService.RegisterCustomerAsync"/>.
/// </summary>
public sealed record RegisterCustomerResult(
    bool Success,
    Guid? CustomerId,
    string? DenialReason);

/// <summary>
/// Result returned by <see cref="EmploymentService.HireAgentAsync"/>.
/// C-038: <see cref="ProRataBillingStartDate"/> is populated on every successful hire.
/// </summary>
public sealed record HireAgentResult(
    bool Success,
    Guid? AgentId,
    DateTimeOffset? ProRataBillingStartDate,
    string? DenialReason);

/// <summary>
/// Implements the Employment Manager component (§1).
/// All public methods are constitutional call sites: CE.ValidateAction is invoked as a
/// pre-condition, outside any database transaction, before any state is mutated.
/// </summary>
public sealed class EmploymentService
{
    // C-001: constitutional constant — CE latency SLA
    private const int CeValidateActionTimeoutSeconds = 5;

    private readonly IConfiguration _config;
    private readonly ILogger<EmploymentService> _logger;

    public EmploymentService(IConfiguration config, ILogger<EmploymentService> logger)
    {
        _config = config;
        _logger = logger;
    }

    // ─── Internal helpers ────────────────────────────────────────────────────

    /// <summary>
    /// Creates a fresh gRPC client for the Constitutional Engine.
    /// Channel is not cached here — callers are short-lived request handlers.
    /// ADR-001: gRPC is the only transport to the CE.
    /// </summary>
    private ConstitutionalService.ConstitutionalServiceClient CreateCeClient()
    {
        var url = _config["ConstitutionalEngine:GrpcUrl"]
            ?? throw new InvalidOperationException(
                "ConstitutionalEngine:GrpcUrl is not configured. " +
                "Add it to appsettings.json or environment variables.");

        var channel = GrpcChannel.ForAddress(url);
        return new ConstitutionalService.ConstitutionalServiceClient(channel);
    }

    /// <summary>
    /// Minimal JSON string escaping to prevent injection in action parameters.
    /// </summary>
    private static string EscapeJson(string value)
        => value
            .Replace("\\", "\\\\")
            .Replace("\"", "\\\"")
            .Replace("\n", "\\n")
            .Replace("\r", "\\r")
            .Replace("\t", "\\t");

    // ─── RegisterCustomer ────────────────────────────────────────────────────

    /// <summary>
    /// Registers a new customer.
    /// C-023: CE.ValidateAction is called and confirmed before any record is created.
    /// </summary>
    public async Task<RegisterCustomerResult> RegisterCustomerAsync(
        RegisterCustomerRequest request,
        CancellationToken cancellationToken)
    {
        // ── Step 1: CE.ValidateAction (C-023 — must precede every state change) ──
        ValidateActionResponse ceResponse;
        try
        {
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            cts.CancelAfter(TimeSpan.FromSeconds(CeValidateActionTimeoutSeconds));

            var ceClient = CreateCeClient();
            ceResponse = await ceClient.ValidateActionAsync(
                new ValidateActionRequest
                {
                    ContractId           = string.Empty,   // no contract yet for new customer
                    ActionType           = "REGISTER_CUSTOMER",
                    ActionParameters     = $"{{\"email\":\"{EscapeJson(request.Email)}\",\"name\":\"{EscapeJson(request.Name)}\"}}",
                    DecisionSpaceVersion = 1,
                },
                cancellationToken: cts.Token);
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1 + C-059: log before rethrowing; never swallow.
            _logger.LogError(
                ex,
                "CE.ValidateAction failed for RegisterCustomer — Operation failed: {Context}",
                $"email={request.Email}");
            throw;
        }

        // C-023: Only allow action if CE explicitly returns Allow.
        // ⛔ CS0019 guard: Decision is ValidationDecision, NOT PolicyDecision.
        if (ceResponse.Decision != ValidationDecision.Allow)
        {
            _logger.LogWarning(
                "CE denied RegisterCustomer for email={Email}. Decision={Decision} Reason={Reason}",
                request.Email,
                ceResponse.Decision,
                ceResponse.Reason);

            return new RegisterCustomerResult(false, null, ceResponse.Reason);
        }

        // ── Step 2: Business logic — create customer record ──────────────────
        // (DB write would happen here; placeholder Guid represents persisted CustomerId)
        var customerId = Guid.NewGuid();

        _logger.LogInformation(
            "Customer registered successfully. CustomerId={CustomerId} Email={Email}",
            customerId,
            request.Email);

        return new RegisterCustomerResult(true, customerId, null);
    }

    // ─── HireAgent ───────────────────────────────────────────────────────────

    /// <summary>
    /// Hires a professional agent against an existing contract.
    /// C-023: CE.ValidateAction is called and confirmed before any record is created.
    /// C-038: <see cref="HireAgentResult.ProRataBillingStartDate"/> is stamped at the moment
    ///        the CE permits the action — never retroactively adjusted.
    /// </summary>
    public async Task<HireAgentResult> HireAgentAsync(
        HireAgentRequest request,
        CancellationToken cancellationToken)
    {
        // ── Step 1: CE.ValidateAction (C-023 — precondition, outside any DB TX) ──
        ValidateActionResponse ceResponse;
        try
        {
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            cts.CancelAfter(TimeSpan.FromSeconds(CeValidateActionTimeoutSeconds));

            var ceClient = CreateCeClient();

            // Build action parameters as a minimal JSON object.
            // All values are escaped to prevent injection (C-059).
            var actionParameters =
                $"{{" +
                $"\"contractId\":\"{EscapeJson(request.ContractId)}\"," +
                $"\"professionalType\":\"{EscapeJson(request.ProfessionalType)}\"," +
                $"\"skillId\":\"{EscapeJson(request.SkillId)}\"," +
                $"\"approvedBudgetInrPaise\":\"{request.ApprovedBudgetInrPaise}\"," +
                $"\"billingCycleAnchorDay\":\"{EscapeJson(request.BillingCycleAnchorDay)}\"" +
                $"}}";

            ceResponse = await ceClient.ValidateActionAsync(
                new ValidateActionRequest
                {
                    ContractId           = request.ContractId,
                    ActionType           = "HIRE_AGENT",
                    ActionParameters     = actionParameters,
                    DecisionSpaceVersion = int.TryParse(request.DecisionSpaceVersion, out var dsvE) ? dsvE : 1,
                },
                cancellationToken: cts.Token);
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1 + C-059: log before rethrowing; never swallow.
            _logger.LogError(
                ex,
                "CE.ValidateAction failed for HireAgent — Operation failed: {Context}",
                $"contractId={request.ContractId} professionalType={request.ProfessionalType}");
            throw;
        }

        // C-023: Only proceed if CE explicitly returns Allow.
        // ⛔ CS0019 guard: Decision is ValidationDecision, NOT PolicyDecision.
        if (ceResponse.Decision != ValidationDecision.Allow)
        {
            _logger.LogWarning(
                "CE denied HireAgent. ContractId={ContractId} ProfessionalType={ProfessionalType} " +
                "Decision={Decision} Reason={Reason}",
                request.ContractId,
                request.ProfessionalType,
                ceResponse.Decision,
                ceResponse.Reason);

            return new HireAgentResult(false, null, null, ceResponse.Reason);
        }

        // ── Step 2: C-038 — stamp billing start date at the instant CE granted approval ──
        // This timestamp is the constitutional anchor for all pro-rata calculations.
        // It must NOT be derived from a DB write timestamp — it is the CE approval moment.
        var proRataBillingStartDate = DateTimeOffset.UtcNow;

        // ── Step 3: Business logic — persist agent record ────────────────────
        // (DB write would happen here; placeholder Guid represents persisted AgentId)
        var agentId = Guid.NewGuid();

        _logger.LogInformation(
            "Agent hired successfully. AgentId={AgentId} ContractId={ContractId} " +
            "ProfessionalType={ProfessionalType} ProRataBillingStartDate={ProRataBillingStartDate}",
            agentId,
            request.ContractId,
            request.ProfessionalType,
            proRataBillingStartDate);

        // C-038: ProRataBillingStartDate is always populated on success.
        return new HireAgentResult(true, agentId, proRataBillingStartDate, null);
    }
}