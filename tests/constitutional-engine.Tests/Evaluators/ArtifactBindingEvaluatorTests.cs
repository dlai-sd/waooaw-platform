// Implements: work-contracts/WC-170-real-agent-work-end-to-end.md WC170-R005, WC170-R006
// constitutional_basis: C-001, C-005, C-023, C-059, C-063, C-076

using System.Text.Json;
using Waooaw.ConstitutionalEngine.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

public sealed class ArtifactBindingEvaluatorTests
{
    private static readonly string Digest = new('a', 64);

    [Theory]
    [InlineData("EMPLOYMENT_ACCEPT_ARTIFACT_VERSION")]
    [InlineData("EMPLOYMENT_CONFIRM_SCOPE_BOUNDARY")]
    public async Task ADecisionNamingOneExactArtifactVersionIsAllowed(string action)
    {
        var result = await Evaluate(
            action,
            new { artifactId = Guid.NewGuid(), artifactDigest = Digest }
        );

        Assert.Equal(EvaluationVerdict.Allow, result.Verdict);
    }

    [Theory]
    [InlineData("{}")]
    [InlineData(
        "{\"artifactId\":\"00000000-0000-0000-0000-000000000000\",\"artifactDigest\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}"
    )]
    [InlineData(
        "{\"artifactId\":\"6f6b5f0e-1c1f-4d0f-9a0c-5c8b8d9b0a11\",\"artifactDigest\":\"not-a-digest\"}"
    )]
    [InlineData("[1]")]
    [InlineData("{")]
    public async Task ADecisionWithoutAnExactArtifactBindingIsDenied(string parameters)
    {
        var result = await new ArtifactBindingEvaluator().EvaluateAsync(
            Context("EMPLOYMENT_ACCEPT_ARTIFACT_VERSION", parameters)
        );

        Assert.Equal(EvaluationVerdict.Deny, result.Verdict);
    }

    [Fact]
    public async Task AStepRunsOnlyUnderALockedArtifactWithTwoSeparateEvidenceIds()
    {
        var step = new
        {
            artifactId = Guid.NewGuid(),
            artifactDigest = Digest,
            artifactStatus = "LOCKED",
            approvalEvidenceId = Guid.NewGuid(),
            scopeEvidenceId = Guid.NewGuid(),
        };

        Assert.Equal(
            EvaluationVerdict.Allow,
            (await Evaluate(ArtifactBindingEvaluator.ExecuteStep, step)).Verdict
        );
        Assert.Equal(
            EvaluationVerdict.Deny,
            (
                await Evaluate(
                    ArtifactBindingEvaluator.ExecuteStep,
                    step with
                    {
                        artifactStatus = "PROPOSED",
                    }
                )
            ).Verdict
        );
        Assert.Equal(
            EvaluationVerdict.Deny,
            (
                await Evaluate(
                    ArtifactBindingEvaluator.ExecuteStep,
                    step with
                    {
                        scopeEvidenceId = step.approvalEvidenceId,
                    }
                )
            ).Verdict
        );
        Assert.Equal(
            EvaluationVerdict.Deny,
            (
                await Evaluate(
                    ArtifactBindingEvaluator.ExecuteStep,
                    step with
                    {
                        approvalEvidenceId = Guid.Empty,
                    }
                )
            ).Verdict
        );
        Assert.Equal(
            EvaluationVerdict.Deny,
            (
                await Evaluate(
                    ArtifactBindingEvaluator.ExecuteStep,
                    step with
                    {
                        artifactDigest = "abc",
                    }
                )
            ).Verdict
        );
    }

    [Fact]
    public async Task OtherActionsStayOutsideTheEvaluatorScope()
    {
        var result = await Evaluate("RELATIONSHIP_UPDATE", new { anything = 1 });

        Assert.Equal(EvaluationVerdict.Allow, result.Verdict);
    }

    private static Task<EvaluationResult> Evaluate(string action, object parameters) =>
        new ArtifactBindingEvaluator().EvaluateAsync(
            Context(action, JsonSerializer.Serialize(parameters))
        );

    private static EvaluationContext Context(string action, string parameters) =>
        new(Guid.NewGuid().ToString("D"), action, parameters, 1, Guid.NewGuid().ToString("D"));
}
