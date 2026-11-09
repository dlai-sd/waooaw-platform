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

public sealed class InferenceWorkloadValidator(IConfiguration configuration, TimeProvider clock)
{
    private readonly ConcurrentDictionary<string, long> _replays = new(StringComparer.Ordinal);

    public async Task<InferenceWorkloadContext> RequireAsync(HttpContext http, string callerName, string targetName,
        string purpose, string route, string operation, string digest, CancellationToken ct)
    {
        if (http.Request.Method != "POST" || http.Request.Path.Value != route)
            throw new InferenceWorkloadRejectedException();
        var credentials = configuration["WAOOAW_WORKLOAD_CREDENTIALS"] ?? throw new InferenceWorkloadRejectedException();
        using var manifest = JsonDocument.Parse(await File.ReadAllTextAsync(Path.Combine(credentials, "manifest.json"), ct));
        var workloads = manifest.RootElement.GetProperty("workloads");
        var caller = workloads.GetProperty(callerName);
        var target = workloads.GetProperty(targetName);
        if (!manifest.RootElement.GetProperty("route_grants").EnumerateArray().Any(grant =>
            grant.GetProperty("caller").GetString() == callerName && grant.GetProperty("target").GetString() == targetName
            && grant.GetProperty("method").GetString() == "POST" && grant.GetProperty("route").GetString() == route
            && grant.GetProperty("operation").GetString() == operation && grant.GetProperty("contract_major").GetInt32() == 1))
            throw new InferenceWorkloadRejectedException();
        var certificate = await http.Connection.GetClientCertificateAsync(ct) ?? throw new InferenceWorkloadRejectedException();
        var callerUri = caller.GetProperty("identity_uri").GetString()!;
        if (!ValidatePeer(certificate, credentials, callerUri))
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
                || value.GetProperty("key_id").GetString() != caller.GetProperty("delegation_key_id").GetString()
                || value.GetProperty("target_audience").GetString() != target.GetProperty("audience").GetString()
                || value.GetProperty("method").GetString() != "POST"
                || value.GetProperty("route").GetString() != route || value.GetProperty("operation").GetString() != operation
                || value.GetProperty("schema_version").GetString() != "1.0" || value.GetProperty("contract_major").GetInt32() != 1
                || value.GetProperty("purpose").GetString() != purpose || value.GetProperty("actor_source").GetString() != "BP_SESSION"
                || value.GetProperty("request_digest").GetString() != digest
                || value.GetProperty("not_before").GetInt64() > now || expires <= now
                || value.GetProperty("issued_at").GetInt64() > now || expires - value.GetProperty("issued_at").GetInt64() > 60)
                throw new InferenceWorkloadRejectedException();
            using var signingCertificate = X509CertificateLoader.LoadCertificateFromFile(
                Path.Combine(credentials, "workloads", callerName, "delegation-cert.pem"));
            using var key = signingCertificate.GetECDsaPublicKey() ?? throw new InferenceWorkloadRejectedException();
            if (!key.VerifyData(payload, Decode(parts[1]), HashAlgorithmName.SHA256, DSASignatureFormat.Rfc3279DerSequence))
                throw new InferenceWorkloadRejectedException();
            var context = new InferenceWorkloadContext(Guid.Parse(value.GetProperty("tenant_id").GetString()!),
                Guid.Parse(value.GetProperty("relationship_id").GetString()!), Guid.Parse(value.GetProperty("actor_subject").GetString()!),
                value.GetProperty("effective_role").GetString()!, Guid.Parse(value.GetProperty("subject_reference").GetString()!),
                Guid.Parse(value.GetProperty("command_id").GetString()!), Guid.Parse(value.GetProperty("idempotency_key").GetString()!),
                value.GetProperty("expected_versions").EnumerateObject().ToDictionary(property => property.Name, property => property.Value.GetString()!));
            var roleAllowed = purpose == "CONVERSATION_CONTENT_RECOVERY"
                ? context.Role is "OWNER" or "MANAGER"
                : context.Role is "EMPLOYER" or "EVALUATOR" or "OUTCOME_OWNER" or "RELATIONSHIP_MANAGER";
            if (!roleAllowed
                || context.TenantId == Guid.Empty || context.RelationshipId == Guid.Empty || context.ActorId == Guid.Empty
                || context.ContributionId == Guid.Empty || context.ExecutionId == Guid.Empty || context.IdempotencyKey == Guid.Empty)
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

    private static byte[] Decode(string text)
    {
        var normalized = text.Replace('-', '+').Replace('_', '/');
        return Convert.FromBase64String(normalized.PadRight((normalized.Length + 3) / 4 * 4, '='));
    }
}
