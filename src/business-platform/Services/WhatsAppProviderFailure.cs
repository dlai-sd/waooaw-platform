// Implements: architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md §10.2, §25.2 WC120-P2
// Constitutional basis: C-014, C-059

using System.Text.Json;

namespace Waooaw.BusinessPlatform.Services;

/// <summary>
/// Bounded classification of a Meta WhatsApp Cloud API failure. Only the HTTP status, the numeric
/// Meta error code and a fixed reason label are retained; message text can carry customer data.
/// </summary>
/// <param name="Reason">Fixed label that is safe to persist and log.</param>
/// <param name="Definitive">
/// True when the provider certainly did not accept the message, so retrying the same request cannot
/// create a duplicate. Throttling, authority and server failures are not definitive.
/// </param>
public sealed record WhatsAppProviderFailure(string Reason, bool Definitive)
{
    public static WhatsAppProviderFailure Classify(int? httpStatus, int? metaCode)
    {
        switch (metaCode)
        {
            case 4 or 80007 or 130429 or 131048 or 131056:
                return new("PROVIDER_RATE_LIMITED", false);
            case 0 or 10 or 190 or (>= 200 and <= 299):
                return new("PROVIDER_AUTHORITY_REJECTED", false);
            case 131000 or 131016 or 1 or 2:
                return new("PROVIDER_UNAVAILABLE", false);
            case 131047:
                return new("PROVIDER_REJECTED_OUTSIDE_WINDOW", true);
            case 131026:
                return new("PROVIDER_REJECTED_UNDELIVERABLE", true);
            case 131030:
                return new("PROVIDER_REJECTED_RECIPIENT_NOT_ALLOWED", true);
            case 131031 or 368:
                return new("PROVIDER_REJECTED_ACCOUNT_RESTRICTED", true);
            case 131042:
                return new("PROVIDER_REJECTED_PAYMENT_ISSUE", true);
            case 131051:
                return new("PROVIDER_REJECTED_UNSUPPORTED_TYPE", true);
            case >= 132000 and <= 132099:
                return new("PROVIDER_REJECTED_TEMPLATE", true);
            case 100 or 131008 or 131009 or 131021:
                return new("PROVIDER_REJECTED_INVALID_REQUEST", true);
        }
        return httpStatus switch
        {
            429 => new("PROVIDER_RATE_LIMITED", false),
            401 or 403 => new("PROVIDER_AUTHORITY_REJECTED", false),
            >= 500 => new("PROVIDER_UNAVAILABLE", false),
            >= 400 => new("PROVIDER_REJECTED", true),
            _ => new("PROVIDER_FAILURE_UNCLASSIFIED", false),
        };
    }

    /// <summary>Reads the numeric code from a Graph send error body or a webhook status errors array.</summary>
    public static int? ReadMetaCode(JsonElement root)
    {
        if (root.ValueKind != JsonValueKind.Object)
            return null;
        if (root.TryGetProperty("error", out var error))
            return ReadCode(error);
        if (
            root.TryGetProperty("errors", out var errors)
            && errors.ValueKind == JsonValueKind.Array
            && errors.GetArrayLength() > 0
        )
            return ReadCode(errors[0]);
        return null;
    }

    private static int? ReadCode(JsonElement element) =>
        element.ValueKind == JsonValueKind.Object
        && element.TryGetProperty("code", out var code)
        && code.ValueKind == JsonValueKind.Number
        && code.TryGetInt32(out var value)
            ? value
            : null;
}

public sealed class WhatsAppProviderHttpException(int httpStatus, int? metaCode)
    : Exception("PROVIDER_HTTP_FAILURE")
{
    public int HttpStatus { get; } = httpStatus;
    public int? MetaCode { get; } = metaCode;
}
