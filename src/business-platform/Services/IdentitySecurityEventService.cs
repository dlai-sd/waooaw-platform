// Implements: architecture/reference/data/identity-security-data-contract.md §Logical Event Schema
// Implements: work-contracts/WC-105-auth-ui-runtime-defect-repair.md WC105-R014, WC105-R016
// Constitutional basis: C-002, C-005, C-007, C-027, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Npgsql;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record IdentitySecurityEventInput(
    Guid CorrelationId,
    string SourceEventId,
    string EventType,
    string ProviderClass,
    string Outcome,
    string ReasonCode,
    string AssuranceClass,
    string SourceBoundary,
    string? ActorIdentifier = null,
    string? SessionIdentifier = null,
    DateTimeOffset? OccurredAt = null
);

public sealed class IdentitySecurityEventService
{
    public static readonly IReadOnlySet<string> EventTypes = new HashSet<string>(
        [
            "AUTHENTICATION_START",
            "PROVIDER_HANDOFF",
            "CALLBACK_SUCCESS",
            "CALLBACK_FAILURE",
            "SESSION_ESTABLISHMENT",
            "REGISTRATION_START",
            "REGISTRATION_COMPLETION",
            "REGISTRATION_FAILURE",
            "REFRESH_SUCCESS",
            "REFRESH_FAILURE",
            "AUTHORIZATION_DENIAL",
            "LOGOUT_REQUEST",
            "LOGOUT_COMPLETION",
            "LOGOUT_FAILURE",
            "ACCOUNT_SWITCH",
            "SESSION_EXPIRY",
            "SESSION_REVOCATION_ONE",
            "SESSION_REVOCATION_ALL",
        ],
        StringComparer.Ordinal
    );

    private static readonly IReadOnlySet<string> ProviderClasses = new HashSet<string>(
        ["GOOGLE", "FACEBOOK", "APPLE", "EMAIL", "INTERNAL", "UNKNOWN"],
        StringComparer.Ordinal
    );
    private static readonly IReadOnlySet<string> Outcomes = new HashSet<string>(
        ["ATTEMPTED", "SUCCEEDED", "DENIED", "FAILED", "CANCELLED"],
        StringComparer.Ordinal
    );
    private static readonly IReadOnlySet<string> AssuranceClasses = new HashSet<string>(
        ["ANONYMOUS", "AAL1", "AAL2", "AAL3", "UNKNOWN"],
        StringComparer.Ordinal
    );
    private static readonly IReadOnlySet<string> SourceBoundaries = new HashSet<string>(
        ["WEB_APPLICATION", "BUSINESS_PLATFORM", "KEYCLOAK", "IDENTITY_EDGE"],
        StringComparer.Ordinal
    );
    private static readonly Regex SourceEventPattern = new(
        "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$",
        RegexOptions.CultureInvariant
    );
    private static readonly Regex ReasonCodePattern = new(
        "^[A-Z][A-Z0-9_]{1,63}$",
        RegexOptions.CultureInvariant
    );

    private readonly IDbContextFactory<IdentityDbContext> _dbFactory;
    private readonly byte[] _referenceKey;
    private readonly string _referenceKeyVersion;
    private readonly string _environment;

    public IdentitySecurityEventService(
        IDbContextFactory<IdentityDbContext> dbFactory,
        IOptions<IdentityHmacOptions> hmacOptions,
        IOptions<IdentityEnvironmentOptions> environmentOptions
    )
    {
        _dbFactory = dbFactory ?? throw new ArgumentNullException(nameof(dbFactory));
        var hmac = hmacOptions?.Value;
        var key = hmac?.Key;
        if (string.IsNullOrEmpty(key) || key.Length < IdentityHmacOptions.MinKeyLength)
            throw new InvalidOperationException(
                "Identity security events require valid HMAC material."
            );
        _referenceKey = Encoding.UTF8.GetBytes(key);
        _referenceKeyVersion = hmac!.ActiveVersion;
        _environment =
            environmentOptions?.Value.Environment?.Trim().ToLowerInvariant() ?? string.Empty;
        if (_environment is not ("local" or "demo" or "uat" or "prod"))
            throw new InvalidOperationException(
                "Identity security events require a known environment."
            );
    }

