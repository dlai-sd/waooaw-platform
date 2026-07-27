// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041
// constitutional_basis: C-041 (Tool Authorization), C-059 (Traceability), C-073 (Annotated Obligations), C-076 (≥90% Unit Test Coverage)

// C-073: All using directives precede the namespace to avoid proto namespace collision.
using FluentAssertions;
using Microsoft.Extensions.Logging.Abstractions;
using System.Text.Json;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

/// <summary>
/// CCT-EF-01 gate: Constitutional Compliance Tests for C041ToolAuthorizationEvaluator.
/// Verifies default-deny, allow-listed tools, edge cases, and non-MCP passthrough.
/// C-076: ≥90% unit test coverage required.
/// </summary>
public sealed class CCT_EF01_C041ToolAuthorizationEvaluatorTests
{
    // ── Helpers ──────────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: Factory helper — builds an EvaluationContext via the canonical FromRequest path.
    /// ActionParameters is JSON-encoded; GetParameter(key) is the only correct access pattern.
    /// </summary>
    private static C041ToolAuthorizationEvaluator CreateEvaluator()
        => new C041ToolAuthorizationEvaluator(
            NullLogger<C041ToolAuthorizationEvaluator>.Instance);

    /// <summary>
    /// Builds a ValidateActionRequest for MCP_TOOL_CALL with arbitrary JSON action parameters.
    /// </summary>
    private static EvaluationContext BuildContext(
        string actionType,
        string actionParametersJson,
        string contractId = "contract-001",
        string tenantId   = "tenant-test")
    {
        var request = new ValidateActionRequest
        {
            ContractId           = contractId,
            ActionType           = actionType,
            ActionParameters     = actionParametersJson,
            DecisionSpaceVersion = 1,
        };
        return EvaluationContext.FromRequest(request, tenantId);
    }

    /// <summary>Serialises a parameters object to a JSON string for ActionParameters.</summary>
    private static string Params(object value)
        => JsonSerializer.Serialize(value);

    // ── ClaimId ───────────────────────────────────────────────────────────────

    [Fact]
    // C-073: Annotated — verifies constitutional claim identity binding for C-041.
    public void ClaimId_Always_ReturnsC041()
    {
        var evaluator = CreateEvaluator();
        evaluator.ClaimId.Should().Be("C-041");
    }

    // ── Default-deny (C-041 constitutional requirement) ───────────────────────

