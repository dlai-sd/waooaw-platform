// Implements: architecture/reference/product/wc085-identity-provisioning-data-contract.md CURRENT Sections 4-6
// constitutional_basis: C-005, C-007, C-026, C-059

using System.Buffers.Binary;
using System.Data;
using System.Security.Cryptography;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;
using Npgsql;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

/// <summary>Server-only identity constructed by the adapter after independent bearer validation, never model binding.</summary>
public sealed record VerifiedCustomerActor
{
    internal VerifiedCustomerActor(string issuer, string subject) => (Issuer, Subject) = (issuer, subject);
    public string Issuer { get; }
    public string Subject { get; }
}

/// <summary>
/// Server-only result of eligible Google web/email validation and exact-subject stock Keycloak Admin reads.
/// Construction is restricted to the BP assembly. No browser proof or Boolean trust assertion is accepted.
/// </summary>
public sealed record VerifiedGoogleWorkspaceProof
{
    internal VerifiedGoogleWorkspaceProof(VerifiedCustomerActor actor, string providerIssuer, string brokerAlias,
        string providerSubject, DateTimeOffset verifiedAt, DateTimeOffset authTime, string trustConfigDigest, Guid correlationId)
    {
        Actor = actor;
        ProviderIssuer = providerIssuer;
        BrokerAlias = brokerAlias;
        ProviderSubject = providerSubject;
        VerifiedAt = verifiedAt;
        AuthTime = authTime;
        TrustConfigDigest = trustConfigDigest;
        CorrelationId = correlationId;
    }

    public VerifiedCustomerActor Actor { get; }
    public string ProviderIssuer { get; }
    public string BrokerAlias { get; }
    public string ProviderSubject { get; }
    public DateTimeOffset VerifiedAt { get; }
    public DateTimeOffset AuthTime { get; }
    public string TrustConfigDigest { get; }
    public Guid CorrelationId { get; }
}

public sealed record CustomerWorkspaceTrust(string ActorIssuer, string ProviderIssuer, string BrokerAlias, string TrustConfigDigest);
public sealed record CustomerWorkspaceMembership(Guid AccountId, Guid TenantId, Guid MembershipId, string[] Roles);
public sealed record CustomerWorkspaceCompletion(IdentityCompletionResult Result, int StatusCode, string ResponseBody);

public enum CustomerWorkspaceError
{
    InvalidInput,
    ProofRequired,
    FreshAuthenticationRequired,
    RegistrationNotFound,
    RegistrationIneligible,
    IdempotencyConflict,
    RecoveryRequired,
    MembershipRequired,
    InvariantViolation,
    DependencyUnavailable,
}

public sealed class CustomerWorkspaceException(CustomerWorkspaceError error, Exception? innerException = null)
    : Exception("Customer workspace operation denied.", innerException)
{
    public CustomerWorkspaceError Error { get; } = error;
    public int StatusCode => Error switch
    {
        CustomerWorkspaceError.InvalidInput => 400,
        CustomerWorkspaceError.FreshAuthenticationRequired or CustomerWorkspaceError.MembershipRequired => 403,
        CustomerWorkspaceError.RegistrationNotFound => 404,
        CustomerWorkspaceError.IdempotencyConflict or CustomerWorkspaceError.RecoveryRequired => 409,
        CustomerWorkspaceError.RegistrationIneligible => 422,
        _ => 503,
    };
}

