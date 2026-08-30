// Implements: WC-079 AA-02, AA-04, AA-06, AA-09
// constitutional_basis: C-001, C-003, C-023, C-036, C-037, C-038, C-041, C-049, C-059, C-063, C-070, C-079, C-088, C-094, C-099

using System.Security.Cryptography;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Globalization;

namespace Waooaw.BusinessPlatform.Services;

public sealed record AdmissionFinding(
    string RuleId,
    string Severity,
    string ContractPath,
    string ConstitutionalBasis,
    string Expected,
    string ObservedCategory,
    string Remediation,
    bool Blocking);

public static class AgentAdmissionCanonicalizer
{
    public static string Canonicalize(JsonElement element)
    {
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream, new JsonWriterOptions
        {
            Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
            Indented = false,
        }))
        {
            WriteElement(writer, element);
        }

        return Encoding.UTF8.GetString(stream.ToArray());
    }

    public static string Digest(JsonElement element) =>
        $"sha256:{Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(Canonicalize(element)))).ToLowerInvariant()}";

    public static string Digest(string value) =>
        $"sha256:{Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(value))).ToLowerInvariant()}";

    private static void WriteElement(Utf8JsonWriter writer, JsonElement element)
    {
        switch (element.ValueKind)
        {
            case JsonValueKind.Object:
                writer.WriteStartObject();
                foreach (var property in element.EnumerateObject().OrderBy(value => value.Name, StringComparer.Ordinal))
                {
                    writer.WritePropertyName(property.Name);
                    WriteElement(writer, property.Value);
                }
                writer.WriteEndObject();
                break;
            case JsonValueKind.Array:
                writer.WriteStartArray();
                foreach (var item in element.EnumerateArray()) WriteElement(writer, item);
                writer.WriteEndArray();
                break;
            case JsonValueKind.String:
                writer.WriteStringValue(element.GetString());
                break;
            case JsonValueKind.Number:
                WriteNumber(writer, element);
                break;
            case JsonValueKind.True:
                writer.WriteBooleanValue(true);
                break;
            case JsonValueKind.False:
                writer.WriteBooleanValue(false);
                break;
            case JsonValueKind.Null:
                writer.WriteNullValue();
                break;
            default:
                throw new JsonException("Unsupported JSON value in admission content.");
        }
    }

    private static void WriteNumber(Utf8JsonWriter writer, JsonElement element)
    {
        if (element.TryGetInt64(out var integer))
        {
            writer.WriteNumberValue(integer);
            return;
        }
        if (!element.TryGetDouble(out var number) || !double.IsFinite(number))
            throw new JsonException("Admission numbers must be finite IEEE-754 values.");
        writer.WriteRawValue(CanonicalizeNumber(number), skipInputValidation: true);
    }

    private static string CanonicalizeNumber(double number)
    {
        if (number == 0d) return "0";

        var shortest = number.ToString("R", CultureInfo.InvariantCulture);
        var negative = shortest[0] == '-';
        var unsigned = negative ? shortest[1..] : shortest;
        var exponentIndex = unsigned.IndexOfAny(['E', 'e']);
        var mantissa = exponentIndex < 0 ? unsigned : unsigned[..exponentIndex];
        var exponent = exponentIndex < 0
            ? 0
            : int.Parse(unsigned[(exponentIndex + 1)..], NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture);
        var decimalIndex = mantissa.IndexOf('.');
        var decimalPosition = (decimalIndex < 0 ? mantissa.Length : decimalIndex) + exponent;
        var digits = mantissa.Replace(".", string.Empty, StringComparison.Ordinal);
        var leadingZeroes = digits.TakeWhile(value => value == '0').Count();
        digits = digits[leadingZeroes..];
        decimalPosition -= leadingZeroes;
        digits = digits.TrimEnd('0');

        string canonical;
        if (decimalPosition > 0 && decimalPosition <= 21)
        {
            canonical = digits.Length <= decimalPosition
                ? digits + new string('0', decimalPosition - digits.Length)
                : digits.Insert(decimalPosition, ".");
        }
        else if (decimalPosition <= 0 && decimalPosition > -6)
        {
            canonical = "0." + new string('0', -decimalPosition) + digits;
        }
        else
        {
            var scientificExponent = decimalPosition - 1;
            canonical = digits.Length == 1 ? digits : $"{digits[0]}.{digits[1..]}";
            canonical += $"e{(scientificExponent >= 0 ? "+" : string.Empty)}{scientificExponent}";
        }

        return negative ? "-" + canonical : canonical;
    }
}

