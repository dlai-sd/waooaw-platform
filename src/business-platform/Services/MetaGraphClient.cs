// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R008, WC149-R009
// Constitutional basis: C-023, C-059, C-063, C-083, C-084

using System.Net.Http.Headers;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Waooaw.BusinessPlatform.Services;

public sealed partial class MetaConnectionOptions
{
    public const string SectionName = "ProviderConnections:Meta";
    public const string DefaultGraphVersion = "v21.0";
    public const string GraphHost = "graph.facebook.com";
    public const string DialogHost = "www.facebook.com";

    public static readonly IReadOnlyList<string> Scopes =
    [
        "pages_show_list",
        "pages_manage_posts",
        "pages_read_engagement",
    ];

    public string GraphVersion { get; init; } = DefaultGraphVersion;
    public string RedirectUri { get; init; } = string.Empty;

    [GeneratedRegex(@"^v[0-9]{1,2}\.[0-9]{1,2}$")]
    private static partial Regex VersionPattern();

    public static MetaConnectionOptions From(IConfiguration configuration)
    {
        var version = configuration[$"{SectionName}:GraphVersion"]?.Trim();
        return new()
        {
            GraphVersion =
                version is { Length: > 0 } && VersionPattern().IsMatch(version)
                    ? version
                    : DefaultGraphVersion,
            RedirectUri = configuration[$"{SectionName}:RedirectUri"]?.Trim() ?? string.Empty,
        };
    }

    public Uri? RedirectUriValue =>
        Uri.TryCreate(RedirectUri, UriKind.Absolute, out var uri)
        && string.IsNullOrEmpty(uri.UserInfo)
        && string.IsNullOrEmpty(uri.Fragment)
        && (uri.Scheme == Uri.UriSchemeHttps || (uri.Scheme == Uri.UriSchemeHttp && uri.IsLoopback))
            ? uri
            : null;

    public Uri AuthorizationUrl(string appId, string state)
    {
        var query = string.Join(
            "&",
            new Dictionary<string, string>
            {
                ["client_id"] = appId,
                ["redirect_uri"] = RedirectUri,
                ["state"] = state,
                ["response_type"] = "code",
                ["scope"] = string.Join(',', Scopes),
            }.Select(pair => $"{pair.Key}={Uri.EscapeDataString(pair.Value)}")
        );
        return new Uri($"https://{DialogHost}/{GraphVersion}/dialog/oauth?{query}");
    }
}

public sealed record MetaPage(string Id, string Name, string AccessToken)
{
    public override string ToString() => $"MetaPage {{ Id = {Id}, AccessToken = [redacted] }}";
}

public enum MetaGraphFailure
{
    /// <summary>Graph refused the token or the authorization (OAuthException / code 190).</summary>
    AuthRejected,

    /// <summary>Graph answered with another client error.</summary>
    Rejected,

    /// <summary>Graph could not be reached, timed out or failed on its side.</summary>
    Unavailable,
}

/// <summary>A Graph failure. The message is fixed text: Graph error bodies are never copied into it.</summary>
public sealed class MetaGraphException(MetaGraphFailure failure)
    : Exception($"Graph API call failed: {failure}")
{
    public MetaGraphFailure Failure { get; } = failure;
}

public interface IMetaGraphClient
{
    Task<string> ExchangeCodeAsync(
        string appId,
        string appSecret,
        string redirectUri,
        string code,
        CancellationToken ct
    );

    Task<string> ExtendUserTokenAsync(
        string appId,
        string appSecret,
        string userToken,
        CancellationToken ct
    );

    Task<IReadOnlyList<MetaPage>> ListPagesAsync(string userToken, CancellationToken ct);

    Task<string> PublishAsync(
        string pageId,
        string pageToken,
        string message,
        CancellationToken ct
    );
}

