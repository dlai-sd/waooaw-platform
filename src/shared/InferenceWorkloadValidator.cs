// Implements: WC-134 R006/R008; ADR-046 signed private inference boundaries.
using System.Collections.Concurrent;
using System.Formats.Asn1;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using Microsoft.AspNetCore.Server.Kestrel.Https;

namespace Waooaw.WorkloadIdentity;

public sealed class InferenceWorkloadRejectedException : Exception;

public sealed record InferenceWorkloadContext(Guid TenantId, Guid RelationshipId, Guid ActorId, string Role,
    Guid ContributionId, Guid ExecutionId, Guid IdempotencyKey, IReadOnlyDictionary<string, string> ExpectedVersions);

public sealed record PlatformWorkloadContext(string ActorSubject, string Role, string? TenantId = null,
    string? RelationshipId = null);

/// <summary>
/// Trust material for inbound workload calls when credentials are delivered through Key Vault rather than a directory:
/// the signed trust manifest plus peer and delegation-certificate checks against the CURRENT verified bundle.
/// </summary>
public sealed record InboundCredentialMaterial(string ManifestJson,
    Func<X509Certificate2, string, bool> ValidatePeer, Func<string, string, X509Certificate2?> DelegationCertificate);

public interface IInboundCredentialSource
{
    InboundCredentialMaterial? Current();
}

