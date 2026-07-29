// Implements: architecture/reference/components/business-platform.md §1 Employment Manager
// constitutional_basis: C-023, C-038, C-059
using Microsoft.AspNetCore.Mvc;
using Waooaw.ConstitutionalEngine.Grpc;
using Grpc.Net.Client;

// NOTE: Waooaw.ConstitutionalEngine.Evaluators is a CE-internal namespace.
// Business Platform calls CE via gRPC only — no direct evaluator assembly reference.

namespace Waooaw.BusinessPlatform.Controllers;

// ─── Request / Response DTOs ──────────────────────────────────────────────────

/// <summary>Payload for POST /api/customers — customer self-registration.</summary>
public sealed record RegisterCustomerRequest(
    string DisplayName,
    string Email,
    string? PreferredLanguage
);

/// <summary>Response body returned after customer registration.</summary>
public sealed record RegisterCustomerResponse(
    Guid CustomerId,
    string DisplayName,
    string Email,
    DateTimeOffset RegisteredAt
);

/// <summary>Payload for POST /api/agents/hire — create a new employment contract (C-034, C-038).</summary>
public sealed record HireAgentRequest(
    string ProfessionalType,
    string ContractDisplayName,
    long ApprovedBudgetInrPaise,
    string? BillingPreference      // "SEPARATE" | "COMBINED"
);

/// <summary>Employment contract DTO returned on hire. C-038: includes pro-rata billing start.</summary>
public sealed record EmploymentContractDto(
    Guid ContractId,
    Guid TenantId,
    string ProfessionalType,
    string ContractDisplayName,
    string State,                                    // EVALUATION | ACTIVE | SUSPENDED | TERMINATED
    long ApprovedBudgetInrPaise,
    DateTimeOffset ProRataBillingStartDate,          // C-038 — set at hire time
    string? BillingPreference,
    DateTimeOffset CreatedAt
);

// ─── Controller ───────────────────────────────────────────────────────────────

[ApiController, Route("api/v1")]
public sealed class CustomersController : ControllerBase
{
    // ADR-001 latency budget: CE calls must complete within 5 s.
    private const int CeCallTimeoutSeconds = 5;

    private readonly IConfiguration _config;
    private readonly ILogger<CustomersController> _logger;

    public CustomersController(
        IConfiguration config,
        ILogger<CustomersController> logger)
    {
        _config = config;
        _logger = logger;
    }

    // ── pre-existing stubs (WC013-02a) — MUST NOT be removed ────────────────

    [HttpPost("employment/contracts")]
    public IActionResult FormEmploymentContract() => Ok();

    [HttpGet("employment/contracts/{id}")]
    public IActionResult GetEmploymentContract(Guid id) => Ok();

    // ── WC013-03a additions ──────────────────────────────────────────────────

    /// <summary>
    /// POST /api/customers
    /// Registers a new customer tenant.
    /// C-023: CE.ValidateAction is called and confirmed durable BEFORE the
    ///        registration record is committed (Evidence First).
    /// </summary>
    [HttpPost("/api/customers")]
    public async Task<IActionResult> RegisterCustomer(
        [FromBody] RegisterCustomerRequest request,
        CancellationToken cancellationToken)
    {
        if (request is null)
            return BadRequest("Request body is required.");

        if (string.IsNullOrWhiteSpace(request.DisplayName))
            return UnprocessableEntity("display_name is required.");

        if (string.IsNullOrWhiteSpace(request.Email))
            return UnprocessableEntity("email is required.");

        // ── 1. Pre-condition: CE.ValidateAction (C-023) ───────────────────
        //    CE call is NOT inside a DB transaction — it is the gate.
        var tenantId = ExtractTenantId();
        var actionParams = $"{{\"email\":\"{request.Email}\",\"display_name\":\"{request.DisplayName}\"}}";

        ValidateActionResponse? ceDecision;
        try
        {
            ceDecision = await CallCeValidateActionAsync(
                contractId: tenantId.ToString(),
                actionType: "CUSTOMER_REGISTRATION",
                actionParameters: actionParams,
                decisionSpaceVersion: 1,
                tenantId: tenantId.ToString(),
                cancellationToken: cancellationToken);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "CE.ValidateAction failed for CUSTOMER_REGISTRATION, tenant {TenantId}", tenantId);
            return StatusCode(503, "Constitutional Engine unavailable — registration denied.");
        }

        if (ceDecision is null)
            return StatusCode(503, "Constitutional Engine returned no decision — registration denied.");

        // ValidationDecision is from ValidateActionResponse; Allow = permitted
        if (ceDecision.Decision != ValidationDecision.Allow)
        {
            _logger.LogWarning(
                "CE denied CUSTOMER_REGISTRATION for tenant {TenantId}. Reason: {Reason}",
                tenantId, ceDecision.Reason);
            return StatusCode(403, new { ceDecision.Reason });
        }

        // ── 2. Commit registration (EmploymentService wired in WC013-03b) ──
        var customerId = Guid.NewGuid();
        var registeredAt = DateTimeOffset.UtcNow;

        _logger.LogInformation(
            "Customer registered: {CustomerId} tenant {TenantId} at {RegisteredAt}",
            customerId, tenantId, registeredAt);

        var response = new RegisterCustomerResponse(
            customerId,
            request.DisplayName,
            request.Email,
            registeredAt);

