// Implements: architecture/reference/components/authentication-authorization-simplification-solution-contract.md §10, §12.5
// constitutional_basis: C-023, C-026, C-059, C-063

using System.Buffers.Binary;
using System.Data;
using System.Security.Cryptography;
using System.Text;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;
using Microsoft.Extensions.Options;
using Npgsql;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public enum IdentityLifecycleCommand
{
    Link,
    Unlink,
    Recovery,
}

public enum IdentityLifecycleProvider
{
    Google,
    Facebook,
    Apple,
    Email,
}

public sealed record IdentityLifecycleOperation(
    Guid OperationReference,
    Guid LinkReference,
    IdentityLifecycleCommand Command,
    IdentityLifecycleProvider Provider,
    string State,
    DateTimeOffset ExpiresAt,
    bool Replayed
);

public sealed class IdentityLifecycleConflictException()
    : Exception("The lifecycle idempotency key was reused with different input.");

public sealed class IdentityLifecycleRecoveryRequiredException()
    : Exception("The identity lifecycle operation requires reconciliation.");

public sealed class IdentityLifecycleLastMethodException()
    : Exception("At least one usable authentication method must remain.");

public sealed class IdentityLifecycleService
{
    private static readonly TimeSpan OperationWindow = TimeSpan.FromMinutes(10);
    private readonly IDbContextFactory<IdentityDbContext> _factory;
    private readonly string _keyVersion;
    private readonly byte[] _idempotencyKey;
    private readonly IKeycloakIdentityLifecycleWriter? _writer;

    public IdentityLifecycleService(
        IDbContextFactory<IdentityDbContext> factory,
        IOptions<IdentityHmacOptions> hmacOptions,
        IKeycloakIdentityLifecycleWriter? writer = null
    )
    {
        _factory = factory;
        var options = hmacOptions.Value;
        if (
            string.IsNullOrWhiteSpace(options.ActiveVersion)
            || string.IsNullOrEmpty(options.Key)
            || options.Key.Length < IdentityHmacOptions.MinKeyLength
        )
            throw new InvalidOperationException(
                "Lifecycle operations require valid versioned identity HMAC material."
            );
        _keyVersion = options.ActiveVersion;
        _idempotencyKey = Encoding.UTF8.GetBytes(options.Key);
        _writer = writer;
    }

    public Task<IdentityLifecycleOperation> BeginLinkAsync(
        VerifiedCustomerActor actor,
        IdentityLifecycleProvider provider,
        Guid stepUpTransactionReference,
        Guid idempotencyKey,
        Guid correlationId,
        CancellationToken ct = default
    )
    {
        if (stepUpTransactionReference == Guid.Empty)
            throw new CustomerWorkspaceException(CustomerWorkspaceError.InvalidInput);
        return BeginAsync(
            actor,
            IdentityLifecycleCommand.Link,
            provider,
            idempotencyKey,
            null,
            correlationId,
            ct
        );
    }

    public Task<IdentityLifecycleOperation> BeginUnlinkAsync(
        VerifiedCustomerActor actor,
        Guid linkReference,
        Guid idempotencyKey,
        Guid correlationId,
        CancellationToken ct = default
    ) => BeginUnlinkResolvedAsync(actor, linkReference, idempotencyKey, correlationId, ct);

    private async Task<IdentityLifecycleOperation> BeginUnlinkResolvedAsync(
        VerifiedCustomerActor actor,
        Guid linkReference,
        Guid idempotencyKey,
        Guid correlationId,
        CancellationToken ct
    )
    {
        if (linkReference == Guid.Empty)
            throw new CustomerWorkspaceException(CustomerWorkspaceError.InvalidInput);
        var provider = await ReadProviderAsync(actor, linkReference, ct);
        return await BeginAsync(
            actor,
            IdentityLifecycleCommand.Unlink,
            provider,
            idempotencyKey,
            linkReference,
            correlationId,
            ct
        );
    }