public sealed class AgentAdmissionValidator
{
    public const string Profile = "AAV-1.0.0";

    public IReadOnlyList<AdmissionFinding> Validate(
        JsonElement content,
        string expectedProfessionalType,
        string expectedProfessionalVersion,
        string suppliedDigest,
        bool includeReadiness = false)
    {
        var findings = new List<AdmissionFinding>();
        if (content.ValueKind != JsonValueKind.Object)
        {
            Add(findings, "AAV-001", "/", "C-088, C-094", "admission contract JSON object", "INVALID_CONTRACT_SHAPE");
            return findings;
        }

        var identity = Object(content, "professionalIdentity");
        var compliance = Object(content, "complianceDeclaration");
        var skills = Array(content, "skillManifest");

        Require(content, findings, "AAV-001", "C-088, C-094", "contractSchemaVersion", "canonicalizationProfile", "professionalIdentity", "complianceDeclaration", "skillManifest");
        ValidateKnownFields(content, identity, compliance, skills, findings);
        if (String(content, "contractSchemaVersion") != "1.0.0" || String(content, "canonicalizationProfile") != "RFC8785")
            Add(findings, "AAV-002", "/contractSchemaVersion", "C-059", "supported schema version 1.0.0", "UNSUPPORTED_VERSION");
        if (!string.Equals(AgentAdmissionCanonicalizer.Digest(content), suppliedDigest, StringComparison.Ordinal))
            Add(findings, "AAV-003", "/", "C-059, C-063", "RFC 8785 SHA-256 digest matching immutable content", "DIGEST_MISMATCH");
        if (identity is null
            || String(identity.Value, "professionalTypeId") != expectedProfessionalType
            || String(identity.Value, "professionalVersion") != expectedProfessionalVersion)
            Add(findings, "AAV-003", "/professionalIdentity", "C-059, C-063", "path-bound professional type and version", "IDENTITY_MISMATCH");

        if (identity is null || !HasObjects(identity.Value, "agentSpecification", "agentVerificationDocument")
            || compliance is null || !HasObjects(compliance.Value, "constitutionalDna", "agentBaseSpec"))
            Add(findings, "AAV-004", "/professionalIdentity", "C-070, C-094", "exact specification, AVD, DNA, and Base Spec references", "REFERENCE_INCOMPLETE");
        if (compliance is null || Object(compliance.Value, "platformAgentContract") is null)
            Add(findings, "AAV-005", "/complianceDeclaration/platformAgentContract", "C-041, C-094", "exact compatible PAC declaration", "PAC_INCOMPLETE");

        if (skills is null || skills.Value.GetArrayLength() == 0)
        {
            Add(findings, "AAV-006", "/skillManifest", "C-036, C-037", "one or more complete Skill Definitions", "SKILLS_MISSING");
        }
        else
        {
            foreach (var (skill, index) in skills.Value.EnumerateArray().Select((value, index) => (value, index)))
            {
                RequireSkill(skill, index, findings);
            }
        }

        if (compliance is null || !HasNonEmptyArray(compliance.Value, "evidenceFirstOperations")
            || Object(compliance.Value, "decisionConsequenceMap") is null
            || !HasNonEmptyArray(compliance.Value, "constitutionalConformanceTests"))
            Add(findings, "AAV-009", "/complianceDeclaration", "C-023, C-059, C-099", "DCM, Evidence First operations, CCTs, and artifact bindings", "CONFORMANCE_INCOMPLETE");
        if (compliance is null || Object(compliance.Value, "emergencyStop") is null
            || Object(compliance.Value, "retentionPolicy") is null
            || string.IsNullOrWhiteSpace(String(compliance.Value, "degradationBehavior")))
            Add(findings, "AAV-010", "/complianceDeclaration", "C-001, C-049, C-079", "consistent retention, degradation, and Emergency Stop policies", "POLICY_INCOMPLETE");
        if (includeReadiness)
            Add(findings, "AAV-012", "/activationEvidence", "C-063, C-079", "current platform-owned readiness assertions", "READINESS_REQUIRED");

        return findings;
    }

