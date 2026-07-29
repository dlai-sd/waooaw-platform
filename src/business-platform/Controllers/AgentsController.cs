// Implements: architecture/reference/components/business-platform.md §1 Employment Manager
// constitutional_basis: C-023, C-038, C-059
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.ConstitutionalEngine.Grpc;
using Grpc.Net.Client;

namespace Waooaw.BusinessPlatform.Controllers;

/// <summary>
/// Implements POST /api/customers (RegisterCustomer) and POST /api/agents/hire (HireAgent).
/// Constitutional obligations:
///   C-023 — Evidence First: CE.ValidateAction confirmed before any state change.
///   C-038 — Pro-rata billing: ProRataBillingStartDate set at moment of hire.
///   C-059 — Implementation Traceability: header annotation on every file.
/// </summary>
[ApiController, Route("api")]
public sealed class AgentsController : ControllerBase
{
    private readonly IConfiguration _config;
    private readonly ILogger<AgentsController> _logger;

    // Constitutional basis: C-023 — no action executes without CE confirmation.
    // Constructor is ALL-POSITIONAL — no named arguments after positional (CS1744).
    public AgentsController(IConfiguration config, ILogger<AgentsController> logger)
    {
        _config = config;
        _logger = logger;
    }

    // ─── POST /api/customers ──────────────────────────────────────────────────

    /// <summary>
    /// Register a new customer. C-023: CE.ValidateAction called and confirmed before returning.
    /// </summary>
    [HttpPost("customers")]
    public async Task<IActionResult> RegisterCustomer(
        [FromBody] RegisterCustomerRequest request,
        CancellationToken cancellationToken)
    {
        // ── C-023: CE.ValidateAction is the constitutional pre-condition.
        // ⛔ CE call is NOT inside a DB transaction.
        var grpcUrl = _config["ConstitutionalEngine:GrpcUrl"]
            ?? throw new InvalidOperationException("ConstitutionalEngine:GrpcUrl is not configured.");

        using var channel = GrpcChannel.ForAddress(grpcUrl);
        var ceClient = new ConstitutionalService.ConstitutionalServiceClient(channel);

        ValidateActionResponse ceResponse;
        try
        {
            ceResponse = await ceClient.ValidateActionAsync(
                new ValidateActionRequest
                {
                    ContractId           = "",
                    ActionType           = "REGISTER_CUSTOMER",
                    ActionParameters     = $"{{\"email\":\"{request.Email}\"," +
                                           $"\"organisation\":\"{request.OrganisationName}\"," +
                                           $"\"display_name\":\"{request.DisplayName}\"}}",
                    DecisionSpaceVersion = 1,
                },
                cancellationToken: cancellationToken);
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1 — never swallow; always log before returning.
            _logger.LogError(ex,
                "CE.ValidateAction failed for RegisterCustomer: {Context}",
                $"email={request.Email}");
            return StatusCode(503, new { error = "Constitutional Engine unavailable. Registration blocked." });
        }

        if (ceResponse.Decision != PolicyDecision.Permit)
        {
            _logger.LogWarning(
                "CE denied RegisterCustomer for email={Email}: {Reason}",
                request.Email, ceResponse.Reason);
            return StatusCode(403, new { error = ceResponse.Reason });
        }

        // ── Happy path: CE permitted. Build response.
        var customerId   = Guid.NewGuid();
        var registeredAt = DateTimeOffset.UtcNow;

        var response = new RegisterCustomerResponse(
            customerId,
            request.DisplayName,
            request.Email,
            request.OrganisationName,
            registeredAt);

        _logger.LogInformation(
            "Customer registered: CustomerId={CustomerId} Email={Email} Organisation={Organisation} RegisteredAt={RegisteredAt}",
            customerId, request.Email, request.OrganisationName, registeredAt);

        return Ok(response);
    }

    // ─── POST /api/agents/hire ────────────────────────────────────────────────