/// <summary>
/// Calls the Graph API over HTTPS on graph.facebook.com only. Secrets and tokens travel in POST bodies or the
/// Authorization header, never in a URL, and no response body is logged or copied into an exception.
/// </summary>
public sealed partial class MetaGraphClient(HttpClient http, MetaConnectionOptions options)
    : IMetaGraphClient
{
    private const int MaximumResponseBytes = 262_144;

    [GeneratedRegex("^[0-9]{1,40}$")]
    private static partial Regex IdPattern();

    public async Task<string> ExchangeCodeAsync(
        string appId,
        string appSecret,
        string redirectUri,
        string code,
        CancellationToken ct
    )
    {
        using var document = await SendAsync(
            HttpMethod.Post,
            "oauth/access_token",
            null,
            new Dictionary<string, string>
            {
                ["client_id"] = appId,
                ["client_secret"] = appSecret,
                ["redirect_uri"] = redirectUri,
                ["code"] = code,
            },
            ct
        );
        return Token(document);
    }

    public async Task<string> ExtendUserTokenAsync(
        string appId,
        string appSecret,
        string userToken,
        CancellationToken ct
    )
    {
        using var document = await SendAsync(
            HttpMethod.Post,
            "oauth/access_token",
            null,
            new Dictionary<string, string>
            {
                ["grant_type"] = "fb_exchange_token",
                ["client_id"] = appId,
                ["client_secret"] = appSecret,
                ["fb_exchange_token"] = userToken,
            },
            ct
        );
        return Token(document);
    }

    public async Task<IReadOnlyList<MetaPage>> ListPagesAsync(
        string userToken,
        CancellationToken ct
    )
    {
        using var document = await SendAsync(
            HttpMethod.Get,
            "me/accounts?fields=id,name,access_token&limit=25",
            userToken,
            null,
            ct
        );
        if (
            !document.RootElement.TryGetProperty("data", out var data)
            || data.ValueKind != JsonValueKind.Array
        )
            throw new MetaGraphException(MetaGraphFailure.Rejected);
        var pages = new List<MetaPage>();
        foreach (var entry in data.EnumerateArray())
        {
            var id = Text(entry, "id");
            var name = Text(entry, "name");
            var token = Text(entry, "access_token");
            if (
                id is not null
                && IdPattern().IsMatch(id)
                && name is { Length: > 0 }
                && token is { Length: > 0 }
            )
                pages.Add(new MetaPage(id, name.Length > 200 ? name[..200] : name, token));
        }
        return pages;
    }

    public async Task<string> PublishAsync(
        string pageId,
        string pageToken,
        string message,
        CancellationToken ct
    )
    {
        if (!IdPattern().IsMatch(pageId))
            throw new MetaGraphException(MetaGraphFailure.Rejected);
        using var document = await SendAsync(
            HttpMethod.Post,
            $"{pageId}/feed",
            pageToken,
            new Dictionary<string, string> { ["message"] = message },
            ct
        );
        return Text(document.RootElement, "id") is { Length: > 0 and <= 128 } id
            ? id
            : throw new MetaGraphException(MetaGraphFailure.Rejected);
    }

    private async Task<JsonDocument> SendAsync(
        HttpMethod method,
        string path,
        string? bearer,
        Dictionary<string, string>? form,
        CancellationToken ct
    )
    {
        var uri = new Uri(
            $"https://{MetaConnectionOptions.GraphHost}/{options.GraphVersion}/{path}"
        );
        if (uri.Scheme != Uri.UriSchemeHttps || uri.Host != MetaConnectionOptions.GraphHost)
            throw new MetaGraphException(MetaGraphFailure.Rejected);
        using var request = new HttpRequestMessage(method, uri);
        if (form is not null)
            request.Content = new FormUrlEncodedContent(form);
        if (bearer is not null)
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", bearer);
        try
        {
            using var response = await http.SendAsync(
                request,
                HttpCompletionOption.ResponseHeadersRead,
                ct
            );
            var body = await ReadAsync(response, ct);
            JsonDocument? document = null;
            try
            {
                document = JsonDocument.Parse(body);
            }
            catch (JsonException) { }
            if (response.IsSuccessStatusCode)
                return document is { RootElement.ValueKind: JsonValueKind.Object }
                    ? document
                    : throw new MetaGraphException(MetaGraphFailure.Rejected);
            using (document)
                throw new MetaGraphException(Classify((int)response.StatusCode, document));
        }
        catch (Exception exception)
            when (exception is HttpRequestException or TaskCanceledException or IOException)
        {
            throw new MetaGraphException(MetaGraphFailure.Unavailable);
        }
    }

    private static MetaGraphFailure Classify(int status, JsonDocument? document)
    {
        if (status >= 500)
            return MetaGraphFailure.Unavailable;
        if (
            document?.RootElement.ValueKind == JsonValueKind.Object
            && document.RootElement.TryGetProperty("error", out var error)
            && error.ValueKind == JsonValueKind.Object
        )
        {
            var isCode190 =
                error.TryGetProperty("code", out var code)
                && code.ValueKind == JsonValueKind.Number
                && code.TryGetInt32(out var number)
                && number == 190;
            if (isCode190 || Text(error, "type") == "OAuthException")
                return MetaGraphFailure.AuthRejected;
        }
        return status is 401 ? MetaGraphFailure.AuthRejected : MetaGraphFailure.Rejected;
    }

    private static async Task<byte[]> ReadAsync(HttpResponseMessage response, CancellationToken ct)
    {
        await using var stream = await response.Content.ReadAsStreamAsync(ct);
        using var buffer = new MemoryStream();
        var chunk = new byte[8192];
        int read;
        while ((read = await stream.ReadAsync(chunk, ct)) > 0)
        {
            buffer.Write(chunk, 0, read);
            if (buffer.Length > MaximumResponseBytes)
                throw new MetaGraphException(MetaGraphFailure.Rejected);
        }
        return buffer.ToArray();
    }

    private static string Token(JsonDocument document) =>
        Text(document.RootElement, "access_token") is { Length: > 0 } token
            ? token
            : throw new MetaGraphException(MetaGraphFailure.Rejected);

    private static string? Text(JsonElement element, string name) =>
        element.ValueKind == JsonValueKind.Object
        && element.TryGetProperty(name, out var value)
        && value.ValueKind == JsonValueKind.String
            ? value.GetString()
            : null;
}
