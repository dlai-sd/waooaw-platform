// Implements: WC-134 professional generation operation authority.
// constitutional_basis: C-023, C-059, C-063
using System.Text.Json;
using System.Text.Json.Nodes;
using FluentAssertions;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class ConversationOperationBindingTests
{
    private static readonly string InputDigest = "sha256:" + new string('1', 64);
    private static readonly string OutputDigest = "sha256:" + new string('2', 64);
    private static readonly string PromptDigest = "sha256:" + new string('3', 64);
    private static readonly string ModelDigest = "sha256:" + new string('4', 64);

    private static ConversationOperationBindingV1 Valid() =>
        new(
            "PROFESSIONAL_RESPONSE",
            "USE_TOOL",
            InputDigest,
            OutputDigest,
            new("prompt:one", "1.0", PromptDigest),
            new("model:one", "1.0", ModelDigest)
        );

    public static IEnumerable<object[]> InvalidBindings()
    {
        var binding = Valid();
        yield return [binding with { Kind = "OTHER" }];
        yield return [binding with { GovernedAction = "" }];
        yield return [binding with { GovernedAction = new string('a', 201) }];
        yield return [binding with { InputSchemaDigest = "sha256:" + new string('A', 64) }];
        yield return [binding with { OutputSchemaDigest = "sha256:short" }];
        yield return [binding with { PromptPolicy = null! }];
        yield return [binding with { ModelPolicy = null! }];
        yield return [binding with { PromptPolicy = binding.PromptPolicy with { Ref = " " } }];
        yield return
        [
            binding with
            {
                PromptPolicy = binding.PromptPolicy with { Ref = new string('a', 201) },
            },
        ];
        yield return [binding with { PromptPolicy = binding.PromptPolicy with { Version = "" } }];
        yield return
        [
            binding with
            {
                PromptPolicy = binding.PromptPolicy with { Version = new string('a', 65) },
            },
        ];
        yield return [binding with { PromptPolicy = binding.PromptPolicy with { Digest = "" } }];
        yield return [binding with { ModelPolicy = binding.ModelPolicy with { Digest = "" } }];
        yield return [binding with { PatchType = "GOAL" }];
        yield return [binding with { Kind = "EMPLOYMENT_CONTRIBUTION_INTERPRETATION" }];
        yield return
        [
            binding with
            {
                Kind = "EMPLOYMENT_CONTRIBUTION_INTERPRETATION",
                PatchType = "OTHER",
            },
        ];
    }

    [Theory]
    [MemberData(nameof(InvalidBindings))]
    public void InvalidBindingCannotBeUsed(ConversationOperationBindingV1 binding)
    {
        binding.IsValid().Should().BeFalse();
        binding
            .Matches(["USE_TOOL"], [], InputDigest, OutputDigest, "1.0", PromptDigest)
            .Should()
            .BeFalse();
    }

    [Theory]
    [InlineData("INDUCTION_CONTEXT")]
    [InlineData("GOAL")]
    [InlineData("PLAN")]
    [InlineData("CALENDAR")]
    [InlineData("DEPENDENCY")]
    [InlineData("OPERATING_CYCLE")]
    [InlineData("CORRECTIVE_PROPOSAL")]
    public void InterpretationAcceptsOnlyDeclaredPatchTypes(string patchType)
    {
        var binding = Valid() with
        {
            Kind = "EMPLOYMENT_CONTRIBUTION_INTERPRETATION",
            PatchType = patchType,
        };
        binding.IsValid().Should().BeTrue();
    }

    [Theory]
    [InlineData("permission")]
    [InlineData("exclusion")]
    [InlineData("input")]
    [InlineData("output")]
    [InlineData("version")]
    [InlineData("prompt")]
    public void MatchingRequiresEveryAuthorityCoordinate(string changed)
    {
        var binding = Valid();
        binding
            .Matches(
                changed == "permission" ? ["use_tool"] : ["USE_TOOL"],
                changed == "exclusion" ? ["USE_TOOL"] : [],
                changed == "input" ? OutputDigest : InputDigest,
                changed == "output" ? InputDigest : OutputDigest,
                changed == "version" ? "2.0" : "1.0",
                changed == "prompt" ? ModelDigest : PromptDigest
            )
            .Should()
            .BeFalse();
        binding
            .Matches(["USE_TOOL"], [], InputDigest, OutputDigest, "1.0", PromptDigest)
            .Should()
            .BeTrue();
    }

    [Theory]
    [InlineData("[]")]
    [InlineData("null")]
    [InlineData("\"response\"")]
    public void ParseRejectsNonObjects(string json)
    {
        using var document = JsonDocument.Parse(json);
        Action parse = () => ConversationOperationBindingV1.Parse(document.RootElement);
        parse.Should().Throw<JsonException>();
    }

    [Theory]
    [InlineData("unknown")]
    [InlineData("patchType")]
    [InlineData("Kind")]
    public void ParseRejectsOpenOrForbiddenFields(string field)
    {
        var json = JsonSerializer.SerializeToNode(
            Valid(),
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        )!;
        json[field] = field == "patchType" ? null : "value";
        using var document = JsonDocument.Parse(json.ToJsonString());
        Action parse = () => ConversationOperationBindingV1.Parse(document.RootElement);
        parse.Should().Throw<JsonException>();
    }

    [Fact]
    public void ParseAcceptsClosedValidBinding()
    {
        var json = JsonSerializer.Serialize(
            Valid(),
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        );
        using var document = JsonDocument.Parse(json);
        ConversationOperationBindingV1.Parse(document.RootElement).Should().Be(Valid());
    }
}