    [Fact]
    // C-073: C-041 default-deny — unlisted tool MUST produce Deny verdict.
    public async Task EvaluateAsync_UnlistedTool_ReturnsDeny()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            actionType: "MCP_TOOL_CALL",
            actionParametersJson: Params(new
            {
                tool_name        = "exec_shell",
                authorized_tools = new[] { "read_file", "write_file" }
            }));

        // C-073: Await Task<EvaluationResult> directly — never use .AsTask (does not exist on Task<T>).
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-041");
        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    // C-073: C-041 default-deny — empty authorized_tools list → every tool is denied.
    public async Task EvaluateAsync_EmptyAuthorizedTools_ReturnsDeny()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            actionType: "MCP_TOOL_CALL",
            actionParametersJson: Params(new
            {
                tool_name        = "read_file",
                authorized_tools = Array.Empty<string>()
            }));

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-041");
    }

    [Fact]
    // C-073: C-041 default-deny — missing tool_name parameter → Deny.
    public async Task EvaluateAsync_MissingToolName_ReturnsDeny()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            actionType: "MCP_TOOL_CALL",
            actionParametersJson: Params(new
            {
                authorized_tools = new[] { "read_file" }
                // tool_name intentionally omitted
            }));

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-041");
    }

    [Fact]
    // C-073: C-041 default-deny — missing authorized_tools parameter → Deny.
    public async Task EvaluateAsync_MissingAuthorizedTools_ReturnsDeny()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            actionType: "MCP_TOOL_CALL",
            actionParametersJson: Params(new
            {
                tool_name = "read_file"
                // authorized_tools intentionally omitted
            }));

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-041");
    }

    [Fact]
    // C-073: C-041 default-deny — empty JSON object (no parameters at all) → Deny.
    public async Task EvaluateAsync_EmptyActionParameters_ReturnsDeny()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            actionType: "MCP_TOOL_CALL",
            actionParametersJson: "{}");

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-041");
    }

    // ── Allow path ────────────────────────────────────────────────────────────

    [Fact]
    // C-073: C-041 allow — tool_name present in authorized_tools → Allow.
    public async Task EvaluateAsync_AuthorizedTool_ReturnsAllow()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            actionType: "MCP_TOOL_CALL",
            actionParametersJson: Params(new
            {
                tool_name        = "read_file",
                authorized_tools = new[] { "read_file", "write_file" }
            }));

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
        result.ClaimId.Should().Be("C-041");
    }

    [Fact]
    // C-073: C-041 allow — second item in multi-tool list is also authorized.
    public async Task EvaluateAsync_SecondAuthorizedTool_ReturnsAllow()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            actionType: "MCP_TOOL_CALL",
            actionParametersJson: Params(new
            {
                tool_name        = "write_file",
                authorized_tools = new[] { "read_file", "write_file", "list_directory" }
            }));

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
        result.ClaimId.Should().Be("C-041");
    }

    [Fact]
    // C-073: C-041 allow — single-element authorized_tools list containing the requested tool.
    public async Task EvaluateAsync_SingleElementListMatchingTool_ReturnsAllow()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            actionType: "MCP_TOOL_CALL",
            actionParametersJson: Params(new
            {
                tool_name        = "list_directory",
                authorized_tools = new[] { "list_directory" }
            }));

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
        result.ClaimId.Should().Be("C-041");
    }

    // ── Non-MCP passthrough ───────────────────────────────────────────────────

    [Fact]
    // C-073: C-041 scope — evaluator only governs MCP_TOOL_CALL; other action types pass through.
    public async Task EvaluateAsync_NonMcpActionType_ReturnsAllow()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            actionType: "HTTP_REQUEST",
            actionParametersJson: Params(new { url = "https://example.com" }));

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
        result.ClaimId.Should().Be("C-041");
    }

    [Fact]
    // C-073: C-041 scope — AGENT_QUERY is not a tool call; evaluator should pass through.
    public async Task EvaluateAsync_AgentQueryActionType_ReturnsAllow()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            actionType: "AGENT_QUERY",
            actionParametersJson: Params(new { query = "What is 2+2?" }));

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
        result.ClaimId.Should().Be("C-041");
    }

    [Fact]
    // C-073: C-041 scope — empty action type string is not MCP_TOOL_CALL; pass through.
    public async Task EvaluateAsync_EmptyActionType_ReturnsAllow()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            actionType: string.Empty,
            actionParametersJson: Params(new { tool_name = "exec_shell" }));

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
        result.ClaimId.Should().Be("C-041");
    }

    // ── Case-sensitivity / exact match ────────────────────────────────────────

    [Fact]
    // C-073: C-041 exact-match — tool names are case-sensitive; wrong case → Deny.
    public async Task EvaluateAsync_ToolNameWrongCase_ReturnsDeny()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            actionType: "MCP_TOOL_CALL",
            actionParametersJson: Params(new
            {
                tool_name        = "READ_FILE",       // uppercase
                authorized_tools = new[] { "read_file" } // lowercase in list
            }));

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // C-041: exact string match required; case mismatch = Deny (default deny)
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-041");
    }

    // ── Cancellation ──────────────────────────────────────────────────────────

    [Fact]
    // C-073: Async discipline — CancellationToken propagation must not cause unobserved exceptions
    //        when the token is not yet cancelled at call time.
    public async Task EvaluateAsync_WithCancellationToken_CompletesNormally()
    {
        var evaluator = CreateEvaluator();
        using var cts = new CancellationTokenSource();
        var ctx = BuildContext(
            actionType: "MCP_TOOL_CALL",
            actionParametersJson: Params(new
            {
                tool_name        = "read_file",
                authorized_tools = new[] { "read_file" }
            }));

        var result = await evaluator.EvaluateAsync(ctx, cts.Token);

        result.Should().NotBeNull();
        result.ClaimId.Should().Be("C-041");
    }

    // ── EvaluationResult shape ────────────────────────────────────────────────

    [Fact]
    // C-073: Result contract — every result must carry a non-empty Reason for auditability (C-059).
    public async Task EvaluateAsync_DenyResult_HasNonEmptyReason()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            actionType: "MCP_TOOL_CALL",
            actionParametersJson: Params(new
            {
                tool_name        = "dangerous_tool",
                authorized_tools = new[] { "safe_tool" }
            }));

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Reason.Should().NotBeNullOrWhiteSpace(
            because: "C-059 traceability requires a non-empty Reason on every evaluation result");
    }

    [Fact]
    // C-073: Result contract — Allow result must also carry Reason for full traceability (C-059).
    public async Task EvaluateAsync_AllowResult_HasNonEmptyReason()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            actionType: "MCP_TOOL_CALL",
            actionParametersJson: Params(new
            {
                tool_name        = "read_file",
                authorized_tools = new[] { "read_file" }
            }));

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
        result.Reason.Should().NotBeNullOrWhiteSpace(
            because: "C-059 traceability requires a non-empty Reason on every evaluation result");
    }

    // ── Parameterised: tool authorisation matrix ──────────────────────────────

    [Theory]
    [InlineData("read_file",      new[] { "read_file", "write_file" }, true)]
    [InlineData("write_file",     new[] { "read_file", "write_file" }, true)]
    [InlineData("exec_shell",     new[] { "read_file", "write_file" }, false)]
    [InlineData("list_directory", new[] { "read_file" },               false)]
    [InlineData("read_file",      new[] { "read_file" },               true)]
    // C-073: Parameterised matrix — verifies allow/deny for a range of tool/list combinations.
    public async Task EvaluateAsync_ToolMatrix_ReturnsExpectedVerdict(
        string   toolName,
        string[] authorizedTools,
        bool     expectAllow)
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            actionType: "MCP_TOOL_CALL",
            actionParametersJson: Params(new
            {
                tool_name        = toolName,
                authorized_tools = authorizedTools
            }));

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        var expectedVerdict = expectAllow ? EvaluationVerdict.Allow : EvaluationVerdict.Deny;
        result.Verdict.Should().Be(expectedVerdict,
            because: $"tool '{toolName}' {(expectAllow ? "is" : "is not")} in the authorized list");
        result.ClaimId.Should().Be("C-041");
    }

    // ── ContractId / TenantId threading ──────────────────────────────────────

    [Fact]
    // C-073: Context threading — evaluator must not corrupt contractId or tenantId on result.
    public async Task EvaluateAsync_ContextFields_AreNotCorrupted()
    {
        const string expectedContractId = "contract-xyz-9999";
        const string expectedTenantId   = "tenant-acme";

        var evaluator = CreateEvaluator();
        var request = new ValidateActionRequest
        {
            ContractId           = expectedContractId,
            ActionType           = "MCP_TOOL_CALL",
            ActionParameters     = Params(new
            {
                tool_name        = "read_file",
                authorized_tools = new[] { "read_file" }
            }),
            DecisionSpaceVersion = 2,
        };
        var ctx = EvaluationContext.FromRequest(request, expectedTenantId);

        ctx.ContractId.Should().Be(expectedContractId);
        ctx.TenantId.Should().Be(expectedTenantId);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);
        result.Should().NotBeNull();
    }
}