    public async Task<bool> RecordAsync(IdentitySecurityEventInput input, CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);
        return await RecordAsync(input, db, ct);
    }

    internal async Task<bool> RecordAsync(
        IdentitySecurityEventInput input,
        IdentityDbContext db,
        CancellationToken ct
    )
    {
        ArgumentNullException.ThrowIfNull(input);
        Validate(input);
        var occurredAt = input.OccurredAt ?? DateTimeOffset.UtcNow;
        if (occurredAt > DateTimeOffset.UtcNow.AddMinutes(5))
            throw new ArgumentException(
                "Identity security event time cannot be in the future.",
                nameof(input)
            );

        var securityEvent = new IdentitySecurityEventRecord
        {
            CorrelationId = input.CorrelationId,
            SourceEventId = input.SourceEventId,
            ActorRef = HashReference("actor", input.ActorIdentifier),
            SessionRef = HashReference("session", input.SessionIdentifier),
            Environment = _environment,
            EventType = input.EventType,
            ProviderClass = input.ProviderClass,
            Outcome = input.Outcome,
            ReasonCode = input.ReasonCode,
            AssuranceClass = input.AssuranceClass,
            SourceBoundary = input.SourceBoundary,
            ReferenceKeyVersion = _referenceKeyVersion,
            RetentionClass = "SECURITY_400D",
            RetainUntil = occurredAt.AddDays(400),
            OccurredAt = occurredAt,
            RecordedAt = DateTimeOffset.UtcNow,
            WriterService = "business-platform",
        };
        if (db.Database.IsRelational())
        {
            var inserted = await db.Database.ExecuteSqlInterpolatedAsync(
                $"""
                INSERT INTO institutional.identity_security_events
                    (event_id, correlation_id, source_event_id, actor_ref, session_ref,
                     environment, event_type, provider_class, outcome, reason_code,
                     assurance_class, source_boundary, reference_key_version, retention_class,
                     retain_until, schema_version, occurred_at, recorded_at, writer_service)
                VALUES
                    ({securityEvent.EventId}, {securityEvent.CorrelationId}, {securityEvent.SourceEventId},
                     {securityEvent.ActorRef}, {securityEvent.SessionRef}, {securityEvent.Environment},
                     {securityEvent.EventType}, {securityEvent.ProviderClass}, {securityEvent.Outcome},
                     {securityEvent.ReasonCode}, {securityEvent.AssuranceClass}, {securityEvent.SourceBoundary},
                     {securityEvent.ReferenceKeyVersion}, {securityEvent.RetentionClass},
                     {securityEvent.RetainUntil}, {securityEvent.SchemaVersion}, {securityEvent.OccurredAt},
                     {securityEvent.RecordedAt}, {securityEvent.WriterService})
                ON CONFLICT DO NOTHING
                """,
                ct
            );
            return inserted == 1;
        }

        db.SecurityEvents.Add(securityEvent);
        try
        {
            await db.SaveChangesAsync(ct);
            return true;
        }
        catch (DbUpdateException exception)
            when (IsUniqueViolation(exception))
        {
            return false;
        }
    }

    private static bool IsUniqueViolation(Exception exception)
    {
        for (var current = exception; current is not null; current = current.InnerException)
        {
            if (current is PostgresException { SqlState: PostgresErrorCodes.UniqueViolation })
                return true;
        }
        return false;
    }

    private static void Validate(IdentitySecurityEventInput input)
    {
        if (input.CorrelationId == Guid.Empty)
            throw new ArgumentException("A non-empty correlation ID is required.", nameof(input));
        if (!SourceEventPattern.IsMatch(input.SourceEventId))
            throw new ArgumentException("The source event ID is invalid.", nameof(input));
        if (!EventTypes.Contains(input.EventType))
            throw new ArgumentException(
                "The identity security event type is invalid.",
                nameof(input)
            );
        if (!ProviderClasses.Contains(input.ProviderClass))
            throw new ArgumentException("The provider class is invalid.", nameof(input));
        if (!Outcomes.Contains(input.Outcome))
            throw new ArgumentException("The event outcome is invalid.", nameof(input));
        if (!ReasonCodePattern.IsMatch(input.ReasonCode))
            throw new ArgumentException("The event reason code is invalid.", nameof(input));
        if (!AssuranceClasses.Contains(input.AssuranceClass))
            throw new ArgumentException("The assurance class is invalid.", nameof(input));
        if (!SourceBoundaries.Contains(input.SourceBoundary))
            throw new ArgumentException("The source boundary is invalid.", nameof(input));
    }

    private string? HashReference(string purpose, string? identifier)
    {
        if (string.IsNullOrWhiteSpace(identifier))
            return null;
        var bytes = HMACSHA256.HashData(
            _referenceKey,
            Encoding.UTF8.GetBytes($"wc103:{purpose}:{identifier}")
        );
        return Convert.ToHexString(bytes).ToLowerInvariant();
    }
}