    private static void ValidateKnownFields(
        JsonElement content,
        JsonElement? identity,
        JsonElement? compliance,
        JsonElement? skills,
        ICollection<AdmissionFinding> findings)
    {
        Known(content, "/", findings, "contractSchemaVersion", "canonicalizationProfile", "professionalIdentity", "complianceDeclaration", "skillManifest");
        if (identity is { } professionalIdentity)
            Known(professionalIdentity, "/professionalIdentity", findings, "professionalTypeId", "professionalVersion", "ownerSubjectId", "supportedLanguages", "supportedChannels", "agentSpecification", "agentVerificationDocument", "predecessorVersion");
        if (compliance is { } declaration)
        {
            Known(declaration, "/complianceDeclaration", findings, "constitutionalDna", "agentBaseSpec", "platformAgentContract", "decisionSpaceSchema", "decisionConsequenceMap", "evidenceFirstOperations", "emergencyStop", "constitutionalConformanceTests", "dataClasses", "retentionPolicy", "securityPosture", "limitationBehavior", "degradationBehavior");
            KnownChild(declaration, "emergencyStop", "/complianceDeclaration/emergencyStop", findings, "supported", "signal", "maximumResponseSeconds");
            foreach (var name in new[] { "constitutionalDna", "agentBaseSpec", "decisionConsequenceMap" })
                KnownChild(declaration, name, $"/complianceDeclaration/{name}", findings, "path", "version", "digest");
            foreach (var name in new[] { "platformAgentContract", "decisionSpaceSchema", "retentionPolicy", "securityPosture" })
                KnownChild(declaration, name, $"/complianceDeclaration/{name}", findings, "schemaVersion", "schemaDigest");
        }
        if (identity is { } identityValue)
        {
            KnownChild(identityValue, "agentSpecification", "/professionalIdentity/agentSpecification", findings, "path", "version", "digest");
            KnownChild(identityValue, "agentVerificationDocument", "/professionalIdentity/agentVerificationDocument", findings, "path", "version", "digest");
        }
        if (skills is not { } manifest) return;
        foreach (var (skill, index) in manifest.EnumerateArray().Select((value, index) => (value, index)))
        {
            if (skill.ValueKind != JsonValueKind.Object)
            {
                Add(findings, "AAV-001", $"/skillManifest/{index}", "C-088, C-094", "skill definition object", "INVALID_FIELD_SHAPE");
                continue;
            }
            var path = $"/skillManifest/{index}";
            Known(skill, path, findings, "skillId", "skillVersion", "capability", "businessKpi", "inputs", "outputs", "decisionSpaceSubset", "tools", "constitutionalActions", "configurationSchema", "goalSchema", "schedulePolicy", "reviewPolicy", "costUnits", "trialBehavior", "degradationBehavior", "compatibility", "nonGoalExemption");
            foreach (var name in new[] { "configurationSchema", "goalSchema", "compatibility" })
                KnownChild(skill, name, $"{path}/{name}", findings, "schemaVersion", "schemaDigest");
            KnownChild(skill, "schedulePolicy", $"{path}/schedulePolicy", findings, "mode", "customerAdjustable", "minimumIntervalSeconds", "governedEvents");
            KnownChild(skill, "reviewPolicy", $"{path}/reviewPolicy", findings, "performanceReviewDays", "customerContractReviewDays");
            KnownChild(skill, "nonGoalExemption", $"{path}/nonGoalExemption", findings, "exemptionId", "purpose", "scope", "measurableOperationalOutcome", "approvingAuthority", "constitutionalAcceptanceReference", "effectiveFrom", "effectiveUntil", "revocationConditions");
            if (Array(skill, "tools") is { } tools)
                foreach (var (tool, toolIndex) in tools.EnumerateArray().Select((value, toolIndex) => (value, toolIndex)))
                    Known(tool, $"{path}/tools/{toolIndex}", findings, "toolId", "providerId", "defaultDenied", "governedAction");
        }
    }