        return CreatedAtAction(nameof(RegisterCustomer), new { id = customerId }, response);
    }

    /// <summary>
    /// POST /api/agents/hire
    /// Creates an employment contract in EVALUATION state (C-034).
    /// C-023: CE.ValidateAction confirmed before any state is written.
    /// C-038: pro_rata_billing_start_date stamped at hire time.
    /// </summary>
    [HttpPost("/api/agents/hire")]
    public async Task<IActionResult> HireAgent(
        [FromBody] HireAgentRequest request,
        CancellationToken cancellationToken)
    {
        if (request is null)
            return BadRequest("Request body is required.");

        if (string.IsNullOrWhiteSpace(request.ProfessionalType))
            return UnprocessableEntity("professional_type is required.");

        if (string.IsNullOrWhiteSpace(request.ContractDisplayName))
            return UnprocessableEntity("contract_display_name is required.");

        if (request.ApprovedBudgetInrPaise <= 0)
            return UnprocessableEntity("approved_budget_inr_paise must be positive.");

        // ── 1. Pre-condition: CE.ValidateAction (C-023) ───────────────────
        //    CE call is NOT inside a DB transaction — it is the gate.
        var tenantId = ExtractTenantId();
        var actionParams =
            $"{{\"professional_type\":\"{request.ProfessionalType}\"," +
            $"\"contract_display_name\":\"{request.ContractDisplayName}\"," +
            $"\"approved_budget_inr_paise\":{request.ApprovedBudgetInrPaise}}}";

        ValidateActionResponse? ceDecision;
        try
        {
            ceDecision = await CallCeValidateActionAsync(
                contractId: tenantId.ToString(),
                actionType: "HIRE_AGENT",
                actionParameters: actionParams,
                decisionSpaceVersion: 1,
                tenantId: tenantId.ToString(),
                cancellationToken: cancellationToken);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "CE.ValidateAction failed for HIRE_AGENT, tenant {TenantId}", tenantId);
            return StatusCode(503, "Constitutional Engine unavailable — hire denied.");
        }

        if (ceDecision is null)
            return StatusCode(503, "Constitutional Engine returned no decision — hire denied.");

        // ValidationDecision is from ValidateActionResponse; Allow = permitted
        if (ceDecision.Decision != ValidationDecision.Allow)
        {
            _logger.LogWarning(
                "CE denied HIRE_AGENT for tenant {TenantId}, type {ProfessionalType}. Reason: {Reason}",
                tenantId, request.ProfessionalType, ceDecision.Reason);
            return StatusCode(403, new { ceDecision.Reason });
        }

        // ── 2. Create employment contract (C-034, C-038) ─────────────────
        //    pro_rata_billing_start_date is stamped NOW at hire time (C-038).
        var contractId = Guid.NewGuid();
        var now = DateTimeOffset.UtcNow;

        _logger.LogInformation(
            "Employment contract created: {ContractId} tenant {TenantId} type {ProfessionalType} at {CreatedAt}",
            contractId, tenantId, request.ProfessionalType, now);

        var contract = new EmploymentContractDto(
            contractId,
            tenantId,
            request.ProfessionalType,
            request.ContractDisplayName,
            "EVALUATION",                    // C-034: initial state
            request.ApprovedBudgetInrPaise,
            now,                             // C-038: pro_rata_billing_start_date at hire time
            request.BillingPreference,
            now);

        return CreatedAtAction(nameof(GetEmploymentContract), new { id = contractId }, contract);
    }

    // ── Private helpers ───────────────────────────────────────────────────────

    /// <summary>
    /// Extracts the tenant ID from the JWT claim or falls back to a
    /// deterministic placeholder when running outside an auth context
    /// (integration tests, local development).
    /// </summary>
    private Guid ExtractTenantId()
    {
        var tenantClaim = User.FindFirst("tenant_id")?.Value
                       ?? User.FindFirst("tid")?.Value;

        if (tenantClaim is not null && Guid.TryParse(tenantClaim, out var tenantGuid))
            return tenantGuid;

        // Fallback for unauthenticated local/test contexts — not production-safe.
        _logger.LogWarning("tenant_id claim not found in JWT; using empty GUID placeholder.");
        return Guid.Empty;
    }

    /// <summary>
    /// Calls CE.ValidateAction via gRPC.
    /// ADR-001: target latency &lt;40 ms on hot path; hard ceiling 5 s (CeCallTimeoutSeconds).
    /// C-023: must return PERMIT before any write is attempted.
    /// </summary>
    private async Task<ValidateActionResponse> CallCeValidateActionAsync(
        string contractId,
        string actionType,
        string actionParameters,
        int decisionSpaceVersion,
        string tenantId,
        CancellationToken cancellationToken)
    {
        var grpcUrl = _config["ConstitutionalEngine:GrpcUrl"]
                      ?? throw new InvalidOperationException("ConstitutionalEngine:GrpcUrl is not configured.");

        using var channel = GrpcChannel.ForAddress(grpcUrl);
        var client = new ConstitutionalService.ConstitutionalServiceClient(channel);

        using var cts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        cts.CancelAfter(TimeSpan.FromSeconds(CeCallTimeoutSeconds));

        var grpcRequest = new ValidateActionRequest
        {
            ContractId           = contractId,
            ActionType           = actionType,
            ActionParameters     = actionParameters,
            DecisionSpaceVersion = decisionSpaceVersion
        };

        var callOptions = new Grpc.Core.CallOptions(
            headers: new Grpc.Core.Metadata
            {
                { "x-tenant-id", tenantId }
            },
            cancellationToken: cts.Token);

        return await client.ValidateActionAsync(grpcRequest, callOptions);
    }
}