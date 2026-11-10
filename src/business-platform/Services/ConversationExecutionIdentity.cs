// Implements: WC-134 R006; professional-runtime conversation execution identity
// Constitutional basis: C-023, C-059, C-063

using System.Security.Cryptography;
using System.Text;

namespace Waooaw.BusinessPlatform.Services;

public static class ConversationExecutionIdentity
{
    private static readonly Guid Namespace = new("f3e57984-3923-4f89-91bd-32453502471a");

    public static Guid Create(
        Guid tenantId,
        Guid relationshipId,
        Guid actorId,
        Guid conversationId,
        Guid idempotencyKey
    )
    {
        var identity = Encoding.UTF8.GetBytes(
            $"{tenantId:D}:{relationshipId:D}:{actorId:D}:{conversationId:D}:{idempotencyKey:D}"
        );
        var input = new byte[16 + identity.Length];
        Namespace.TryWriteBytes(input, bigEndian: true, out _);
        identity.CopyTo(input, 16);
        // RFC 9562 UUID-v5: SHA-1 names the execution; it is not an authority or secret.
        var hash = SHA1.HashData(input);
        hash[6] = (byte)((hash[6] & 0x0f) | 0x50);
        hash[8] = (byte)((hash[8] & 0x3f) | 0x80);
        return new Guid(hash.AsSpan(0, 16), bigEndian: true);
    }
}
