// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R003
// Constitutional basis: C-023, C-059, C-063, C-083, C-084

using System.Net;
using System.Net.Sockets;

namespace Waooaw.BusinessPlatform.Services;

public static class ProviderTestOutcomes
{
    public const string Passed = "PASSED";
    public const string Failed = "FAILED";
    public const string NotTestable = "NOT_TESTABLE";
}

public static class ProviderAuthSchemes
{
    public const string Bearer = "BEARER";
    public const string XApiKey = "X_API_KEY";
    public const string XGoogApiKey = "X_GOOG_API_KEY";
    public const string Header = "HEADER";
    public const string SubscriptionKey = "SUBSCRIPTION_KEY";
    public const string MetaApp = "META_APP";

    /// <summary>Schemes a Founder may choose when adding a provider. META_APP is reserved for the seeded Meta row.</summary>
    public static readonly IReadOnlyList<string> All =
    [
        Bearer,
        XApiKey,
        XGoogApiKey,
        Header,
        SubscriptionKey,
    ];
}

public static class ProviderTestMethods
{
    public const string Get = "GET";
    public const string PostEmptyJson = "POST_EMPTY_JSON";

    public static readonly IReadOnlyList<string> All = [Get, PostEmptyJson];
}

/// <summary>What the Test call needs from a provider row. Never carries the credential value.</summary>
public sealed record ProviderTestTarget(
    string ProviderName,
    string? TestUrl,
    string? AuthScheme,
    string? AuthHeader,
    string? TestMethod = null
);

/// <summary>Sanitized result. Detail is a short fixed reason such as "HTTP 401"; the provider's body is never kept.</summary>
public sealed record ProviderCredentialTestResult(string Outcome, string Detail, int? HttpStatus);

public interface IProviderCredentialTester
{
    Task<ProviderCredentialTestResult> TestAsync(
        ProviderTestTarget target,
        string value,
        CancellationToken ct
    );
}

/// <summary>
/// One read-only HTTPS GET to the provider's test endpoint. The endpoint must resolve only to public addresses; the
/// connection is pinned to the address that was checked, redirects are never followed, and the response body is never read.
/// </summary>
public sealed class ProviderCredentialTester : IProviderCredentialTester
{
    private static readonly TimeSpan ProbeTimeout = TimeSpan.FromSeconds(10);
    private readonly Func<string, CancellationToken, Task<IPAddress[]>> _resolve;
    private readonly Func<IPAddress, HttpMessageHandler> _handlerFor;

    public ProviderCredentialTester()
        : this((host, ct) => Dns.GetHostAddressesAsync(host, ct), pinned => PinnedHandler(pinned))
    { }

    internal ProviderCredentialTester(
        Func<string, CancellationToken, Task<IPAddress[]>> resolve,
        Func<IPAddress, HttpMessageHandler> handlerFor
    )
    {
        _resolve = resolve;
        _handlerFor = handlerFor;
    }

    public async Task<ProviderCredentialTestResult> TestAsync(
        ProviderTestTarget target,
        string value,
        CancellationToken ct
    )
    {
        if (string.IsNullOrWhiteSpace(target.TestUrl))
            return new(ProviderTestOutcomes.NotTestable, "No test endpoint is configured.", null);
        if (
            !Uri.TryCreate(target.TestUrl, UriKind.Absolute, out var uri)
            || uri.Scheme != Uri.UriSchemeHttps
            || uri.Port != 443
            || !string.IsNullOrEmpty(uri.UserInfo)
            || !string.IsNullOrEmpty(uri.Fragment)
        )
            return Failed("The test endpoint must be an https URL.");
        IPAddress[] addresses;
        try
        {
            addresses = await _resolve(uri.DnsSafeHost, ct);
        }
        catch (Exception exception) when (exception is SocketException or ArgumentException)
        {
            return Failed("The test endpoint host could not be resolved.");
        }
        if (addresses.Length == 0 || addresses.Any(address => !IsPublic(address)))
            return Failed("The test endpoint resolves to a blocked address.");

        var metaApp = target.AuthScheme == ProviderAuthSchemes.MetaApp;
        var postsEmptyJson = target.TestMethod == ProviderTestMethods.PostEmptyJson;
        if (metaApp)
        {
            var metaUri = MetaAppUri(uri, value);
            if (metaUri is null)
                return Failed("The Meta app credential must be JSON with appId and appSecret.");
            uri = metaUri;
        }

        using var request = new HttpRequestMessage(
            postsEmptyJson ? HttpMethod.Post : HttpMethod.Get,
            uri
        );
        if (postsEmptyJson)
            request.Content = new StringContent(
                "{}",
                System.Text.Encoding.UTF8,
                "application/json"
            );
        if (!metaApp && !TryApplyAuth(request, target, value))
            return Failed("The credential could not be sent as a request header.");
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
        timeout.CancelAfter(ProbeTimeout);
        try
        {
            using var client = new HttpClient(_handlerFor(addresses[0]), disposeHandler: true)
            {
                Timeout = Timeout.InfiniteTimeSpan,
            };
            using var response = await client.SendAsync(
                request,
                HttpCompletionOption.ResponseHeadersRead,
                timeout.Token
            );
            var status = (int)response.StatusCode;
            if (postsEmptyJson)
                return status switch
                {
                    400 or 422 => new(
                        ProviderTestOutcomes.Passed,
                        $"HTTP {status}: the key was accepted and the empty request was refused",
                        status
                    ),
                    401 or 403 => new(ProviderTestOutcomes.Failed, $"HTTP {status}", status),
                    _ => new(ProviderTestOutcomes.NotTestable, $"HTTP {status}", status),
                };
            return response.IsSuccessStatusCode
                ? new(ProviderTestOutcomes.Passed, $"HTTP {status}", status)
                : new(ProviderTestOutcomes.Failed, $"HTTP {status}", status);
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            return Failed("The provider did not answer within 10 seconds.");
        }
        catch (Exception exception) when (exception is HttpRequestException or IOException)
        {
            return Failed("The provider could not be reached.");
        }
    }

