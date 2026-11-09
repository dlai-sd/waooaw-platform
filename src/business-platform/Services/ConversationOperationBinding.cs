// Implements: architecture/reference/components/conversation-core.md §4.1 WC-134 Professional Generation Contract
// Constitutional basis: C-003, C-023, C-059, C-063
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace Waooaw.BusinessPlatform.Services;

public sealed record ConversationInferencePolicyReferenceV1(
    [property: JsonRequired] string Ref,
    [property: JsonRequired] string Version,
    [property: JsonRequired] string Digest
);

public sealed record ConversationOperationBindingV1(
    [property: JsonRequired] string Kind,
    [property: JsonRequired] string GovernedAction,
    [property: JsonRequired] string InputSchemaDigest,
    [property: JsonRequired] string OutputSchemaDigest,
    [property: JsonRequired] ConversationInferencePolicyReferenceV1 PromptPolicy,
    [property: JsonRequired] ConversationInferencePolicyReferenceV1 ModelPolicy,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? PatchType = null
)
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web)
    {
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        PropertyNameCaseInsensitive = false,
    };

    public static ConversationOperationBindingV1 Parse(JsonElement value)
    {
        if (value.ValueKind != JsonValueKind.Object)
            throw new JsonException("A conversation operation must be an object.");
        var binding =
            value.Deserialize<ConversationOperationBindingV1>(Json)
            ?? throw new JsonException("A conversation operation must be an object.");
        if (
            !binding.IsValid()
            || (binding.Kind == "PROFESSIONAL_RESPONSE" && value.TryGetProperty("patchType", out _))
        )
            throw new JsonException("The declared conversation operation is invalid.");
        return binding;
    }

    public bool Matches(
        IReadOnlyList<string> permittedActions,
        IReadOnlyList<string> exclusions,
        string inputDigest,
        string outputDigest,
        string promptVersion,
        string promptDigest
    ) =>
        IsValid()
        && permittedActions.Contains(GovernedAction, StringComparer.Ordinal)
        && !exclusions.Contains(GovernedAction, StringComparer.Ordinal)
        && InputSchemaDigest == inputDigest
        && OutputSchemaDigest == outputDigest
        && PromptPolicy.Version == promptVersion
        && PromptPolicy.Digest == promptDigest;

    public bool IsValid() =>
        Kind is "PROFESSIONAL_RESPONSE" or "EMPLOYMENT_CONTRIBUTION_INTERPRETATION"
        && Text(GovernedAction, 200)
        && Digest(InputSchemaDigest)
        && Digest(OutputSchemaDigest)
        && Policy(PromptPolicy)
        && Policy(ModelPolicy)
        && (
            Kind == "PROFESSIONAL_RESPONSE"
                ? PatchType is null
                : PatchType
                    is "INDUCTION_CONTEXT"
                        or "GOAL"
                        or "PLAN"
                        or "CALENDAR"
                        or "DEPENDENCY"
                        or "OPERATING_CYCLE"
                        or "CORRECTIVE_PROPOSAL"
        );

    private static bool Policy(ConversationInferencePolicyReferenceV1? value) =>
        value is not null
        && Text(value.Ref, 200)
        && Text(value.Version, 64)
        && Digest(value.Digest);

    private static bool Text(string? value, int maximum) =>
        !string.IsNullOrWhiteSpace(value) && value.Length <= maximum;

    private static bool Digest(string? value) =>
        value is not null
        && Regex.IsMatch(
            value,
            "^sha256:[0-9a-f]{64}$",
            RegexOptions.CultureInvariant,
            TimeSpan.FromMilliseconds(100)
        );
}