    /// <summary>
    /// Hire a professional agent under an existing employment contract.
    /// C-023: CE.ValidateAction confirmed before returning.
    /// C-038: ProRataBillingStartDate set to UtcNow at the instant of hire.
    /// </summary>
    [HttpPost("agents/hire")]
    public async Task<IActionResult> HireAgent(
        [FromBody] HireAgentRequest request,
        CancellationToken cancellationToken)
    {
        // ── C-023: CE.ValidateAction is the constitutional pre-condition.
        // ⛔ CE call is NOT inside a DB transaction.
        var grpcUrl = _config["ConstitutionalEngine:GrpcUrl"]
            ?? throw new InvalidOperationException("ConstitutionalEngine:GrpcUrl is not configured.");

        using var channel = GrpcChannel.ForAddress(grpcUrl);
        var ceClient = new ConstitutionalService.ConstitutionalServiceClient(channel);

        ValidateActionResponse ceResponse;
        try
        {
            ceResponse = await ceClient.ValidateActionAsync(
                new ValidateActionRequest
                {
                    ContractId           = request.ContractId.ToString(),
                    ActionType           = "HIRE_AGENT",
                    ActionParameters     = $"{{\"professional_type\":\"{request.ProfessionalType}\"," +
                                           $"\"skill_id\":\"{request.SkillId}\"," +
                                           $"\"approved_budget_inr_paise\":{request.ApprovedBudgetInrPaise}}}",
                    DecisionSpaceVersion = 1,
                },
                cancellationToken: cancellationToken);
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1 — never swallow; always log before returning.
            _logger.LogError(ex,
                "CE.ValidateAction failed for HireAgent: {Context}",
                $"contractId={request.ContractId} professionalType={request.ProfessionalType}");
            return StatusCode(503, new { error = "Constitutional Engine unavailable. Hire blocked." });
        }

        if (ceResponse.Decision != PolicyDecision.Permit)
        {
            _logger.LogWarning(
                "CE denied HireAgent for ContractId={ContractId} ProfessionalType={ProfessionalType}: {Reason}",
                request.ContractId, request.ProfessionalType, ceResponse.Reason);
            return StatusCode(403, new { error = ceResponse.Reason });
        }

        // ── C-038: Pro-rata billing start date MUST be captured at the exact instant of hire.
        // This timestamp is the authoritative billing anchor — do not derive from any other source.
        var proRataBillingStartDate = DateTimeOffset.UtcNow;
        var evidenceRecordId        = Guid.NewGuid().ToString();

        // ── C-023: Record evidence via CE before returning success.
        try
        {
            await ceClient.RecordEvidenceAsync(
                new RecordEvidenceRequest
                {
                    ContractId            = request.ContractId.ToString(),
                    ActionType            = "HIRE_AGENT",
                    State                 = "EXECUTED",
                    ConstitutionalBasis   = "C-023,C-038",
                    DecisionSpaceVersion  = 1,
                    IsScopeBoundary       = false,
                },
                cancellationToken: cancellationToken);
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1 — CE evidence recording failure is logged but does not
            // roll back the permit already granted; the hire still returns success.
            // The CE ValidateAction permit is already durable at CE side.
            _logger.LogError(ex,
                "CE.RecordEvidence failed after HireAgent permit: {Context}",
                $"contractId={request.ContractId} professionalType={request.ProfessionalType}");
            // Intentional: do not fail the hire — CE ValidateAction already committed the permit.
            // A background reconciliation job will detect and re-submit missing evidence records.
        }

        var response = new HireAgentResponse(
            request.ContractId,
            request.ProfessionalType,
            request.SkillId,
            request.ApprovedBudgetInrPaise,
            proRataBillingStartDate,    // C-038 — billing anchor set at hire instant
            "ACTIVE",
            evidenceRecordId);

        _logger.LogInformation(
            "Agent hired: ContractId={ContractId} ProfessionalType={ProfessionalType} " +
            "SkillId={SkillId} BudgetInrPaise={BudgetInrPaise} BillingStart={BillingStart}",
            request.ContractId,
            request.ProfessionalType,
            request.SkillId,
            request.ApprovedBudgetInrPaise,
            proRataBillingStartDate);

        return Ok(response);
    }
}