public sealed class CustomerWorkspaceProvisioningService
{
    private const string OperationFamily = "CompleteRegistration";
    private const int MaximumAttempts = 3;
    private static readonly TimeSpan Freshness = TimeSpan.FromMinutes(5);
    private static readonly TimeSpan ClockSkew = TimeSpan.FromSeconds(30);
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);
    private static readonly JsonSerializerOptions LockJsonOptions = new() { Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping };
    private static readonly Regex HashPattern = new("\\A[0-9a-f]{64}\\z", RegexOptions.CultureInvariant);
    private static readonly Regex LanguagePattern = new("\\A[a-z]{2}(-[A-Z]{2})?\\z", RegexOptions.CultureInvariant);
    private readonly IDbContextFactory<IdentityDbContext> _factory;
    private readonly CustomerWorkspaceTrust _trust;
    private readonly TimeProvider _time;

    public CustomerWorkspaceProvisioningService(IDbContextFactory<IdentityDbContext> factory,
        CustomerWorkspaceTrust trust, TimeProvider? timeProvider = null)
    {
        _factory = factory ?? throw new ArgumentNullException(nameof(factory));
        _trust = trust ?? throw new ArgumentNullException(nameof(trust));
        _time = timeProvider ?? TimeProvider.System;
        if (!ValidKey(trust.ActorIssuer, 256) || !ValidKey(trust.ProviderIssuer, 256)
            || !ValidKey(trust.BrokerAlias, 40) || !HashPattern.IsMatch(trust.TrustConfigDigest))
            throw new ArgumentException("Explicit verified broker trust configuration is required.", nameof(trust));
    }

    public async Task<CustomerWorkspaceCompletion> CompleteAsync(VerifiedGoogleWorkspaceProof proof,
        Guid registrationId, Guid idempotencyKey, string canonicalHash, CancellationToken ct = default)
    {
        ValidateProof(proof);
        if (registrationId == Guid.Empty || idempotencyKey == Guid.Empty || canonicalHash is null || !HashPattern.IsMatch(canonicalHash))
            throw new CustomerWorkspaceException(CustomerWorkspaceError.InvalidInput);
        for (var attempt = 1; attempt <= MaximumAttempts; attempt++)
        {
            try
            {
                return await CompleteAttemptAsync(proof, registrationId, idempotencyKey, canonicalHash, ct);
            }
            catch (Exception exception) when (DatabaseError(exception) is { } databaseError)
            {
                var retryable = databaseError.SqlState is PostgresErrorCodes.SerializationFailure or PostgresErrorCodes.DeadlockDetected
                    || databaseError.SqlState == PostgresErrorCodes.UniqueViolation && databaseError.ConstraintName is
                        "actor_bindings_actor_unique" or "login_methods_provider_unique" or "idempotency_ledger_actor_key_op_unique";
                if (retryable && attempt < MaximumAttempts)
                {
                    ValidateProof(proof);
                    continue;
                }
                throw new CustomerWorkspaceException(
                    databaseError.SqlState == PostgresErrorCodes.UniqueViolation && databaseError.ConstraintName == "login_methods_provider_unique"
                        ? CustomerWorkspaceError.RecoveryRequired
                        : databaseError.SqlState is PostgresErrorCodes.CheckViolation or PostgresErrorCodes.ForeignKeyViolation
                            ? CustomerWorkspaceError.InvariantViolation : CustomerWorkspaceError.DependencyUnavailable, exception);
            }
            catch (NpgsqlException exception)
            {
                throw new CustomerWorkspaceException(CustomerWorkspaceError.DependencyUnavailable, exception);
            }
            catch (OperationCanceledException exception) when (!ct.IsCancellationRequested)
            {
                throw new CustomerWorkspaceException(CustomerWorkspaceError.DependencyUnavailable, exception);
            }
        }
        throw new CustomerWorkspaceException(CustomerWorkspaceError.DependencyUnavailable);
    }

    public async Task<CustomerWorkspaceMembership> ResolveAsync(VerifiedCustomerActor actor, CancellationToken ct = default)
    {
        ValidateActor(actor);
        try
        {
            await using var db = await _factory.CreateDbContextAsync(ct);
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
            timeout.CancelAfter(TimeSpan.FromSeconds(15));
            await using var transaction = await db.Database.BeginTransactionAsync(IsolationLevel.ReadCommitted, timeout.Token);
            await db.Database.ExecuteSqlRawAsync("SET TRANSACTION READ ONLY", timeout.Token);
            var membership = await ResolveInTransactionAsync(db, actor, timeout.Token);
            await transaction.CommitAsync(timeout.Token);
            return membership;
        }
        catch (NpgsqlException exception)
        {
            throw new CustomerWorkspaceException(CustomerWorkspaceError.DependencyUnavailable, exception);
        }
        catch (OperationCanceledException exception) when (!ct.IsCancellationRequested)
        {
            throw new CustomerWorkspaceException(CustomerWorkspaceError.DependencyUnavailable, exception);
        }
    }

    /// <summary>Re-resolves in the caller's existing transaction and sets both tenant GUCs; caller still authorizes the resource/action.</summary>
    public async Task<CustomerWorkspaceMembership> ResolveInTransactionAsync(IdentityDbContext db,
        VerifiedCustomerActor actor, CancellationToken ct = default)
    {
        ValidateActor(actor);
        if (db.Database.CurrentTransaction is null)
            throw new InvalidOperationException("Membership resolution requires an existing transaction.");
        try
        {
            await SetContextAsync(db, actor, ct);
            var membership = await ReadMembershipAsync(db, ct)
                ?? throw new CustomerWorkspaceException(CustomerWorkspaceError.MembershipRequired);
            await db.Database.ExecuteSqlInterpolatedAsync($"""
                SELECT pg_catalog.set_config('app.tenant_id', {membership.TenantId.ToString("D")}, true),
                       pg_catalog.set_config('app.current_tenant_id', {membership.TenantId.ToString("D")}, true)
                """, ct);
            return membership;
        }
        catch (NpgsqlException exception)
        {
            throw new CustomerWorkspaceException(CustomerWorkspaceError.DependencyUnavailable, exception);
        }
    }

    private async Task<CustomerWorkspaceCompletion> CompleteAttemptAsync(VerifiedGoogleWorkspaceProof proof,
        Guid registrationId, Guid idempotencyKey, string canonicalHash, CancellationToken ct)
    {
        ValidateProof(proof);
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
        timeout.CancelAfter(TimeSpan.FromSeconds(15));
        ct = timeout.Token;
        await using var db = await _factory.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(IsolationLevel.ReadCommitted, ct);
        await SetContextAsync(db, proof.Actor, ct);
        var locks = new[]
        {
            LockKey(["wc085-actor", proof.Actor.Issuer, proof.Actor.Subject]),
            LockKey(["wc085-provider", proof.ProviderIssuer, proof.BrokerAlias, proof.ProviderSubject]),
        };
        foreach (var lockKey in locks.Distinct().Order())
            await db.Database.ExecuteSqlInterpolatedAsync($"SELECT pg_catalog.pg_advisory_xact_lock({lockKey})", ct);

        var registration = (await db.Registrations.FromSqlInterpolated($"""
            SELECT * FROM identity.registrations WHERE registration_id = {registrationId}
                AND actor_issuer = {proof.Actor.Issuer} COLLATE "C" AND actor_subject = {proof.Actor.Subject} COLLATE "C" FOR UPDATE
            """).ToListAsync(ct)).SingleOrDefault()
            ?? throw new CustomerWorkspaceException(CustomerWorkspaceError.RegistrationNotFound);
        var keyText = idempotencyKey.ToString("D");
        var replay = await db.IdempotencyLedger.SingleOrDefaultAsync(entry => entry.ActorIssuer == proof.Actor.Issuer
            && entry.ActorSubject == proof.Actor.Subject && entry.OperationFamily == OperationFamily && entry.IdempotencyKey == keyText, ct);
        if (replay is not null && (replay.CanonicalHash != canonicalHash || replay.RegistrationId != registrationId))
            throw new CustomerWorkspaceException(CustomerWorkspaceError.IdempotencyConflict);
        ValidateRegistration(registration, proof.BrokerAlias);
        var binding = await db.ActorBindings.SingleOrDefaultAsync(actor => actor.ActorIssuer == proof.Actor.Issuer
            && actor.ActorSubject == proof.Actor.Subject, ct);
        IdentityRegistrationRecord root;
        if (binding is null)
        {
            if (registration.State == IdentityRegistrationState.Completed || replay is not null)
                throw new CustomerWorkspaceException(CustomerWorkspaceError.MembershipRequired);
            binding = await CreateCohortAsync(db, proof, registration, ct);
            root = registration;
        }
        else
        {
            var login = await db.LoginMethods.SingleOrDefaultAsync(record => record.LoginMethodId == binding.LoginMethodId, ct);
            if (binding.Status != "ACTIVE" || login is null || login.Status != "ACTIVE" || login.AccountId != binding.AccountId
                || login.ProviderIssuer != proof.ProviderIssuer || login.BrokerAlias != proof.BrokerAlias || login.ProviderSubject != proof.ProviderSubject)
                throw new CustomerWorkspaceException(CustomerWorkspaceError.RecoveryRequired);
            var live = await ReadMembershipAsync(db, ct)
                ?? throw new CustomerWorkspaceException(CustomerWorkspaceError.MembershipRequired);
            if (live.AccountId != binding.AccountId)
                throw new CustomerWorkspaceException(CustomerWorkspaceError.InvariantViolation);
            var account = await db.Accounts.SingleAsync(record => record.AccountId == binding.AccountId, ct);
            root = await db.Registrations.SingleAsync(record => record.RegistrationId == account.OriginRegistrationId, ct);
            ValidateCompletedRoot(root, binding);
        }

        if (registration.State != IdentityRegistrationState.Completed)
        {
            var previousState = registration.State.ToString();
            registration.State = IdentityRegistrationState.Completed;
            registration.AccountId = root.AccountId;
            registration.ActorBindingId = root.ActorBindingId;
            registration.OriginRegistrationId = root.OriginRegistrationId;
            registration.CompletionOutcome = root.CompletionOutcome;
            registration.CompletionProfileSnapshot = root.CompletionProfileSnapshot;
            registration.CompletionStatusCode = root.CompletionStatusCode;
            registration.CompletionResponseBody = root.CompletionResponseBody;
            registration.CompletedAt = _time.GetUtcNow();
            registration.UpdatedAt = registration.CompletedAt.Value;
            db.RegistrationEvents.Add(new IdentityRegistrationEventRecord
            {
                RegistrationId = registrationId, ActorIssuer = proof.Actor.Issuer, ActorSubject = proof.Actor.Subject,
                EventType = "RegistrationCompleted", FromState = previousState, ToState = "Completed", CorrelationId = proof.CorrelationId,
            });
        }
        ValidateCompletedRoot(root, binding);
        if (registration.AccountId != root.AccountId || registration.ActorBindingId != root.ActorBindingId
            || registration.OriginRegistrationId != root.RegistrationId || registration.CompletionResponseBody != root.CompletionResponseBody
            || registration.CompletionOutcome != root.CompletionOutcome || registration.CompletionProfileSnapshot != root.CompletionProfileSnapshot
            || registration.CompletionStatusCode != root.CompletionStatusCode)
            throw new CustomerWorkspaceException(CustomerWorkspaceError.InvariantViolation);
        if (replay is not null && (replay.StatusCode != root.CompletionStatusCode || replay.ResponseBody != root.CompletionResponseBody))
            throw new CustomerWorkspaceException(CustomerWorkspaceError.InvariantViolation);
        if (replay is null)
        {
            await db.Database.ExecuteSqlInterpolatedAsync($"""
                INSERT INTO identity.idempotency_ledger(entry_id, actor_issuer, actor_subject, registration_id,
                    idempotency_key, operation_family, canonical_hash, status_code, response_body)
                VALUES ({Guid.NewGuid()}, {proof.Actor.Issuer}, {proof.Actor.Subject}, {registrationId},
                    {keyText}, {OperationFamily}, {canonicalHash}, 200, {root.CompletionResponseBody})
                """, ct);
        }
        await db.SaveChangesAsync(ct);
        var membership = await ReadMembershipAsync(db, ct)
            ?? throw new CustomerWorkspaceException(CustomerWorkspaceError.MembershipRequired);
        if (membership.AccountId != root.AccountId)
            throw new CustomerWorkspaceException(CustomerWorkspaceError.InvariantViolation);
        var result = JsonSerializer.Deserialize<IdentityCompletionResult>(root.CompletionResponseBody!, JsonOptions);
        if (result is null || result.AccountReference != root.AccountId || result.Outcome != root.CompletionOutcome
            || result.AssuranceLevel != "AAL2_ACCOUNT" || result.DefaultTarget != "APPLICATION_HOME")
            throw new CustomerWorkspaceException(CustomerWorkspaceError.InvariantViolation);
        await db.Database.ExecuteSqlRawAsync("SET CONSTRAINTS ALL IMMEDIATE", ct);
        ValidateProof(proof);
        await transaction.CommitAsync(ct);
        return new CustomerWorkspaceCompletion(result, 200, root.CompletionResponseBody!);
    }

    private async Task<IdentityActorBindingRecord> CreateCohortAsync(IdentityDbContext db, VerifiedGoogleWorkspaceProof proof,
        IdentityRegistrationRecord registration, CancellationToken ct)
    {
        var accountId = Guid.NewGuid();
        var tenantId = Guid.NewGuid();
        while (tenantId == accountId) tenantId = Guid.NewGuid();
        var binding = new IdentityActorBindingRecord
        {
            ActorBindingId = Guid.NewGuid(), ActorIssuer = proof.Actor.Issuer, ActorSubject = proof.Actor.Subject,
            LoginMethodId = Guid.NewGuid(), AccountId = accountId, VerifiedAt = proof.VerifiedAt,
            AuthTime = proof.AuthTime, TrustConfigDigest = proof.TrustConfigDigest, CorrelationId = proof.CorrelationId,
        };
        db.ActorBindings.Add(binding);
        await db.SaveChangesAsync(ct);
        db.LoginMethods.Add(new IdentityLoginMethodRecord
        {
            LoginMethodId = binding.LoginMethodId, AccountId = accountId, ProviderIssuer = proof.ProviderIssuer,
            BrokerAlias = proof.BrokerAlias, ProviderSubject = proof.ProviderSubject,
        });
        await db.SaveChangesAsync(ct);
        db.Accounts.Add(new IdentityAccountRecord
        {
            AccountId = accountId, InitialTenantId = tenantId, OriginRegistrationId = registration.RegistrationId,
        });
        await db.SaveChangesAsync(ct);
        var acceptedDomain = await db.Database.SqlQuery<string>($"""
            SELECT domain_code AS "Value" FROM business.business_domain_taxonomy
            WHERE domain_code COLLATE "C" = {registration.BusinessDomain} COLLATE "C" AND is_active
            """).SingleOrDefaultAsync(ct);
        db.Organisations.Add(new IdentityOrganisationRecord
        {
            Id = tenantId, TenantId = tenantId, Name = registration.BusinessName!, IdentityManaged = true,
            BusinessDomain = acceptedDomain,
        });
        await db.SaveChangesAsync(ct);
        db.Memberships.Add(new IdentityMembershipRecord { MembershipId = Guid.NewGuid(), AccountId = accountId, TenantId = tenantId });
        await db.SaveChangesAsync(ct);
        registration.AccountId = accountId;
        registration.ActorBindingId = binding.ActorBindingId;
        registration.OriginRegistrationId = registration.RegistrationId;
        registration.CompletionOutcome = "ACCOUNT_CREATED";
        registration.CompletionStatusCode = 200;
        registration.CompletionResponseBody = JsonSerializer.Serialize(
            new IdentityCompletionResult("ACCOUNT_CREATED", accountId, "AAL2_ACCOUNT", "APPLICATION_HOME"), JsonOptions);
        registration.CompletionProfileSnapshot = JsonSerializer.Serialize(new
        {
            registration.DisplayName, registration.BusinessName, registration.BusinessDomain, registration.LanguagePreference,
            emailVerified = true, registration.MobileVerified,
        }, JsonOptions);
        return binding;
    }

    private static async Task SetContextAsync(IdentityDbContext db, VerifiedCustomerActor actor, CancellationToken ct)
    {
        if (db.Database.GetDbConnection() is not NpgsqlConnection connection
            || new NpgsqlConnectionStringBuilder(connection.ConnectionString).NoResetOnClose)
            throw new InvalidOperationException("A reset-enabled PostgreSQL connection is required.");
        await db.Database.ExecuteSqlInterpolatedAsync($"""
            SELECT pg_catalog.set_config('app.identity_issuer', {actor.Issuer}, true),
                   pg_catalog.set_config('app.identity_subject', {actor.Subject}, true),
                   pg_catalog.set_config('app.tenant_id', '', true),
                   pg_catalog.set_config('app.current_tenant_id', '', true),
                   pg_catalog.set_config('lock_timeout', '3s', true),
                   pg_catalog.set_config('statement_timeout', '10s', true),
                   pg_catalog.set_config('idle_in_transaction_session_timeout', '15s', true)
            """, ct);
    }

    private static async Task<CustomerWorkspaceMembership?> ReadMembershipAsync(IdentityDbContext db, CancellationToken ct)
    {
        await using var command = db.Database.GetDbConnection().CreateCommand();
        command.Transaction = db.Database.CurrentTransaction!.GetDbTransaction();
        command.CommandText = "SELECT account_id, tenant_id, membership_id, roles FROM identity.resolve_customer_membership()";
        await using var reader = await command.ExecuteReaderAsync(ct);
        if (!await reader.ReadAsync(ct)) return null;
        var result = new CustomerWorkspaceMembership(reader.GetGuid(0), reader.GetGuid(1), reader.GetGuid(2), reader.GetFieldValue<string[]>(3));
        if (await reader.ReadAsync(ct) || result.AccountId == result.TenantId || !result.Roles.SequenceEqual(["OWNER"]))
            throw new CustomerWorkspaceException(CustomerWorkspaceError.InvariantViolation);
        return result;
    }

    private void ValidateActor(VerifiedCustomerActor actor)
    {
        if (actor is null || actor.Issuer != _trust.ActorIssuer || !ValidKey(actor.Issuer, 256) || !ValidKey(actor.Subject, 256))
            throw new CustomerWorkspaceException(CustomerWorkspaceError.ProofRequired);
    }

    private void ValidateProof(VerifiedGoogleWorkspaceProof proof)
    {
        if (proof is null) throw new CustomerWorkspaceException(CustomerWorkspaceError.ProofRequired);
        ValidateActor(proof.Actor);
        if (proof.ProviderIssuer != _trust.ProviderIssuer || proof.BrokerAlias != _trust.BrokerAlias
            || proof.TrustConfigDigest != _trust.TrustConfigDigest || !ValidKey(proof.ProviderSubject, 256) || proof.CorrelationId == Guid.Empty)
            throw new CustomerWorkspaceException(CustomerWorkspaceError.ProofRequired);
        var now = _time.GetUtcNow();
        if (proof.AuthTime < now - Freshness || proof.VerifiedAt < now - Freshness
            || proof.AuthTime > now + ClockSkew || proof.VerifiedAt > now + ClockSkew || proof.AuthTime > proof.VerifiedAt + ClockSkew)
            throw new CustomerWorkspaceException(CustomerWorkspaceError.FreshAuthenticationRequired);
    }

    private void ValidateRegistration(IdentityRegistrationRecord registration, string brokerAlias)
    {
        var expectedPath = brokerAlias switch
        {
            "google" => IdentityAuthenticationPath.Google,
            "facebook" => IdentityAuthenticationPath.Meta,
            _ => throw new CustomerWorkspaceException(CustomerWorkspaceError.ProofRequired),
        };
        if (registration.AuthenticationPath != expectedPath || !registration.EmailVerified
            || !ValidProfile(registration.DisplayName, 120) || !ValidProfile(registration.BusinessName, 160)
            || !ValidProfile(registration.BusinessDomain, 100) || registration.LanguagePreference is null
            || !LanguagePattern.IsMatch(registration.LanguagePreference)
            || registration.State != IdentityRegistrationState.Completed
                && (registration.State != IdentityRegistrationState.ReadyToComplete || registration.ExpiresAt <= _time.GetUtcNow()))
            throw new CustomerWorkspaceException(CustomerWorkspaceError.RegistrationIneligible);
    }

    private static void ValidateCompletedRoot(IdentityRegistrationRecord root, IdentityActorBindingRecord binding)
    {
        if (root.State != IdentityRegistrationState.Completed || root.AccountId != binding.AccountId
            || root.ActorBindingId != binding.ActorBindingId || root.ActorIssuer != binding.ActorIssuer || root.ActorSubject != binding.ActorSubject
            || root.OriginRegistrationId != root.RegistrationId || root.CompletedAt is null || root.CompletionStatusCode != 200
            || root.CompletionOutcome is not ("ACCOUNT_CREATED" or "ACCOUNT_REUSED")
            || root.CompletionProfileSnapshot is null || root.CompletionResponseBody is null)
            throw new CustomerWorkspaceException(CustomerWorkspaceError.InvariantViolation);
    }

    private static bool ValidProfile(string? value, int maximum) => !string.IsNullOrWhiteSpace(value) && ValidKey(value, maximum);

    private static bool ValidKey(string? value, int maximum)
    {
        if (string.IsNullOrEmpty(value) || value.Length > maximum || value.Contains('\0')) return false;
        try { _ = new UTF8Encoding(false, true).GetByteCount(value); return true; }
        catch (EncoderFallbackException) { return false; }
    }

    private static long LockKey(string[] parts) => BinaryPrimitives.ReadInt64BigEndian(
        SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(parts, LockJsonOptions)).AsSpan(0, 8));

    private static PostgresException? DatabaseError(Exception exception) =>
        exception as PostgresException ?? (exception as DbUpdateException)?.InnerException as PostgresException;
}