    private static void KnownChild(
        JsonElement parent,
        string name,
        string path,
        ICollection<AdmissionFinding> findings,
        params string[] allowed)
    {
        if (Object(parent, name) is { } child) Known(child, path, findings, allowed);
    }

    private static void Known(
        JsonElement element,
        string path,
        ICollection<AdmissionFinding> findings,
        params string[] allowed)
    {
        if (element.ValueKind != JsonValueKind.Object)
        {
            Add(findings, "AAV-001", path, "C-088, C-094", "contract object", "INVALID_FIELD_SHAPE");
            return;
        }
        var names = allowed.ToHashSet(StringComparer.Ordinal);
        foreach (var property in element.EnumerateObject().Where(property => !names.Contains(property.Name)))
            Add(findings, "AAV-001", $"{path.TrimEnd('/')}/{property.Name}", "C-088, C-094", "field declared by contract schema", "UNKNOWN_FIELD");
    }

    private static void RequireSkill(JsonElement skill, int index, ICollection<AdmissionFinding> findings)
    {
        var path = $"/skillManifest/{index}";
        if (string.IsNullOrWhiteSpace(String(skill, "skillId"))
            || string.IsNullOrWhiteSpace(String(skill, "businessKpi"))
            || !HasNonEmptyArray(skill, "decisionSpaceSubset")
            || Object(skill, "configurationSchema") is null
            || Object(skill, "goalSchema") is null)
            Add(findings, "AAV-006", path, "C-036, C-037", "skill KPI, Decision Space, and admitted schemas", "SKILL_INCOMPLETE");

        var tools = Array(skill, "tools");
        if (tools is null || tools.Value.EnumerateArray().Any(tool =>
                !Boolean(tool, "defaultDenied")
                || string.IsNullOrWhiteSpace(String(tool, "governedAction"))))
            Add(findings, "AAV-007", $"{path}/tools", "C-003, C-041", "declared default-denied tools mapped to governed actions", "TOOL_AUTHORITY_INCOMPLETE");
        if (Object(skill, "costUnits") is null)
            Add(findings, "AAV-008", $"{path}/costUnits", "C-038, C-088", "digest-bound billing cost mapping", "COST_MAPPING_MISSING");
        if (Object(skill, "schedulePolicy") is null || Object(skill, "reviewPolicy") is null
            || string.IsNullOrWhiteSpace(String(skill, "trialBehavior"))
            || string.IsNullOrWhiteSpace(String(skill, "degradationBehavior")))
            Add(findings, "AAV-010", path, "C-001, C-049, C-079", "cadence, review, trial, and degradation policies", "SKILL_POLICY_INCOMPLETE");
    }

    private static void Require(
        JsonElement element,
        ICollection<AdmissionFinding> findings,
        string rule,
        string basis,
        params string[] names)
    {
        foreach (var name in names.Where(name => !element.TryGetProperty(name, out _)))
            Add(findings, rule, $"/{name}", basis, "required contract field", "FIELD_MISSING");
    }

    private static void Add(
        ICollection<AdmissionFinding> findings,
        string rule,
        string path,
        string basis,
        string expected,
        string observed) => findings.Add(new(
            rule,
            "ERROR",
            path,
            basis,
            expected,
            observed,
            "Submit a corrected immutable revision that satisfies this rule.",
            true));

    private static JsonElement? Object(JsonElement element, string name) =>
        element.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.Object ? value : null;

    private static JsonElement? Array(JsonElement element, string name) =>
        element.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.Array ? value : null;

    private static string? String(JsonElement element, string name) =>
        element.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString() : null;

    private static bool Boolean(JsonElement element, string name) =>
        element.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.True;

    private static bool HasObjects(JsonElement element, params string[] names) =>
        names.All(name => Object(element, name) is not null);

    private static bool HasNonEmptyArray(JsonElement element, string name) =>
        Array(element, name) is { } array && array.GetArrayLength() > 0;
}