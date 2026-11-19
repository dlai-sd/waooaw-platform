// Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R007, WC135-R016
// Constitutional basis: C-023, C-026, C-048, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services.Visitor;

public sealed record VisitorKey(string Version, byte[] Material);

/// <summary>Versioned key material for visitor personal-data envelopes.</summary>
public interface IVisitorKeyRing
{
    Task<VisitorKey> CurrentAsync(CancellationToken cancellationToken);

    /// <summary>Returns null when the version is unknown; never falls back to another version.</summary>
    Task<byte[]?> KeyForVersionAsync(string version, CancellationToken cancellationToken);
}

/// <summary>Local and test key ring. Demo and above use <see cref="VaultVisitorKeyRing"/>.</summary>
public sealed class ConfigurationVisitorKeyRing(IOptionsMonitor<VisitorConversationOptions> options)
    : IVisitorKeyRing
{
    public Task<VisitorKey> CurrentAsync(CancellationToken cancellationToken)
    {
        var current = options.CurrentValue;
        if (!current.LocalKeys.TryGetValue(current.LocalCurrentKeyVersion, out var material))
            throw new VisitorProtectionException("KEY_UNAVAILABLE");
        return Task.FromResult(
            new VisitorKey(current.LocalCurrentKeyVersion, Encoding.UTF8.GetBytes(material))
        );
    }

    public Task<byte[]?> KeyForVersionAsync(string version, CancellationToken cancellationToken) =>
        Task.FromResult(
            options.CurrentValue.LocalKeys.TryGetValue(version, out var material)
                ? Encoding.UTF8.GetBytes(material)
                : null
        );
}

/// <summary>Key ring backed by the pinned Key Vault phone-subject secret versions.</summary>
public sealed class VaultVisitorKeyRing(
    WhatsAppKeyVaultCredentials credentials,
    IOptionsMonitor<WhatsAppProviderOptions> provider
) : IVisitorKeyRing
{
    public async Task<VisitorKey> CurrentAsync(CancellationToken cancellationToken)
    {
        var version = provider.CurrentValue.PhoneSubjectKeyVersion;
        var material = await credentials.ReadPhoneSubjectKeyAsync(cancellationToken);
        return new VisitorKey(version, Encoding.UTF8.GetBytes(material));
    }

    public async Task<byte[]?> KeyForVersionAsync(
        string version,
        CancellationToken cancellationToken
    )
    {
        try
        {
            return Encoding.UTF8.GetBytes(
                await credentials.ReadPhoneSubjectKeyVersionAsync(version, cancellationToken)
            );
        }
        catch (WhatsAppCapabilityUnavailableException)
        {
            return null;
        }
    }
}

public sealed class VisitorProtectionException(string reason) : Exception(reason)
{
    public string Reason { get; } = reason;
}

/// <summary>
/// AES-GCM envelope <c>v2.{keyVersion}.{nonce}.{tag}.{ciphertext}</c> bound to tenant, field and row, so a
/// ciphertext cannot be moved to another row or field. The key version lets old ciphertext stay readable
/// after rotation until it is re-wrapped.
/// </summary>
public sealed partial class VisitorFieldProtector(IVisitorKeyRing keys)
{
    public const string EnvelopeVersion = "v2";
    private const string Purpose = "WAOOAW-WC135-VISITOR-FIELD-V2";

    public async Task<string> ProtectAsync(
        string plaintext,
        Guid tenantId,
        string field,
        Guid rowId,
        CancellationToken cancellationToken
    )
    {
        var key = await keys.CurrentAsync(cancellationToken);
        if (!KeyVersionPattern().IsMatch(key.Version))
            throw new VisitorProtectionException("KEY_VERSION_INVALID");
        var nonce = RandomNumberGenerator.GetBytes(12);
        var data = Encoding.UTF8.GetBytes(plaintext);
        var cipher = new byte[data.Length];
        var tag = new byte[16];
        var derived = Derive(key.Material);
        try
        {
            using var aes = new AesGcm(derived, tag.Length);
            aes.Encrypt(nonce, data, cipher, tag, Aad(tenantId, field, rowId));
        }
        finally
        {
            CryptographicOperations.ZeroMemory(derived);
            CryptographicOperations.ZeroMemory(data);
        }
        return $"{EnvelopeVersion}.{key.Version}.{Convert.ToBase64String(nonce)}.{Convert.ToBase64String(tag)}.{Convert.ToBase64String(cipher)}";
    }

    public async Task<string> UnprotectAsync(
        string envelope,
        Guid tenantId,
        string field,
        Guid rowId,
        CancellationToken cancellationToken
    )
    {
        var parts = envelope.Split('.');
        if (
            parts.Length != 5
            || parts[0] != EnvelopeVersion
            || !KeyVersionPattern().IsMatch(parts[1])
        )
            throw new VisitorProtectionException("ENVELOPE_INVALID");
        var material =
            await keys.KeyForVersionAsync(parts[1], cancellationToken)
            ?? throw new VisitorProtectionException("KEY_VERSION_UNAVAILABLE");
        var derived = Derive(material);
        try
        {
            var nonce = Convert.FromBase64String(parts[2]);
            var tag = Convert.FromBase64String(parts[3]);
            var cipher = Convert.FromBase64String(parts[4]);
            var plain = new byte[cipher.Length];
            using var aes = new AesGcm(derived, tag.Length);
            aes.Decrypt(nonce, cipher, tag, plain, Aad(tenantId, field, rowId));
            try
            {
                return Encoding.UTF8.GetString(plain);
            }
            finally
            {
                CryptographicOperations.ZeroMemory(plain);
            }
        }
        catch (Exception exception) when (exception is FormatException or CryptographicException)
        {
            throw new VisitorProtectionException("ENVELOPE_INVALID");
        }
        finally
        {
            CryptographicOperations.ZeroMemory(derived);
        }
    }

    /// <summary>True when the envelope was written under a key version other than the current one.</summary>
    public async Task<bool> NeedsRewrapAsync(string envelope, CancellationToken cancellationToken)
    {
        var parts = envelope.Split('.');
        if (parts.Length != 5 || parts[0] != EnvelopeVersion)
            return true;
        var current = await keys.CurrentAsync(cancellationToken);
        return !string.Equals(parts[1], current.Version, StringComparison.Ordinal);
    }

    public static string Mask(string? value) => string.IsNullOrEmpty(value) ? string.Empty : "***";

    private static byte[] Derive(byte[] material) =>
        HKDF.DeriveKey(
            HashAlgorithmName.SHA256,
            material,
            32,
            salt: null,
            info: Encoding.UTF8.GetBytes(Purpose)
        );

    private static byte[] Aad(Guid tenantId, string field, Guid rowId) =>
        Encoding.UTF8.GetBytes($"{tenantId:D}|{field}|{rowId:D}");

    [GeneratedRegex(@"^[A-Za-z0-9_-]{1,64}$", RegexOptions.CultureInvariant)]
    private static partial Regex KeyVersionPattern();
}