    public async Task<IdentityLifecycleOperation> CompleteLinkAsync(
        VerifiedCustomerActor actor,
        Guid operationReference,
        string keycloakUserId,
        KeycloakFederatedBinding binding,
        CancellationToken ct = default
    )
    {
        var writer = RequireWriter();
        var operation = await ReadOperationAsync(actor, operationReference, ct);
        if (operation.State == "COMPLETED")
            return operation with { Replayed = true };
        if (
            operation.Command != IdentityLifecycleCommand.Link
            || ProviderAlias(operation.Provider) != binding.ProviderAlias
        )
            throw new IdentityLifecycleConflictException();

        if (operation.State == "PROOF_REQUIRED")
            await TransitionAsync(
                actor,
                operationReference,
                ["PROOF_REQUIRED"],
                "IDP_PENDING",
                true,
                ct
            );
        else if (operation.State != "IDP_PENDING")
            throw new IdentityLifecycleConflictException();
        var before = await writer.ReadBindingsAsync(keycloakUserId, ct);
        var existing = before.SingleOrDefault(item => item.ProviderAlias == binding.ProviderAlias);
        if (existing is not null && existing != binding)
        {
            await TransitionAsync(actor, operationReference, ["IDP_PENDING"], "FAILED", false, ct);
            throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
        }

        var addedByOperation = existing is null;
        if (addedByOperation)
        {
            try
            {
                await writer.AddBindingAsync(keycloakUserId, binding, ct);
            }
            catch (KeycloakLifecycleUnknownOutcomeException)
            {
                if (!(await writer.ReadBindingsAsync(keycloakUserId, ct)).Contains(binding))
                {
                    await RequireRecoveryAsync(actor, operationReference, ct);
                    throw new IdentityLifecycleRecoveryRequiredException();
                }
            }
            catch (KeycloakLifecycleRejectedException)
            {
                await TransitionAsync(
                    actor,
                    operationReference,
                    ["IDP_PENDING"],
                    "FAILED",
                    false,
                    ct
                );
                throw;
            }
        }
        if (!(await writer.ReadBindingsAsync(keycloakUserId, ct)).Contains(binding))
        {
            await RequireRecoveryAsync(actor, operationReference, ct);
            throw new IdentityLifecycleRecoveryRequiredException();
        }

        try
        {
            await CompleteLinkProjectionAsync(actor, operationReference, ct);
        }
        catch (Exception exception)
            when (exception is NpgsqlException or IdentityLifecycleConflictException)
        {
            var reconciled = await ReadOperationAsync(actor, operationReference, ct);
            if (reconciled.State == "COMPLETED")
                return reconciled with { Replayed = true };
            if (
                !addedByOperation
                || reconciled.State != "IDP_PENDING"
                || await ProjectionExistsAsync(actor, reconciled.LinkReference, ct)
            )
            {
                await RequireRecoveryAsync(actor, operationReference, ct);
                throw new IdentityLifecycleRecoveryRequiredException();
            }

            try
            {
                await writer.RemoveBindingAsync(keycloakUserId, binding.ProviderAlias, ct);
            }
            catch (KeycloakLifecycleUnknownOutcomeException)
            {
                // Mandatory read-back below determines whether compensation committed.
            }
            if (
                (await writer.ReadBindingsAsync(keycloakUserId, ct)).Any(item =>
                    item.ProviderAlias == binding.ProviderAlias
                )
            )
            {
                await RequireRecoveryAsync(actor, operationReference, ct);
                throw new IdentityLifecycleRecoveryRequiredException();
            }
            await TransitionAsync(actor, operationReference, ["IDP_PENDING"], "FAILED", false, ct);
            throw new IdentityActionDeniedException(
                "Identity provider link was compensated after projection failure."
            );
        }
        return await ReadOperationAsync(actor, operationReference, ct);
    }

    public async Task<IdentityLifecycleOperation> CompleteUnlinkAsync(
        VerifiedCustomerActor actor,
        Guid operationReference,
        string keycloakUserId,
        CancellationToken ct = default
    )
    {
        var writer = RequireWriter();
        var operation = await ReadOperationAsync(actor, operationReference, ct);
        if (operation.State == "COMPLETED")
            return operation with { Replayed = true };
        if (operation.Command != IdentityLifecycleCommand.Unlink)
            throw new IdentityLifecycleConflictException();
        if (await CountActiveLinksAsync(actor, ct) <= 1)
            throw new IdentityLifecycleLastMethodException();

        await TransitionAsync(
            actor,
            operationReference,
            ["PROOF_REQUIRED"],
            "IDP_PENDING",
            true,
            ct
        );
        var alias = ProviderAlias(operation.Provider);
        if (
            (await writer.ReadBindingsAsync(keycloakUserId, ct)).Any(item =>
                item.ProviderAlias == alias
            )
        )
        {
            try
            {
                await writer.RemoveBindingAsync(keycloakUserId, alias, ct);
            }
            catch (KeycloakLifecycleUnknownOutcomeException)
            {
                if (
                    (await writer.ReadBindingsAsync(keycloakUserId, ct)).Any(item =>
                        item.ProviderAlias == alias
                    )
                )
                {
                    await RequireRecoveryAsync(actor, operationReference, ct);
                    throw new IdentityLifecycleRecoveryRequiredException();
                }
            }
        }
        if (
            (await writer.ReadBindingsAsync(keycloakUserId, ct)).Any(item =>
                item.ProviderAlias == alias
            )
        )
        {
            await RequireRecoveryAsync(actor, operationReference, ct);
            throw new IdentityLifecycleRecoveryRequiredException();
        }

        await CompleteUnlinkProjectionAsync(actor, operationReference, ct);
        return await ReadOperationAsync(actor, operationReference, ct);
    }