public sealed class InferenceWorkloadValidator(IConfiguration configuration, TimeProvider clock,
    IInboundCredentialSource? source = null)
{
    private readonly ConcurrentDictionary<string, long> _replays = new(StringComparer.Ordinal);

    public Task<InferenceWorkloadContext> RequireAsync(HttpContext http, string callerName, string targetName,
        string purpose, string route, string operation, string digest, CancellationToken ct) =>
        RequireCoreAsync(http, callerName, targetName, purpose, route, operation, digest, ct, ReadConversationContext,
            context =>
            {
                var roleAllowed = purpose == "CONVERSATION_CONTENT_RECOVERY"
                    ? context.Role is "OWNER" or "MANAGER"
                    : context.Role is "EMPLOYER" or "EVALUATOR" or "OUTCOME_OWNER" or "RELATIONSHIP_MANAGER";
                return roleAllowed
                    && context.TenantId != Guid.Empty && context.RelationshipId != Guid.Empty && context.ActorId != Guid.Empty
                    && context.ContributionId != Guid.Empty && context.ExecutionId != Guid.Empty && context.IdempotencyKey != Guid.Empty;
            });

    /// <summary>
    /// Platform-level calls (no tenant, relationship or conversation): the same mTLS, route grant, signature, digest,
    /// freshness and replay checks, but the signed context only has to name a non-empty actor subject and role.
    /// </summary>
    public Task<PlatformWorkloadContext> RequirePlatformAsync(HttpContext http, string callerName, string targetName,
        string purpose, string route, string operation, string digest, CancellationToken ct, string actorSource = "BP_SESSION") =>
        RequireCoreAsync(http, callerName, targetName, purpose, route, operation, digest, ct,
            value => new PlatformWorkloadContext(value.GetProperty("actor_subject").GetString() ?? string.Empty,
                value.GetProperty("effective_role").GetString() ?? string.Empty,
                value.TryGetProperty("tenant_id", out var tenant) ? tenant.GetString() : null,
                value.TryGetProperty("relationship_id", out var relationship) ? relationship.GetString() : null),
            context => context.ActorSubject.Length is > 0 and <= 128 && context.Role.Length is > 0 and <= 64, actorSource);

    private static InferenceWorkloadContext ReadConversationContext(JsonElement value) =>
        new(Guid.Parse(value.GetProperty("tenant_id").GetString()!),
            Guid.Parse(value.GetProperty("relationship_id").GetString()!), Guid.Parse(value.GetProperty("actor_subject").GetString()!),
            value.GetProperty("effective_role").GetString()!, Guid.Parse(value.GetProperty("subject_reference").GetString()!),
            Guid.Parse(value.GetProperty("command_id").GetString()!), Guid.Parse(value.GetProperty("idempotency_key").GetString()!),
            value.GetProperty("expected_versions").EnumerateObject().ToDictionary(property => property.Name, property => property.Value.GetString()!));

    private async Task<T> RequireCoreAsync<T>(HttpContext http, string callerName, string targetName,
        string purpose, string route, string operation, string digest, CancellationToken ct,
        Func<JsonElement, T> readContext, Func<T, bool> isAllowed, string actorSource = "BP_SESSION")
    {
        if (http.Request.Method != "POST" || http.Request.Path.Value != route)
            throw new InferenceWorkloadRejectedException();
        var credentials = configuration["WAOOAW_WORKLOAD_CREDENTIALS"];
        var inbound = credentials is null ? source?.Current() : null;
        if (credentials is null && inbound is null)
            throw new InferenceWorkloadRejectedException();
        using var manifest = JsonDocument.Parse(inbound?.ManifestJson
            ?? await File.ReadAllTextAsync(Path.Combine(credentials!, "manifest.json"), ct));
        var workloads = manifest.RootElement.GetProperty("workloads");
        var caller = workloads.GetProperty(callerName);
        var target = workloads.GetProperty(targetName);
        if (!HasRouteGrant(manifest.RootElement.GetProperty("route_grants"), callerName, targetName, route, operation))
            throw new InferenceWorkloadRejectedException();
        var certificate = await http.Connection.GetClientCertificateAsync(ct) ?? throw new InferenceWorkloadRejectedException();
        var callerUri = caller.GetProperty("identity_uri").GetString()!;
        if (!(inbound is null ? ValidatePeer(certificate, credentials!, callerUri) : inbound.ValidatePeer(certificate, callerUri)))
            throw new InferenceWorkloadRejectedException();
        var header = http.Request.Headers.Authorization.ToString();
        if (!header.StartsWith("Bearer ", StringComparison.Ordinal) || header.Length > 16000)
            throw new InferenceWorkloadRejectedException();
        var parts = header[7..].Split('.');
        if (parts.Length != 2)
            throw new InferenceWorkloadRejectedException();
        try
        {
            var payload = Decode(parts[0]);
            using var document = JsonDocument.Parse(payload);
            var value = document.RootElement;
            var now = clock.GetUtcNow().ToUnixTimeSeconds();
            var expires = value.GetProperty("expires_at").GetInt64();
            if (value.EnumerateObject().Select(property => property.Name).Distinct().Count() != value.EnumerateObject().Count()
                || value.GetProperty("issuer_uri").GetString() != callerUri
                || (inbound is null && value.GetProperty("key_id").GetString() != caller.GetProperty("delegation_key_id").GetString())
                || value.GetProperty("target_audience").GetString() != target.GetProperty("audience").GetString()
                || value.GetProperty("method").GetString() != "POST"
                || value.GetProperty("route").GetString() != route || value.GetProperty("operation").GetString() != operation
                || value.GetProperty("schema_version").GetString() != "1.0" || value.GetProperty("contract_major").GetInt32() != 1
                || value.GetProperty("purpose").GetString() != purpose || value.GetProperty("actor_source").GetString() != actorSource
                || value.GetProperty("request_digest").GetString() != digest
                || value.GetProperty("not_before").GetInt64() > now || expires <= now
                || value.GetProperty("issued_at").GetInt64() > now || expires - value.GetProperty("issued_at").GetInt64() > 60)
                throw new InferenceWorkloadRejectedException();
            using var signingCertificate = inbound is null
                ? X509CertificateLoader.LoadCertificateFromFile(Path.Combine(credentials!, "workloads", callerName, "delegation-cert.pem"))
                : inbound.DelegationCertificate(callerName, value.GetProperty("key_id").GetString()!) ?? throw new InferenceWorkloadRejectedException();
            using var key = signingCertificate.GetECDsaPublicKey() ?? throw new InferenceWorkloadRejectedException();
            if (!key.VerifyData(payload, Decode(parts[1]), HashAlgorithmName.SHA256, DSASignatureFormat.Rfc3279DerSequence))
                throw new InferenceWorkloadRejectedException();
            var context = readContext(value);
            if (!isAllowed(context))
                throw new InferenceWorkloadRejectedException();
            foreach (var replay in _replays.Where(pair => pair.Value <= now))
                _replays.TryRemove(replay.Key, out _);
            var nonce = Guid.Parse(value.GetProperty("envelope_id").GetString()!);
            if (nonce == Guid.Empty)
                throw new InferenceWorkloadRejectedException();
            var envelopeId = callerUri + ":" + nonce.ToString("D");
            if (_replays.Count >= 10000 || !_replays.TryAdd(envelopeId, expires))
                throw new InferenceWorkloadRejectedException();
            return context;
        }
        catch (Exception error) when (error is FormatException or JsonException or KeyNotFoundException or InvalidOperationException or ArgumentException)
        {
            throw new InferenceWorkloadRejectedException();
        }
    }

    public static bool ValidatePeer(X509Certificate2 certificate, string credentials, string expectedUri)
    {
        if (!HasExactUriSan(certificate, expectedUri))
            return false;
        using var root = X509CertificateLoader.LoadCertificateFromFile(Path.Combine(credentials, "trust", "root.pem"));
        using var chain = new X509Chain();
        chain.ChainPolicy.TrustMode = X509ChainTrustMode.CustomRootTrust;
        chain.ChainPolicy.CustomTrustStore.Add(root);
        chain.ChainPolicy.RevocationMode = X509RevocationMode.NoCheck;
        chain.ChainPolicy.ApplicationPolicy.Add(new Oid("1.3.6.1.5.5.7.3.2"));
        var bundle = new X509Certificate2Collection();
        bundle.ImportFromPem(File.ReadAllText(Path.Combine(credentials, "trust", "ca-bundle.pem")));
        chain.ChainPolicy.ExtraStore.AddRange(bundle);
        return chain.Build(certificate);
    }

    public static bool HasExactUriSan(X509Certificate2 certificate, string expectedUri)
    {
        var extension = certificate.Extensions["2.5.29.17"];
        if (extension is null)
            return false;
        var names = new AsnReader(extension.RawData, AsnEncodingRules.DER).ReadSequence();
        var uriTag = new Asn1Tag(TagClass.ContextSpecific, 6);
        while (names.HasData)
        {
            if (names.PeekTag().HasSameClassAndValue(uriTag))
            {
                if (names.ReadCharacterString(UniversalTagNumber.IA5String, uriTag) == expectedUri)
                    return true;
            }
            else
                names.ReadEncodedValue();
        }
        return false;
    }

    public static void ConfigureTransport(WebApplicationBuilder builder, string targetName, string callerName)
    {
        builder.WebHost.ConfigureKestrel(server =>
            server.Configure(builder.Configuration.GetSection("Kestrel")).Endpoint("ConversationInference", endpoint =>
            {
                var credentials = builder.Configuration["WAOOAW_WORKLOAD_CREDENTIALS"]
                    ?? throw new InvalidOperationException("Inference transport requires workload credentials.");
                if (!endpoint.IsHttps)
                    throw new InvalidOperationException("Inference listener requires HTTPS.");
                var workload = Path.Combine(credentials, "workloads", targetName);
                endpoint.HttpsOptions.ServerCertificate = X509Certificate2.CreateFromPemFile(
                    Path.Combine(workload, "tls-cert.pem"), Path.Combine(workload, "tls-key.pem"));
                endpoint.HttpsOptions.ClientCertificateMode = ClientCertificateMode.RequireCertificate;
                using var manifest = JsonDocument.Parse(File.ReadAllText(Path.Combine(credentials, "manifest.json")));
                var callerUri = manifest.RootElement.GetProperty("workloads").GetProperty(callerName).GetProperty("identity_uri").GetString()!;
                endpoint.HttpsOptions.ClientCertificateValidation = (certificate, _, _) => ValidatePeer(certificate, credentials, callerUri);
                endpoint.ListenOptions.Protocols = HttpProtocols.Http1AndHttp2;
            }));
    }

    /// <summary>
    /// A route grant in the trust bundle: the plain list of grant objects, or the grouped form the issuer publishes
    /// to keep the bundle inside one Key Vault secret (caller>target, POST and contract major 1 implied).
    /// </summary>
    private static bool HasRouteGrant(JsonElement grants, string caller, string target, string route, string operation)
    {
        if (grants.ValueKind == JsonValueKind.Array)
            return grants.EnumerateArray().Any(grant =>
                grant.GetProperty("caller").GetString() == caller && grant.GetProperty("target").GetString() == target
                && grant.GetProperty("method").GetString() == "POST" && grant.GetProperty("route").GetString() == route
                && grant.GetProperty("operation").GetString() == operation && grant.GetProperty("contract_major").GetInt32() == 1);
        if (grants.ValueKind != JsonValueKind.Object
            || !grants.TryGetProperty("format", out var format) || format.GetString() != "grouped-v1"
            || !grants.TryGetProperty("pairs", out var pairs) || !pairs.TryGetProperty($"{caller}>{target}", out var items)
            || items.ValueKind != JsonValueKind.Array)
            return false;
        return items.EnumerateArray().Any(item => GroupedGrantMatches(item, route, operation));
    }

    private static bool GroupedGrantMatches(JsonElement item, string route, string operation)
    {
        var length = item.GetArrayLength();
        if (length is not (2 or 4) || item[0].GetString() != route || item[1].GetString() != operation)
            return false;
        return length == 2 || (item[2].GetString() == "POST" && item[3].GetInt32() == 1);
    }

    private static byte[] Decode(string text)
    {
        var normalized = text.Replace('-', '+').Replace('_', '/');
        return Convert.FromBase64String(normalized.PadRight((normalized.Length + 3) / 4 * 4, '='));
    }
}
