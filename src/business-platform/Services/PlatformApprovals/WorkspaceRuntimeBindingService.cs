// Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R007
// Constitutional basis: C-005, C-023, C-026, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services.PlatformApprovals;

/// <summary>
/// Gives a workspace's admission the record the operational mandate resolver reads: one revision holding the package's
/// admission content, and one runtime binding per skill. Both are written once, append-only, from the package the Founder
/// approved; running it again changes nothing.
/// </summary>
public sealed class WorkspaceRuntimeBindingService(
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
    IAgentPackageSource packages,
    TimeProvider clock
)
{
    /// <summary>Returns false when the platform ships no package for this exact professional version.</summary>
    public async Task<bool> EnsureAsync(
        Guid tenantId,
        Guid admissionId,
        Guid ownerSubjectId,
        string professionalType,
        string professionalVersion,
        CancellationToken ct
    )
    {
        var package = packages.Find(professionalType, professionalVersion);
        if (package is null)
            return false;
        for (var attempt = 0; attempt < 2; attempt++)
        {
            await using var db = await dbFactory.CreateDbContextAsync(ct);
            var admission = await db.AgentAdmissions.SingleOrDefaultAsync(
                value => value.TenantId == tenantId && value.AdmissionId == admissionId,
                ct
            );
            if (admission is null)
                return false;
            try
            {
                var revision = admission.CurrentRevision;
                if (revision < 1)
                {
                    revision = 1;
                    db.AgentAdmissionRevisions.Add(
                        new AgentAdmissionRevision
                        {
                            TenantId = tenantId,
                            AdmissionId = admissionId,
                            Revision = revision,
                            ContractSchemaVersion = package.ContractSchemaVersion,
                            AdmissionContentDigest = package.ContentDigest,
                            AdmissionContentJson = package.ContentJson,
                            ActorSubjectId = ownerSubjectId,
                            CreatedAt = clock.GetUtcNow(),
                        }
                    );
                    admission.CurrentRevision = revision;
                    admission.UpdatedAt = clock.GetUtcNow();
                }
                var existing = await db
                    .AgentSkillRuntimeBindings.AsNoTracking()
                    .Where(value =>
                        value.TenantId == tenantId
                        && value.AdmissionId == admissionId
                        && value.SupersededAt == null
                    )
                    .Select(value => new { value.SkillId, value.SkillVersion })
                    .ToListAsync(ct);
                foreach (var skill in package.Skills)
                {
                    if (
                        existing.Any(value =>
                            value.SkillId == skill.SkillId
                            && value.SkillVersion == skill.SkillVersion
                        )
                    )
                        continue;
                    db.AgentSkillRuntimeBindings.Add(
                        new AgentSkillRuntimeBinding
                        {
                            TenantId = tenantId,
                            AdmissionId = admissionId,
                            SkillId = skill.SkillId,
                            SkillVersion = skill.SkillVersion,
                            ReleaseSequence = revision,
                            SpecificationRevision = package.SpecificationRevision,
                            SpecificationDigest = package.SpecificationDigest,
                            PromptVersion = skill.PromptVersion,
                            PromptDigest = skill.PromptDigest,
                            InputSchemaDigest = skill.InputSchemaDigest,
                            OutputSchemaDigest = skill.OutputSchemaDigest,
                            ActivatedAt = clock.GetUtcNow(),
                        }
                    );
                }
                await db.SaveChangesAsync(ct);
                return true;
            }
            catch (DbUpdateException) when (attempt == 0)
            {
                // A concurrent request wrote the same rows; read them on the next pass.
            }
        }
        return false;
    }
}