    private IKeycloakIdentityLifecycleWriter RequireWriter()
    {
        if (_writer?.IsConfigured != true)
            throw new CustomerWorkspaceException(CustomerWorkspaceError.DependencyUnavailable);
        return _writer;
    }

    private async Task<IdentityLifecycleOperation> ReadOperationAsync(
        VerifiedCustomerActor actor,
        Guid operationReference,
        CancellationToken ct
    )
    {
        await using var db = await _factory.CreateDbContextAsync(ct);
        var connection = await OpenConnectionAsync(db, ct);
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.ReadCommitted,
            ct
        );
        await db.Database.ExecuteSqlRawAsync("SET TRANSACTION READ ONLY", ct);
        await SetActorContextAsync(db, actor, ct);
        await using var command = new NpgsqlCommand(
            """
            SELECT operation_id, target_link_reference, command_type, provider_class,
                   state, created_at
              FROM identity.lifecycle_operations
             WHERE operation_id = @operation
            """,
            connection,
            (NpgsqlTransaction)transaction.GetDbTransaction()
        );
        command.Parameters.AddWithValue("operation", operationReference);
        await using var reader = await command.ExecuteReaderAsync(ct);
        if (!await reader.ReadAsync(ct))
            throw new IdentityActionDeniedException(
                "Identity lifecycle operation is not accessible."
            );
        var operation = new IdentityLifecycleOperation(
            reader.GetGuid(0),
            reader.GetGuid(1),
            Enum.Parse<IdentityLifecycleCommand>(reader.GetString(2), true),
            Enum.Parse<IdentityLifecycleProvider>(reader.GetString(3), true),
            reader.GetString(4),
            reader.GetFieldValue<DateTimeOffset>(5) + OperationWindow,
            false
        );
        await reader.DisposeAsync();
        await transaction.CommitAsync(ct);
        return operation;
    }

    private async Task TransitionAsync(
        VerifiedCustomerActor actor,
        Guid operationReference,
        string[] expectedStates,
        string nextState,
        bool incrementAttempt,
        CancellationToken ct
    )
    {
        await using var db = await _factory.CreateDbContextAsync(ct);
        var connection = await OpenConnectionAsync(db, ct);
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.ReadCommitted,
            ct
        );
        await SetActorContextAsync(db, actor, ct);
        await using var command = new NpgsqlCommand(
            """
            UPDATE identity.lifecycle_operations
               SET state = @next,
                   attempt = attempt + CASE WHEN @increment THEN 1 ELSE 0 END,
                   version = version + 1,
                   terminal_at = CASE
                       WHEN @next IN ('COMPLETED', 'FAILED') THEN now()
                       ELSE NULL
                   END
             WHERE operation_id = @operation
               AND state = ANY(@expected)
            """,
            connection,
            (NpgsqlTransaction)transaction.GetDbTransaction()
        );
        command.Parameters.AddWithValue("next", nextState);
        command.Parameters.AddWithValue("increment", incrementAttempt);
        command.Parameters.AddWithValue("operation", operationReference);
        command.Parameters.AddWithValue("expected", expectedStates);
        if (await command.ExecuteNonQueryAsync(ct) != 1)
            throw new IdentityLifecycleConflictException();
        await transaction.CommitAsync(ct);
    }

    private Task RequireRecoveryAsync(
        VerifiedCustomerActor actor,
        Guid operationReference,
        CancellationToken ct
    ) =>
        TransitionAsync(actor, operationReference, ["IDP_PENDING"], "RECOVERY_REQUIRED", false, ct);

    private async Task CompleteLinkProjectionAsync(
        VerifiedCustomerActor actor,
        Guid operationReference,
        CancellationToken ct
    )
    {
        await using var db = await _factory.CreateDbContextAsync(ct);
        var connection = await OpenConnectionAsync(db, ct);
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.Serializable,
            ct
        );
        await SetActorContextAsync(db, actor, ct);
        var operation = await LockOperationAsync(
            connection,
            (NpgsqlTransaction)transaction.GetDbTransaction(),
            operationReference,
            ct
        );
        if (operation.State == "COMPLETED")
        {
            await transaction.CommitAsync(ct);
            return;
        }
        if (operation.State != "IDP_PENDING")
            throw new IdentityLifecycleConflictException();

        await UpdateStateAsync(
            connection,
            (NpgsqlTransaction)transaction.GetDbTransaction(),
            operationReference,
            "IDP_PENDING",
            "IDP_COMMITTED",
            false,
            ct
        );
        await using var projection = new NpgsqlCommand(
            """
            INSERT INTO identity.provider_link_projections (
                link_id, global_user_id, provider_class, binding_reference, state
            ) VALUES (@link, @user, @provider, @binding, 'ACTIVE')
            """,
            connection,
            (NpgsqlTransaction)transaction.GetDbTransaction()
        );
        projection.Parameters.AddWithValue("link", operation.LinkReference);
        projection.Parameters.AddWithValue("user", GlobalUserId(actor));
        projection.Parameters.AddWithValue(
            "provider",
            operation.Provider.ToString().ToUpperInvariant()
        );
        projection.Parameters.AddWithValue("binding", Guid.NewGuid());
        await projection.ExecuteNonQueryAsync(ct);
        await UpdateStateAsync(
            connection,
            (NpgsqlTransaction)transaction.GetDbTransaction(),
            operationReference,
            "IDP_COMMITTED",
            "COMPLETED",
            true,
            ct
        );
        await transaction.CommitAsync(ct);
    }

    private async Task CompleteUnlinkProjectionAsync(
        VerifiedCustomerActor actor,
        Guid operationReference,
        CancellationToken ct
    )
    {
        await using var db = await _factory.CreateDbContextAsync(ct);
        var connection = await OpenConnectionAsync(db, ct);
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.Serializable,
            ct
        );
        await SetActorContextAsync(db, actor, ct);
        var operation = await LockOperationAsync(
            connection,
            (NpgsqlTransaction)transaction.GetDbTransaction(),
            operationReference,
            ct
        );
        if (operation.State == "COMPLETED")
        {
            await transaction.CommitAsync(ct);
            return;
        }
        if (operation.State != "IDP_PENDING")
            throw new IdentityLifecycleConflictException();
        if (await CountActiveLinksAsync(connection, transaction, ct) <= 1)
            throw new IdentityLifecycleLastMethodException();

        await UpdateStateAsync(
            connection,
            (NpgsqlTransaction)transaction.GetDbTransaction(),
            operationReference,
            "IDP_PENDING",
            "IDP_COMMITTED",
            false,
            ct
        );
        await using var projection = new NpgsqlCommand(
            """
            UPDATE identity.provider_link_projections
               SET state = 'RETIRED', retired_at = now()
             WHERE link_id = @link AND state = 'ACTIVE'
            """,
            connection,
            (NpgsqlTransaction)transaction.GetDbTransaction()
        );
        projection.Parameters.AddWithValue("link", operation.LinkReference);
        if (await projection.ExecuteNonQueryAsync(ct) != 1)
            throw new IdentityLifecycleConflictException();
        await UpdateStateAsync(
            connection,
            (NpgsqlTransaction)transaction.GetDbTransaction(),
            operationReference,
            "IDP_COMMITTED",
            "COMPLETED",
            true,
            ct
        );
        await transaction.CommitAsync(ct);
    }

    private async Task<int> CountActiveLinksAsync(VerifiedCustomerActor actor, CancellationToken ct)
    {
        await using var db = await _factory.CreateDbContextAsync(ct);
        var connection = await OpenConnectionAsync(db, ct);
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.ReadCommitted,
            ct
        );
        await db.Database.ExecuteSqlRawAsync("SET TRANSACTION READ ONLY", ct);
        await SetActorContextAsync(db, actor, ct);
        var count = await CountActiveLinksAsync(connection, transaction, ct);
        await transaction.CommitAsync(ct);
        return count;
    }

    private async Task<bool> ProjectionExistsAsync(
        VerifiedCustomerActor actor,
        Guid linkReference,
        CancellationToken ct
    )
    {
        await using var db = await _factory.CreateDbContextAsync(ct);
        var connection = await OpenConnectionAsync(db, ct);
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.ReadCommitted,
            ct
        );
        await db.Database.ExecuteSqlRawAsync("SET TRANSACTION READ ONLY", ct);
        await SetActorContextAsync(db, actor, ct);
        await using var command = new NpgsqlCommand(
            "SELECT EXISTS (SELECT 1 FROM identity.provider_link_projections WHERE link_id = @link)",
            connection,
            (NpgsqlTransaction)transaction.GetDbTransaction()
        );
        command.Parameters.AddWithValue("link", linkReference);
        var exists = await command.ExecuteScalarAsync(ct) is true;
        await transaction.CommitAsync(ct);
        return exists;
    }

    private static async Task<int> CountActiveLinksAsync(
        NpgsqlConnection connection,
        IDbContextTransaction transaction,
        CancellationToken ct
    )
    {
        await using var command = new NpgsqlCommand(
            "SELECT count(*) FROM identity.provider_link_projections WHERE state = 'ACTIVE'",
            connection,
            (NpgsqlTransaction)transaction.GetDbTransaction()
        );
        return Convert.ToInt32(await command.ExecuteScalarAsync(ct));
    }

    private static async Task<IdentityLifecycleOperation> LockOperationAsync(
        NpgsqlConnection connection,
        NpgsqlTransaction transaction,
        Guid operationReference,
        CancellationToken ct
    )
    {
        await using var command = new NpgsqlCommand(
            """
            SELECT operation_id, target_link_reference, command_type, provider_class,
                   state, created_at
              FROM identity.lifecycle_operations
             WHERE operation_id = @operation
             FOR UPDATE
            """,
            connection,
            transaction
        );
        command.Parameters.AddWithValue("operation", operationReference);
        await using var reader = await command.ExecuteReaderAsync(ct);
        if (!await reader.ReadAsync(ct))
            throw new IdentityActionDeniedException(
                "Identity lifecycle operation is not accessible."
            );
        return new(
            reader.GetGuid(0),
            reader.GetGuid(1),
            Enum.Parse<IdentityLifecycleCommand>(reader.GetString(2), true),
            Enum.Parse<IdentityLifecycleProvider>(reader.GetString(3), true),
            reader.GetString(4),
            reader.GetFieldValue<DateTimeOffset>(5) + OperationWindow,
            false
        );
    }

    private static async Task UpdateStateAsync(
        NpgsqlConnection connection,
        NpgsqlTransaction transaction,
        Guid operationReference,
        string expectedState,
        string nextState,
        bool terminal,
        CancellationToken ct
    )
    {
        await using var command = new NpgsqlCommand(
            """
            UPDATE identity.lifecycle_operations
               SET state = @next,
                   version = version + 1,
                   terminal_at = CASE WHEN @terminal THEN now() ELSE NULL END
             WHERE operation_id = @operation AND state = @expected
            """,
            connection,
            transaction
        );
        command.Parameters.AddWithValue("next", nextState);
        command.Parameters.AddWithValue("terminal", terminal);
        command.Parameters.AddWithValue("operation", operationReference);
        command.Parameters.AddWithValue("expected", expectedState);
        if (await command.ExecuteNonQueryAsync(ct) != 1)
            throw new IdentityLifecycleConflictException();
    }

    private static Guid GlobalUserId(VerifiedCustomerActor actor)
    {
        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes($"{actor.Issuer}\u001f{actor.Subject}"))[
            ..16
        ];
        bytes[6] = (byte)((bytes[6] & 0x0f) | 0x50);
        bytes[8] = (byte)((bytes[8] & 0x3f) | 0x80);
        return new Guid(bytes);
    }

    private static string ProviderAlias(IdentityLifecycleProvider provider) =>
        provider switch
        {
            IdentityLifecycleProvider.Google => "google",
            IdentityLifecycleProvider.Facebook => "facebook",
            IdentityLifecycleProvider.Apple => "apple",
            _ => throw new IdentityActionDeniedException(
                "The selected provider does not use a federated lifecycle binding."
            ),
        };

    private static async Task<NpgsqlConnection> OpenConnectionAsync(
        IdentityDbContext db,
        CancellationToken ct
    )
    {
        if (
            db.Database.GetDbConnection() is not NpgsqlConnection connection
            || new NpgsqlConnectionStringBuilder(connection.ConnectionString).NoResetOnClose
        )
            throw new InvalidOperationException(
                "Lifecycle operations require a reset-enabled PostgreSQL connection."
            );
        await db.Database.OpenConnectionAsync(ct);
        return connection;
    }

    private async Task<IdentityLifecycleProvider> ReadProviderAsync(
        VerifiedCustomerActor actor,
        Guid linkReference,
        CancellationToken ct
    )
    {
        await using var db = await _factory.CreateDbContextAsync(ct);
        if (
            db.Database.GetDbConnection() is not NpgsqlConnection connection
            || new NpgsqlConnectionStringBuilder(connection.ConnectionString).NoResetOnClose
        )
            throw new InvalidOperationException(
                "Lifecycle operations require a reset-enabled PostgreSQL connection."
            );
        await db.Database.OpenConnectionAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.ReadCommitted,
            ct
        );
        await db.Database.ExecuteSqlRawAsync("SET TRANSACTION READ ONLY", ct);
        await SetActorContextAsync(db, actor, ct);
        await using var command = new NpgsqlCommand(
            """
            SELECT provider_class
              FROM identity.provider_link_projections
             WHERE link_id = @link AND state = 'ACTIVE'
            """,
            connection,
            (NpgsqlTransaction)transaction.GetDbTransaction()
        );
        command.Parameters.AddWithValue("link", linkReference);
        var value = await command.ExecuteScalarAsync(ct) as string;
        await transaction.CommitAsync(ct);
        return value switch
        {
            "GOOGLE" => IdentityLifecycleProvider.Google,
            "FACEBOOK" => IdentityLifecycleProvider.Facebook,
            "APPLE" => IdentityLifecycleProvider.Apple,
            "EMAIL" => IdentityLifecycleProvider.Email,
            _ => throw new IdentityActionDeniedException(
                "Identity provider link is not accessible."
            ),
        };
    }

    private async Task<IdentityLifecycleOperation> BeginAsync(
        VerifiedCustomerActor actor,
        IdentityLifecycleCommand command,
        IdentityLifecycleProvider provider,
        Guid idempotencyKey,
        Guid? requestedLinkReference,
        Guid correlationId,
        CancellationToken ct
    )
    {
        if (
            actor is null
            || string.IsNullOrWhiteSpace(actor.Issuer)
            || string.IsNullOrWhiteSpace(actor.Subject)
            || idempotencyKey == Guid.Empty
            || correlationId == Guid.Empty
        )
            throw new CustomerWorkspaceException(CustomerWorkspaceError.InvalidInput);

        var digest = Digest(idempotencyKey);
        var operationId = Guid.NewGuid();
        var linkReference = requestedLinkReference ?? Guid.NewGuid();
        var commandName = command.ToString().ToUpperInvariant();
        var providerName = provider.ToString().ToUpperInvariant();

        await using var db = await _factory.CreateDbContextAsync(ct);
        if (
            db.Database.GetDbConnection() is not NpgsqlConnection connection
            || new NpgsqlConnectionStringBuilder(connection.ConnectionString).NoResetOnClose
        )
            throw new InvalidOperationException(
                "Lifecycle operations require a reset-enabled PostgreSQL connection."
            );
        await db.Database.OpenConnectionAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.ReadCommitted,
            ct
        );
        await SetActorContextAsync(db, actor, ct);
        foreach (
            var lockKey in new[]
            {
                LockKey(["wc123-lifecycle-actor", actor.Issuer, actor.Subject]),
                LockKey(["wc123-lifecycle-link", linkReference.ToString("D")]),
            }.Order()
        )
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT pg_catalog.pg_advisory_xact_lock({lockKey})",
                ct
            );

        await using var insert = new NpgsqlCommand(
            """
            INSERT INTO identity.lifecycle_operations (
                operation_id, actor_issuer, actor_subject, command_type, provider_class,
                idempotency_key_version, idempotency_digest, target_link_reference,
                state, correlation_id
            ) VALUES (
                @operation, @issuer, @subject, @command, @provider,
                @version, @digest, @link, 'PROOF_REQUIRED', @correlation
            )
            ON CONFLICT (actor_issuer, actor_subject, command_type, idempotency_digest)
            DO NOTHING
            RETURNING operation_id, target_link_reference, state, created_at
            """,
            connection,
            transaction.GetDbTransaction() as NpgsqlTransaction
        );
        insert.Parameters.AddWithValue("operation", operationId);
        insert.Parameters.AddWithValue("issuer", actor.Issuer);
        insert.Parameters.AddWithValue("subject", actor.Subject);
        insert.Parameters.AddWithValue("command", commandName);
        insert.Parameters.AddWithValue("provider", providerName);
        insert.Parameters.AddWithValue("version", _keyVersion);
        insert.Parameters.AddWithValue("digest", digest);
        insert.Parameters.AddWithValue("link", linkReference);
        insert.Parameters.AddWithValue("correlation", correlationId);

        await using var reader = await insert.ExecuteReaderAsync(ct);
        if (await reader.ReadAsync(ct))
        {
            var created = reader.GetFieldValue<DateTimeOffset>(3);
            var result = new IdentityLifecycleOperation(
                reader.GetGuid(0),
                reader.GetGuid(1),
                command,
                provider,
                reader.GetString(2),
                created + OperationWindow,
                false
            );
            await reader.DisposeAsync();
            await transaction.CommitAsync(ct);
            return result;
        }
        await reader.DisposeAsync();

        await using var replay = new NpgsqlCommand(
            """
            SELECT operation_id, target_link_reference, provider_class, state, created_at
              FROM identity.lifecycle_operations
             WHERE actor_issuer = @issuer
               AND actor_subject = @subject
               AND command_type = @command
               AND idempotency_digest = @digest
            """,
            connection,
            transaction.GetDbTransaction() as NpgsqlTransaction
        );
        replay.Parameters.AddWithValue("issuer", actor.Issuer);
        replay.Parameters.AddWithValue("subject", actor.Subject);
        replay.Parameters.AddWithValue("command", commandName);
        replay.Parameters.AddWithValue("digest", digest);
        await using var replayReader = await replay.ExecuteReaderAsync(ct);
        if (!await replayReader.ReadAsync(ct))
            throw new CustomerWorkspaceException(CustomerWorkspaceError.InvariantViolation);
        var persistedLink = replayReader.GetGuid(1);
        if (
            replayReader.GetString(2) != providerName
            || (requestedLinkReference.HasValue && requestedLinkReference != persistedLink)
        )
            throw new IdentityLifecycleConflictException();
        var replayed = new IdentityLifecycleOperation(
            replayReader.GetGuid(0),
            persistedLink,
            command,
            provider,
            replayReader.GetString(3),
            replayReader.GetFieldValue<DateTimeOffset>(4) + OperationWindow,
            true
        );
        await replayReader.DisposeAsync();
        await transaction.CommitAsync(ct);
        return replayed;
    }

    private string Digest(Guid key)
    {
        using var hmac = new HMACSHA256(_idempotencyKey);
        return Convert
            .ToHexString(
                hmac.ComputeHash(Encoding.UTF8.GetBytes($"wc123:lifecycle:idempotency:{key:D}"))
            )
            .ToLowerInvariant();
    }

    private static long LockKey(IEnumerable<string> parts)
    {
        var digest = SHA256.HashData(Encoding.UTF8.GetBytes(string.Join('\u001f', parts)));
        return BinaryPrimitives.ReadInt64BigEndian(digest);
    }

    private static async Task SetActorContextAsync(
        IdentityDbContext db,
        VerifiedCustomerActor actor,
        CancellationToken ct
    )
    {
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            SELECT pg_catalog.set_config('app.identity_issuer', {actor.Issuer}, true),
                   pg_catalog.set_config('app.identity_subject', {actor.Subject}, true),
                   pg_catalog.set_config('app.current_membership_id', '', true),
                   pg_catalog.set_config('app.tenant_id', '', true),
                   pg_catalog.set_config('app.current_tenant_id', '', true),
                   pg_catalog.set_config('lock_timeout', '3s', true),
                   pg_catalog.set_config('statement_timeout', '10s', true),
                   pg_catalog.set_config('idle_in_transaction_session_timeout', '15s', true)
            """,
            ct
        );
    }
}