    private static ProviderCredentialTestResult Failed(string detail) =>
        new(ProviderTestOutcomes.Failed, detail, null);

    /// <summary>The app-token request for the Meta app. The query carries the secret, so it is never logged or returned.</summary>
    private static Uri? MetaAppUri(Uri endpoint, string value)
    {
        string? appId;
        string? appSecret;
        try
        {
            using var document = System.Text.Json.JsonDocument.Parse(value);
            if (document.RootElement.ValueKind != System.Text.Json.JsonValueKind.Object)
                return null;
            appId = document.RootElement.TryGetProperty("appId", out var id)
                ? id.GetString()
                : null;
            appSecret = document.RootElement.TryGetProperty("appSecret", out var secret)
                ? secret.GetString()
                : null;
        }
        catch (Exception exception)
            when (exception is System.Text.Json.JsonException or InvalidOperationException)
        {
            return null;
        }
        if (
            appId is null
            || appSecret is null
            || !System.Text.RegularExpressions.Regex.IsMatch(appId, "^[0-9]{5,32}$")
            || !System.Text.RegularExpressions.Regex.IsMatch(appSecret, "^[A-Za-z0-9]{8,128}$")
        )
            return null;
        return new UriBuilder(endpoint)
        {
            Query = $"client_id={appId}&client_secret={appSecret}&grant_type=client_credentials",
        }.Uri;
    }

    private static bool TryApplyAuth(
        HttpRequestMessage request,
        ProviderTestTarget target,
        string value
    )
    {
        var header = target.AuthScheme switch
        {
            ProviderAuthSchemes.XApiKey => "x-api-key",
            ProviderAuthSchemes.XGoogApiKey => "x-goog-api-key",
            ProviderAuthSchemes.SubscriptionKey => "api-subscription-key",
            ProviderAuthSchemes.Header => target.AuthHeader,
            _ => "Authorization",
        };
        if (string.IsNullOrWhiteSpace(header))
            return false;
        var headerValue = header == "Authorization" ? "Bearer " + value : value;
        if (headerValue.Any(char.IsControl))
            return false;
        if (!request.Headers.TryAddWithoutValidation(header, headerValue))
            return false;
        if (target.ProviderName == "anthropic")
            request.Headers.TryAddWithoutValidation("anthropic-version", "2023-06-01");
        return true;
    }

    internal static bool IsPublic(IPAddress address)
    {
        if (address.IsIPv4MappedToIPv6)
            address = address.MapToIPv4();
        if (IPAddress.IsLoopback(address))
            return false;
        var bytes = address.GetAddressBytes();
        if (address.AddressFamily == AddressFamily.InterNetwork)
            return !(
                bytes[0] == 0
                || bytes[0] == 10
                || (bytes[0] == 100 && bytes[1] is >= 64 and <= 127)
                || (bytes[0] == 169 && bytes[1] == 254)
                || (bytes[0] == 172 && bytes[1] is >= 16 and <= 31)
                || (bytes[0] == 192 && bytes[1] == 0 && bytes[2] == 0)
                || (bytes[0] == 192 && bytes[1] == 168)
                || (bytes[0] == 198 && bytes[1] is 18 or 19)
                || bytes[0] >= 224
            );
        if (address.AddressFamily != AddressFamily.InterNetworkV6)
            return false;
        return !(
            address.Equals(IPAddress.IPv6Any)
            || address.IsIPv6LinkLocal
            || address.IsIPv6SiteLocal
            || address.IsIPv6Multicast
            || address.IsIPv6UniqueLocal
            || address.IsIPv6Teredo
            // 64:ff9b::/96 (NAT64) and 2002::/16 (6to4) embed an IPv4 address that is not checked here.
            || (bytes[0] == 0x00 && bytes[1] == 0x64 && bytes[2] == 0xff && bytes[3] == 0x9b)
            || (bytes[0] == 0x20 && bytes[1] == 0x02)
        );
    }

    internal static HttpMessageHandler PinnedHandler(IPAddress pinned) =>
        new SocketsHttpHandler
        {
            AllowAutoRedirect = false,
            UseProxy = false,
            UseCookies = false,
            AutomaticDecompression = DecompressionMethods.None,
            ConnectTimeout = ProbeTimeout,
            ConnectCallback = async (context, token) =>
            {
                var socket = new Socket(SocketType.Stream, ProtocolType.Tcp) { NoDelay = true };
                try
                {
                    await socket.ConnectAsync(
                        new IPEndPoint(pinned, context.DnsEndPoint.Port),
                        token
                    );
                    return new NetworkStream(socket, ownsSocket: true);
                }
                catch
                {
                    socket.Dispose();
                    throw;
                }
            },
        };
}
