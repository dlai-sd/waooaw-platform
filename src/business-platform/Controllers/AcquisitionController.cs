// Implements: WC-096 §4.3 Marketplace And Disclosure
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-04
// Constitutional basis: C-005, C-023, C-026, C-049, C-059, C-063

using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.PlatformApprovals;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed record ContinueAcquisitionRequest(
    string ProfessionalType,
    string ProfessionalVersion,
    string Intent,
    string DisclosureRevision,
    string TermsVersion,
    string Acceptance,
    string? CouponCode = null,
    string? PackageCode = null,
    string? QuoteVersion = null,
    bool ValidateQuoteBeforeCharge = false
);

public sealed record HireQuoteRequest(
    string ProfessionalType,
    string ProfessionalVersion,
    string? PackageCode = null
);

public sealed record HireQuoteResponse(
    string PackageCode,
    string Currency,
    long GrossAmountInrPaise,
    long GstAmountInrPaise,
    long BasePriceInrPaise,
    string Cadence,
    int BillingPeriodDays,
    string QuoteVersion
);

public sealed record AcquisitionContinuationResponse(
    Guid RelationshipId,
    string Intent,
    string Status,
    string ResumePath,
    bool Replayed
);

public sealed record AcquisitionIntentResponse(
    Guid AcquisitionIntentId,
    string Intent,
    string Status,
    string ContractDocumentUri,
    string ContractHash,
    DateTimeOffset ExpiresAt,
    bool Replayed,
    HireQuoteResponse? Quote = null
);

