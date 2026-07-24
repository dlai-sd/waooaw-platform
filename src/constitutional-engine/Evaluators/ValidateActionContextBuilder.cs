// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-023 (Evidence First), C-041, C-043, C-048, C-062

using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Builds an EvaluationContext by pre-loading all DB data needed by claim evaluators.
/// All DB reads happen here — evaluators receive a fully-populated context and perform no I/O.
/// This is the single point of DB access for the ValidateAction pipeline.
/// </summary>
public sealed class ValidateActionContextBuilder
{
    private readonly ILogger<ValidateActionContextBuilder> _logger;

    // DESIGN_QUESTION: Should this take IConstitutionalDbContext (interface) for testability,
    // or use the concrete ConstitutionalDbContext? Using an interface is preferred for unit tests.
    // For now, using a data-provider interface to avoid direct EF dependency in this layer.
    private readonly IValidateActionDataProvider _dataProvider;

    public ValidateActionContextBuilder(
        IValidateActionDataProvider dataProvider,
        ILogger<ValidateActionContextBuilder> logger)
    {
        _dataProvider = dataProvider;
        _logger = logger;
    }

    /// <summary>
    /// C-073: Builds the EvaluationContext for a ValidateAction request.
    /// Performs all DB reads in parallel where possible to minimize latency within the 40ms budget.
    /// </summary>
    public async Task<EvaluationContext> BuildAsync(
        string tenantId,
        string agentId,
        string actionType,
        string? toolName,
        long? proposedSpendCents,
        string? actionPayload,
        CancellationToken ct)
    {
        _logger.LogDebug(
            "Building EvaluationContext for tenant {TenantId}, agent {AgentId}, action {ActionType}",
            tenantId, agentId, actionType);

        // Load contract data and security data in parallel
        var contractTask = _dataProvider.GetActiveContractDataAsync(tenantId, ct);
        var exploitationFlagTask = _dataProvider.GetExploitationFlagAsync(tenantId, ct);
        var prohibitedToolsTask = _dataProvider.GetProhibitedToolsAsync(tenantId, ct);
        var currentSpendTask = _dataProvider.GetCurrentPeriodSpendCentsAsync(tenantId, ct);

        await Task.WhenAll(contractTask, exploitationFlagTask, prohibitedToolsTask, currentSpendTask);

        var contractData = await contractTask;
        var hasExploitationFlag = await exploitationFlagTask;
        var prohibitedTools = await prohibitedToolsTask;
        var currentSpend = await currentSpendTask;

        return new EvaluationContext
        {
            TenantId = tenantId,
            AgentId = agentId,
            ActionType = actionType,
            ToolName = toolName,
            ProposedSpendCents = proposedSpendCents,
            ActionPayload = actionPayload,
            ContractAuthorizedActions = contractData?.AuthorizedActions,
            ContractBudgetCeilingCents = contractData?.BudgetCeilingCents,
            CurrentPeriodSpendCents = currentSpend,
            TenantHasExploitationFlag = hasExploitationFlag,
            ProhibitedTools = prohibitedTools,
            AgentInSandboxMode = false, // DESIGN_QUESTION: Where is sandbox mode stored? Agent profile?
            EvaluatedAt = DateTimeOffset.UtcNow
        };
    }
}

/// <summary>
/// Data transfer object for contract data loaded by the data provider.
/// </summary>
public sealed record ContractData(
    IReadOnlyList<string> AuthorizedActions,
    long? BudgetCeilingCents
);

/// <summary>
/// C-073: Abstraction over DB reads for ValidateAction context building.
/// Implemented by the EF Core data provider; mockable in unit tests.
/// </summary>
public interface IValidateActionDataProvider
{
    Task<ContractData?> GetActiveContractDataAsync(string tenantId, CancellationToken ct);
    Task<bool> GetExploitationFlagAsync(string tenantId, CancellationToken ct);
    Task<IReadOnlyList<string>> GetProhibitedToolsAsync(string tenantId, CancellationToken ct);
    Task<long> GetCurrentPeriodSpendCentsAsync(string tenantId, CancellationToken ct);
}