[ApiController]
[Authorize]
[Route("api/v1/acquisition")]
public sealed partial class AcquisitionController(
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
    IProfessionalCatalog catalog,
    EmploymentRelationshipService relationships,
    ILogger<AcquisitionController> logger,
    RelationshipTrialService? trials = null,
    HireQuoteService? quotes = null,
    PlatformProfessionalApprovalService? approvals = null
) : ControllerBase
{
    [GeneratedRegex(@"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")]
    private static partial Regex PackageCodePattern();

    // Used only where no approval service is wired (unit tests); the deployed service always gates on the Founder's approval.
    private static async Task<Guid?> ActiveWorkspaceAdmissionAsync(
        EmploymentRelationshipDbContext db,
        Guid tenantId,
        ProfessionalDisclosure activeDisclosure,
        CancellationToken cancellationToken
    ) =>
        await db
            .AgentAdmissions.AsNoTracking()
            .Where(value =>
                value.TenantId == tenantId
                && value.State == AgentAdmissionState.Active
                && value.ProfessionalTypeId == activeDisclosure.ProfessionalType
                && value.ProfessionalVersion == activeDisclosure.ProjectionVersion
                && value.AdmissionContentDigest != null
                && value.EvidenceSetDigest != null
                && value.ArtifactDigest != null
            )
            .OrderByDescending(value => value.UpdatedAt)
            .Select(value => (Guid?)value.AdmissionId)
            .FirstOrDefaultAsync(cancellationToken);

    [HttpPost("hire-quote")]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> PreviewHireQuoteAsync(
        [FromBody] HireQuoteRequest request,
        [FromHeader(Name = "X-Correlation-ID")] Guid? correlationId,
        CancellationToken cancellationToken
    )
    {
        var disclosure = catalog.GetDisclosure(request.ProfessionalType);
        if (
            disclosure is null
            || !disclosure.Eligibility.Eligible
            || disclosure.ProjectionVersion != request.ProfessionalVersion
            || !IsValidPackageCode(request.PackageCode)
        )
            return Problem(
                statusCode: StatusCodes.Status409Conflict,
                title: "Hire pricing is unavailable for this offer"
            );
        var (quote, failure) = await ResolveQuoteAsync(
            disclosure,
            request.PackageCode,
            correlationId ?? Guid.NewGuid(),
            cancellationToken
        );
        return failure ?? Ok(QuoteResponse(quote!));
    }

    [HttpPost("intents")]
    [CustomerIdentityRoute]
    public async Task<IActionResult> CreateIntentAsync(
        [FromBody] ContinueAcquisitionRequest request,
        [FromHeader(Name = "Idempotency-Key")] Guid? idempotencyKey,
        CancellationToken cancellationToken
    )
    {
        if (!idempotencyKey.HasValue || idempotencyKey == Guid.Empty)
            return Problem(
                statusCode: StatusCodes.Status400BadRequest,
                title: "Idempotency key is required"
            );
        if (!TryValidateRequest(request, out var intent, out var disclosure))
            return Problem(
                statusCode: StatusCodes.Status409Conflict,
                title: "Acquisition disclosure is stale or invalid"
            );

        var actorIdentityHash = ActorIdentityHash();
        var materialHash = MaterialHash(request, intent);
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        // A person who has signed in but not registered has no tenant; row security admits only their own pseudonymous actor hash.
        await using var transaction = db.Database.IsRelational()
            ? await BindActorScopeAsync(db, actorIdentityHash, cancellationToken)
            : null;
        var existing = await db.AcquisitionIntents.SingleOrDefaultAsync(
            value =>
                value.ActorIdentityHash == actorIdentityHash
                && value.IdempotencyKey == idempotencyKey.Value,
            cancellationToken
        );
        if (existing is not null)
        {
            if (
                !string.Equals(existing.MaterialRequestHash, materialHash, StringComparison.Ordinal)
            )
                return Problem(
                    statusCode: StatusCodes.Status409Conflict,
                    title: "Acquisition idempotency conflict"
                );
            if (intent == "HIRE")
            {
                var stale = await ValidateStoredQuoteAsync(
                    existing,
                    request,
                    disclosure!,
                    idempotencyKey.Value,
                    cancellationToken
                );
                if (stale is not null)
                    return stale;
            }
            return Ok(IntentResponse(existing, true));
        }

        var (quote, quoteFailure) = await LockQuoteAsync(
            request,
            intent,
            disclosure!,
            idempotencyKey.Value,
            cancellationToken
        );
        if (quoteFailure is not null)
            return quoteFailure;
        Guid? hireTenantId = null;
        Guid? hireParticipantId = null;
        if (
            quote is not null
            && TryGetMembership(out var quotedTenantId, out var quotedParticipantId)
        )
        {
            hireTenantId = quotedTenantId;
            hireParticipantId = quotedParticipantId;
        }

        var now = DateTimeOffset.UtcNow;
        var documentUri =
            $"/employment-contract?professionalType={Uri.EscapeDataString(disclosure!.ProfessionalType)}"
            + $"&version={Uri.EscapeDataString(disclosure.ProjectionVersion)}"
            + $"&disclosureRevision={Uri.EscapeDataString(disclosure.DisclosureRevision)}"
            + $"&termsVersion={Uri.EscapeDataString(disclosure.TermsVersion)}"
            + $"&mode={intent.ToLowerInvariant()}";
        var acquisitionIntent = new AcquisitionIntent
        {
            AcquisitionIntentId = idempotencyKey.Value,
            ActorIdentityHash = actorIdentityHash,
            IdempotencyKey = idempotencyKey.Value,
            TenantId = hireTenantId,
            ParticipantId = hireParticipantId,
            ProfessionalType = disclosure.ProfessionalType,
            ProfessionalVersion = disclosure.ProjectionVersion,
            Mode = intent,
            DisclosureRevision = disclosure.DisclosureRevision,
            ContractVersion = disclosure.TermsVersion,
            ContractDocumentUri = documentUri,
            ContractHash = ContractHash(disclosure, intent, quote),
            MaterialRequestHash = materialHash,
            CouponCode = NormalizeCoupon(request.CouponCode),
            QuotePackageId = quote?.PackageId,
            QuotePackageCode = quote?.PackageCode,
            QuotePeriodDays = quote?.BillingPeriodDays,
            QuoteGrossInrPaise = quote?.GrossAmountInrPaise,
            QuoteGstInrPaise = quote?.GstAmountInrPaise,
            QuoteBaseInrPaise = quote?.BasePriceInrPaise,
            QuoteVersion = quote?.QuoteVersion,
            ContractAcceptedAt = now,
            ExpiresAt = now.AddHours(24),
        };
        db.AcquisitionIntents.Add(acquisitionIntent);
        await db.SaveChangesAsync(cancellationToken);
        if (transaction is not null)
            await transaction.CommitAsync(cancellationToken);
        return StatusCode(StatusCodes.Status201Created, IntentResponse(acquisitionIntent, false));
    }

    [HttpPost("continuations")]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> ContinueAsync(
        [FromBody] ContinueAcquisitionRequest request,
        [FromHeader(Name = "Idempotency-Key")] Guid? idempotencyKey,
        [FromHeader(Name = "X-Correlation-ID")] Guid? correlationId,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetMembership(out var tenantId, out var participantId))
            return Forbid();
        if (!idempotencyKey.HasValue || idempotencyKey == Guid.Empty)
            return Problem(
                statusCode: StatusCodes.Status400BadRequest,
                title: "Idempotency key is required"
            );

        var intent = request.Intent.Trim().ToUpperInvariant();
        if (intent == "TRIAL" && (trials is null || !trials.IsConfigured))
            return Problem(
                statusCode: StatusCodes.Status409Conflict,
                title: "Trial is currently unavailable",
                detail: "Trial owner services are not available. No relationship was created."
            );
        if (!TryValidateRequest(request, out intent, out var disclosure))
            return Problem(
                statusCode: StatusCodes.Status409Conflict,
                title: "Acquisition disclosure is stale or invalid"
            );
        var activeDisclosure = disclosure!;

        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var actorIdentityHash = ActorIdentityHash(tenantId, participantId);
        var materialHash = MaterialHash(request, intent);
        // The intent may have been started before registration (no tenant), so it is claimed under the actor's own scope.
        await using var claimScope = db.Database.IsRelational()
            ? await BindActorScopeAsync(db, actorIdentityHash, cancellationToken)
            : null;
        var acquisitionIntent = await db.AcquisitionIntents.SingleOrDefaultAsync(
            value =>
                value.ActorIdentityHash == actorIdentityHash
                && value.IdempotencyKey == idempotencyKey.Value,
            cancellationToken
        );
        if (acquisitionIntent is null)
        {
            var (quote, quoteFailure) = await LockQuoteAsync(
                request,
                intent,
                activeDisclosure,
                idempotencyKey.Value,
                cancellationToken
            );
            if (quoteFailure is not null)
                return quoteFailure;
            var now = DateTimeOffset.UtcNow;
            acquisitionIntent = new AcquisitionIntent
            {
                AcquisitionIntentId = idempotencyKey.Value,
                ActorIdentityHash = actorIdentityHash,
                IdempotencyKey = idempotencyKey.Value,
                TenantId = tenantId,
                ParticipantId = participantId,
                ProfessionalType = activeDisclosure.ProfessionalType,
                ProfessionalVersion = activeDisclosure.ProjectionVersion,
                Mode = intent,
                DisclosureRevision = activeDisclosure.DisclosureRevision,
                ContractVersion = activeDisclosure.TermsVersion,
                ContractDocumentUri =
                    $"/employment-contract?professionalType={Uri.EscapeDataString(activeDisclosure.ProfessionalType)}"
                    + $"&version={Uri.EscapeDataString(activeDisclosure.ProjectionVersion)}"
                    + $"&disclosureRevision={Uri.EscapeDataString(activeDisclosure.DisclosureRevision)}"
                    + $"&termsVersion={Uri.EscapeDataString(activeDisclosure.TermsVersion)}"
                    + $"&mode={intent.ToLowerInvariant()}",
                ContractHash = ContractHash(activeDisclosure, intent, quote),
                MaterialRequestHash = materialHash,
                CouponCode = NormalizeCoupon(request.CouponCode),
                QuotePackageId = quote?.PackageId,
                QuotePackageCode = quote?.PackageCode,
                QuotePeriodDays = quote?.BillingPeriodDays,
                QuoteGrossInrPaise = quote?.GrossAmountInrPaise,
                QuoteGstInrPaise = quote?.GstAmountInrPaise,
                QuoteBaseInrPaise = quote?.BasePriceInrPaise,
                QuoteVersion = quote?.QuoteVersion,
                Status = "READY_TO_COMPLETE",
                ContractAcceptedAt = now,
                ExpiresAt = now.AddHours(24),
            };
            db.AcquisitionIntents.Add(acquisitionIntent);
            await db.SaveChangesAsync(cancellationToken);
        }
        else
        {
            if (
                acquisitionIntent.MaterialRequestHash != materialHash
                || acquisitionIntent.ExpiresAt <= DateTimeOffset.UtcNow
            )
                return Problem(
                    statusCode: StatusCodes.Status409Conflict,
                    title: "Acquisition intent is stale or conflicts with this request"
                );
            if (
                acquisitionIntent.TenantId.HasValue && acquisitionIntent.TenantId.Value != tenantId
                || acquisitionIntent.ParticipantId.HasValue
                    && acquisitionIntent.ParticipantId.Value != participantId
            )
                return Problem(
                    statusCode: StatusCodes.Status409Conflict,
                    title: "Acquisition intent belongs to another customer workspace"
                );
            // A paid Hire completes at the price the customer accepted, so a stored quote is never re-priced here.
            if (intent == "HIRE" && acquisitionIntent.ToQuote() is null)
                return Problem(
                    statusCode: StatusCodes.Status409Conflict,
                    title: "Hire price was not locked for this request. Review the offer again.",
                    type: HireQuoteChangedType
                );
            if (
                acquisitionIntent.Status == "COMPLETED"
                && acquisitionIntent.RelationshipId.HasValue
                && acquisitionIntent.TenantId == tenantId
                && acquisitionIntent.ParticipantId == participantId
            )
                return Ok(
                    new AcquisitionContinuationResponse(
                        acquisitionIntent.RelationshipId.Value,
                        intent,
                        "READY",
                        $"/relationships/{acquisitionIntent.RelationshipId.Value}",
                        true
                    )
                );
            acquisitionIntent.TenantId = tenantId;
            acquisitionIntent.ParticipantId = participantId;
            acquisitionIntent.Status = "READY_TO_COMPLETE";
            acquisitionIntent.UpdatedAt = DateTimeOffset.UtcNow;
            await db.SaveChangesAsync(cancellationToken);
        }
        if (claimScope is not null)
            await claimScope.CommitAsync(cancellationToken);
        // The Founder's approval of this exact version is the gate; the workspace's own admission follows from it.
        var admissionId = approvals is not null
            ? await approvals.EnsureWorkspaceAdmissionAsync(
                tenantId,
                participantId,
                activeDisclosure.ProfessionalType,
                activeDisclosure.ProjectionVersion,
                cancellationToken
            )
            : await ActiveWorkspaceAdmissionAsync(
                db,
                tenantId,
                activeDisclosure,
                cancellationToken
            );
        if (!admissionId.HasValue)
            return Problem(
                statusCode: StatusCodes.Status409Conflict,
                title: "Professional is not currently available"
            );

        try
        {
            var lifecycleCorrelationId = correlationId ?? idempotencyKey.Value;
            var acquisitionEvidence = new RelationshipAcquisitionEvidence(
                acquisitionIntent.AcquisitionIntentId,
                intent,
                activeDisclosure.DisclosureRevision,
                activeDisclosure.TermsVersion,
                acquisitionIntent.ContractHash,
                acquisitionIntent.ContractAcceptedAt
            );
            AdmitRelationshipResult result;
            if (intent == "TRIAL")
            {
                if (trials is null)
                    return Problem(
                        statusCode: StatusCodes.Status503ServiceUnavailable,
                        title: "Trial owners unavailable"
                    );
                acquisitionIntent.PlannedRelationshipId ??= Guid.NewGuid();
                acquisitionIntent.PlannedAgentInstanceId ??= Guid.NewGuid();
                acquisitionIntent.Status = "COMPLETING";
                acquisitionIntent.UpdatedAt = DateTimeOffset.UtcNow;
                await db.SaveChangesAsync(cancellationToken);
                result = (
                    await trials.CompleteAcquisitionAsync(
                        tenantId,
                        participantId,
                        acquisitionIntent.AcquisitionIntentId,
                        activeDisclosure.ProfessionalType,
                        activeDisclosure.ProjectionVersion,
                        admissionId.Value,
                        acquisitionIntent.PlannedRelationshipId.Value,
                        acquisitionIntent.PlannedAgentInstanceId.Value,
                        lifecycleCorrelationId,
                        acquisitionEvidence,
                        cancellationToken,
                        TrialIdentityHash.FromClaims(User)
                    )
                ).Admission;
            }
            else
                result = await relationships.AdmitFromAcquisitionAsync(
                    tenantId,
                    participantId,
                    idempotencyKey.Value,
                    activeDisclosure.ProfessionalType,
                    admissionId.Value,
                    activeDisclosure.ProjectionVersion,
                    lifecycleCorrelationId,
                    acquisitionEvidence,
                    cancellationToken
                );
            var participantRole =
                intent == "HIRE"
                    ? RelationshipParticipantRole.Employer
                    : RelationshipParticipantRole.Evaluator;
            if (
                intent == "HIRE"
                && result.Relationship.State == EmploymentRelationshipState.Discovered
            )
            {
                await relationships.TransitionAsync(
                    tenantId,
                    result.Relationship.RelationshipId,
                    participantId,
                    participantRole,
                    EmploymentRelationshipState.Interviewing,
                    lifecycleCorrelationId,
                    false,
                    cancellationToken
                );
            }
            if (
                intent == "HIRE"
                && result.Relationship.State
                    is EmploymentRelationshipState.Discovered
                        or EmploymentRelationshipState.Interviewing
            )
            {
                await relationships.TransitionAsync(
                    tenantId,
                    result.Relationship.RelationshipId,
                    participantId,
                    RelationshipParticipantRole.Employer,
                    EmploymentRelationshipState.Configuring,
                    lifecycleCorrelationId,
                    false,
                    cancellationToken
                );
            }
            var response = new AcquisitionContinuationResponse(
                result.Relationship.RelationshipId,
                intent,
                "READY",
                $"/relationships/{result.Relationship.RelationshipId}",
                !result.Created
            );
            acquisitionIntent.RelationshipId = result.Relationship.RelationshipId;
            acquisitionIntent.Status = "COMPLETED";
            acquisitionIntent.CompletedAt = DateTimeOffset.UtcNow;
            acquisitionIntent.UpdatedAt = acquisitionIntent.CompletedAt.Value;
            await db.SaveChangesAsync(cancellationToken);
            return result.Created
                ? StatusCode(StatusCodes.Status201Created, response)
                : Ok(response);
        }
        catch (ConstitutionalActionDeniedException exception)
        {
            acquisitionIntent.Status = "UNRESOLVED";
            acquisitionIntent.UpdatedAt = DateTimeOffset.UtcNow;
            await db.SaveChangesAsync(cancellationToken);
            return Problem(
                statusCode: StatusCodes.Status403Forbidden,
                title: "Constitutional authorization denied",
                detail: exception.Message
            );
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            acquisitionIntent.Status = "UNRESOLVED";
            acquisitionIntent.UpdatedAt = DateTimeOffset.UtcNow;
            await db.SaveChangesAsync(cancellationToken);
            logger.LogError(
                exception,
                "Acquisition continuation failed for correlation {CorrelationId} and intent {Intent}",
                correlationId ?? idempotencyKey.Value,
                intent
            );
            return Problem(
                statusCode: StatusCodes.Status503ServiceUnavailable,
                title: "Acquisition continuation unavailable"
            );
        }
    }

    private bool TryValidateRequest(
        ContinueAcquisitionRequest request,
        out string intent,
        out ProfessionalDisclosure? disclosure
    )
    {
        intent = request.Intent.Trim().ToUpperInvariant();
        disclosure = catalog.GetDisclosure(request.ProfessionalType);
        return request.Acceptance == "ACCEPT_EMPLOYMENT_CONTRACT"
            && IsValidCoupon(request.CouponCode)
            && IsValidPackageCode(request.PackageCode)
            && intent is "TRIAL" or "HIRE"
            && disclosure is not null
            && disclosure.Eligibility.Eligible
            && disclosure.ProjectionVersion == request.ProfessionalVersion
            && disclosure.DisclosureRevision == request.DisclosureRevision
            && disclosure.TermsVersion == request.TermsVersion
            && (intent != "TRIAL" || disclosure.Trial.Available);
    }

    private const string HireQuoteChangedType = "https://waooaw.com/problems/hire-quote-changed";
    private const string HireQuoteUnavailableType =
        "https://waooaw.com/problems/hire-quote-unavailable";

    private static bool IsValidPackageCode(string? packageCode) =>
        string.IsNullOrWhiteSpace(packageCode) || PackageCodePattern().IsMatch(packageCode.Trim());

    private static HireQuoteResponse QuoteResponse(HireQuote quote) =>
        new(
            quote.PackageCode,
            HireQuote.Currency,
            quote.GrossAmountInrPaise,
            quote.GstAmountInrPaise,
            quote.BasePriceInrPaise,
            quote.Cadence,
            quote.BillingPeriodDays,
            quote.QuoteVersion
        );

    private async Task<(HireQuote? Quote, IActionResult? Failure)> ResolveQuoteAsync(
        ProfessionalDisclosure disclosure,
        string? packageCode,
        Guid correlationId,
        CancellationToken cancellationToken
    )
    {
        if (quotes is null)
            return (
                null,
                Problem(
                    statusCode: StatusCodes.Status503ServiceUnavailable,
                    title: "Hire pricing is unavailable right now",
                    type: HireQuoteUnavailableType
                )
            );
        if (!TryGetMembership(out var tenantId, out var participantId))
            return (
                null,
                Problem(
                    statusCode: StatusCodes.Status409Conflict,
                    title: "Hire pricing needs a customer workspace",
                    type: HireQuoteUnavailableType
                )
            );
        try
        {
            var quote = await quotes.ResolveAsync(
                tenantId,
                participantId.ToString("D"),
                disclosure.ProfessionalType,
                disclosure.ProjectionVersion,
                packageCode,
                correlationId.ToString("D"),
                cancellationToken
            );
            return (quote, null);
        }
        catch (HireQuoteNotOfferedException exception)
        {
            return (
                null,
                Problem(
                    statusCode: StatusCodes.Status409Conflict,
                    title: "Hire is not available for sale right now",
                    detail: exception.Message,
                    type: HireQuoteUnavailableType
                )
            );
        }
        catch (HireQuoteUnavailableException exception)
        {
            logger.LogWarning(
                exception,
                "hire_quote decision=unavailable correlation={Correlation}",
                correlationId
            );
            return (
                null,
                Problem(
                    statusCode: StatusCodes.Status503ServiceUnavailable,
                    title: "Hire pricing is unavailable right now",
                    type: HireQuoteUnavailableType
                )
            );
        }
    }

    // A Hire is only ever priced here; Trial has no amount.
    private async Task<(HireQuote? Quote, IActionResult? Failure)> LockQuoteAsync(
        ContinueAcquisitionRequest request,
        string intent,
        ProfessionalDisclosure disclosure,
        Guid correlationId,
        CancellationToken cancellationToken
    )
    {
        if (intent != "HIRE")
            return (null, null);
        var (quote, failure) = await ResolveQuoteAsync(
            disclosure,
            request.PackageCode,
            correlationId,
            cancellationToken
        );
        if (failure is not null)
            return (null, failure);
        return (quote, QuoteVersionMismatch(request, quote!));
    }

    private async Task<IActionResult?> ValidateStoredQuoteAsync(
        AcquisitionIntent stored,
        ContinueAcquisitionRequest request,
        ProfessionalDisclosure disclosure,
        Guid correlationId,
        CancellationToken cancellationToken
    )
    {
        var locked = stored.ToQuote();
        if (locked is null)
            return Problem(
                statusCode: StatusCodes.Status409Conflict,
                title: "Hire price was not locked for this request. Review the offer again.",
                type: HireQuoteChangedType
            );
        if (!request.ValidateQuoteBeforeCharge)
            return QuoteVersionMismatch(request, locked);
        var (current, failure) = await ResolveQuoteAsync(
            disclosure,
            request.PackageCode,
            correlationId,
            cancellationToken
        );
        if (failure is not null)
            return failure;
        return string.Equals(current!.QuoteVersion, locked.QuoteVersion, StringComparison.Ordinal)
            ? QuoteVersionMismatch(request, locked)
            : Problem(
                statusCode: StatusCodes.Status409Conflict,
                title: "The Hire price changed. Review the offer and accept it again.",
                type: HireQuoteChangedType
            );
    }

    private IActionResult? QuoteVersionMismatch(
        ContinueAcquisitionRequest request,
        HireQuote quote
    ) =>
        string.IsNullOrWhiteSpace(request.QuoteVersion)
        || string.Equals(request.QuoteVersion, quote.QuoteVersion, StringComparison.Ordinal)
            ? null
            : Problem(
                statusCode: StatusCodes.Status409Conflict,
                title: "The Hire price changed. Review the offer and accept it again.",
                type: HireQuoteChangedType
            );

    private static async Task<Microsoft.EntityFrameworkCore.Storage.IDbContextTransaction> BindActorScopeAsync(
        EmploymentRelationshipDbContext db,
        string actorIdentityHash,
        CancellationToken cancellationToken
    )
    {
        var transaction = await db.Database.BeginTransactionAsync(cancellationToken);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_catalog.set_config('app.acquisition_actor_hash', {actorIdentityHash}, true)",
            cancellationToken
        );
        return transaction;
    }

    private string ActorIdentityHash(Guid? tenantId = null, Guid? participantId = null)
    {
        var issuer = User.FindFirstValue("iss");
        var subject = User.FindFirstValue("sub") ?? User.FindFirstValue(ClaimTypes.NameIdentifier);
        if (!string.IsNullOrWhiteSpace(issuer) && !string.IsNullOrWhiteSpace(subject))
            return Hash($"{issuer}\u001f{subject}");
        if (tenantId.HasValue && participantId.HasValue)
            return Hash($"membership\u001f{tenantId:D}\u001f{participantId:D}");
        throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
    }

    private static string MaterialHash(ContinueAcquisitionRequest request, string intent) =>
        Hash(
            JsonSerializer.Serialize(
                new
                {
                    request.ProfessionalType,
                    request.ProfessionalVersion,
                    Intent = intent,
                    request.DisclosureRevision,
                    request.TermsVersion,
                    request.Acceptance,
                    CouponCode = NormalizeCoupon(request.CouponCode),
                    PackageCode = string.IsNullOrWhiteSpace(request.PackageCode)
                        ? null
                        : request.PackageCode.Trim(),
                }
            )
        );

    private static string Hash(string value) =>
        Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(value))).ToLowerInvariant();

    private static string ContractHash(
        ProfessionalDisclosure disclosure,
        string intent,
        HireQuote? quote
    ) =>
        Hash(
            JsonSerializer.Serialize(
                new
                {
                    disclosure.ProfessionalType,
                    disclosure.ProjectionVersion,
                    disclosure.DisclosureRevision,
                    disclosure.TermsVersion,
                    Intent = intent,
                    disclosure.DisplayName,
                    disclosure.CustomerRights,
                    disclosure.Limitations,
                    disclosure.AuthorityNeeds,
                    disclosure.EvidencePosture,
                    disclosure.Trial,
                    Quote = quote,
                }
            )
        );

    private static string? NormalizeCoupon(string? couponCode) =>
        string.IsNullOrWhiteSpace(couponCode) ? null : couponCode.Trim().ToUpperInvariant();

    private static bool IsValidCoupon(string? couponCode)
    {
        var normalized = NormalizeCoupon(couponCode);
        return normalized is null
            || normalized.Length <= 64
                && normalized.All(value =>
                    value is >= 'A' and <= 'Z' or >= '0' and <= '9' or '_' or '-'
                );
    }

    private static AcquisitionIntentResponse IntentResponse(
        AcquisitionIntent intent,
        bool replayed
    ) =>
        new(
            intent.AcquisitionIntentId,
            intent.Mode,
            intent.Status,
            intent.ContractDocumentUri,
            intent.ContractHash,
            intent.ExpiresAt,
            replayed,
            intent.ToQuote() is { } quote ? QuoteResponse(quote) : null
        );

    private bool TryGetMembership(out Guid tenantId, out Guid participantId)
    {
        tenantId = Guid.Empty;
        participantId = Guid.Empty;
        if (
            !HttpContext.Items.TryGetValue(
                CustomerMembershipMiddleware.MembershipItem,
                out var value
            ) || value is not CustomerWorkspaceMembership membership
        )
            return false;
        tenantId = membership.TenantId;
        participantId = membership.AccountId;
        return tenantId != Guid.Empty && participantId != Guid.Empty;
    }
}
