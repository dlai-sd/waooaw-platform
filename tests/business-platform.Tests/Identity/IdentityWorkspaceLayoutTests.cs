// Implements: WC-121 Component 01 Identity-owned workspace layout evidence
// constitutional_basis: C-005, C-007, C-023, C-026, C-059

using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class IdentityWorkspaceLayoutTests
{
    [Fact]
    public async Task ControllerValidatesPersistsAndReportsReplayAndVersionConflicts()
    {
        const string actorSubject = "workspace-layout-controller";
        var tenantId = Guid.NewGuid();
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        await SeedCompletedAccountAsync(factory, $"keycloak-local\u001f{actorSubject}");
        var controller = IdentityTestHelpers.CreateController(
            factory,
            subject: actorSubject,
            tenantId: tenantId.ToString(),
            identityProvider: "google",
            email: "workspace-layout@example.com",
            emailVerified: true,
            customerRoles: ["OWNER"]
        );

        Assert.IsType<OkObjectResult>(
            await controller.GetWorkspaceLayoutPreferencesAsync(CancellationToken.None)
        );
        foreach (
            var invalidRequest in new ReplaceWorkspaceLayoutPreferencesRequest[]
            {
                new(-1, "VISIBLE", "VISIBLE", 50, false),
                new(0, "INVALID", "VISIBLE", 50, false),
                new(0, "VISIBLE", "INVALID", 50, false),
                new(0, "VISIBLE", "VISIBLE", 34, false),
                new(0, "VISIBLE", "VISIBLE", 76, false),
            }
        )
        {
            var invalid = Assert.IsType<ObjectResult>(
                await controller.ReplaceWorkspaceLayoutPreferencesAsync(
                    invalidRequest,
                    CancellationToken.None
                )
            );
            Assert.Equal(400, invalid.StatusCode);
        }

        var updated = Assert.IsType<OkObjectResult>(
            await controller.ReplaceWorkspaceLayoutPreferencesAsync(
                new(0, "COLLAPSED", "VISIBLE", 55, true),
                CancellationToken.None
            )
        );
        Assert.NotNull(updated.Value);

        var divergent = Assert.IsType<ObjectResult>(
            await controller.ReplaceWorkspaceLayoutPreferencesAsync(
                new(1, "VISIBLE", "COLLAPSED", 45, false),
                CancellationToken.None
            )
        );
        Assert.Equal(409, divergent.StatusCode);

        IdentityTestHelpers.RefreshIdempotencyKey(controller);
        var stale = Assert.IsType<ObjectResult>(
            await controller.ReplaceWorkspaceLayoutPreferencesAsync(
                new(0, "VISIBLE", "VISIBLE", 50, false),
                CancellationToken.None
            )
        );
        Assert.Equal(409, stale.StatusCode);
    }

    [Fact]
    public async Task ControllerFailsClosedWithoutSessionOrCompletedAccount()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var withoutSession = IdentityTestHelpers.CreateController(
            factory,
            subject: "workspace-layout-no-session"
        );
        var sessionError = await withoutSession.GetWorkspaceLayoutPreferencesAsync(
            CancellationToken.None
        );
        Assert.IsAssignableFrom<ObjectResult>(sessionError);
        var replaceSessionError = Assert.IsType<ObjectResult>(
            await withoutSession.ReplaceWorkspaceLayoutPreferencesAsync(
                new(0, "VISIBLE", "VISIBLE", 50, false),
                CancellationToken.None
            )
        );
        Assert.Equal(401, replaceSessionError.StatusCode);

        var tenantId = Guid.NewGuid();
        var withoutAccount = IdentityTestHelpers.CreateController(
            factory,
            subject: "workspace-layout-no-account",
            tenantId: tenantId.ToString(),
            identityProvider: "google",
            email: "missing-workspace-layout@example.com",
            emailVerified: true,
            customerRoles: ["OWNER"]
        );
        var notFound = Assert.IsType<ObjectResult>(
            await withoutAccount.GetWorkspaceLayoutPreferencesAsync(CancellationToken.None)
        );
        Assert.Equal(404, notFound.StatusCode);
    }

    [Fact]
    public async Task ReplaceIsVersionedReplayableAndPresentationOnly()
    {
        const string actorSubject = "workspace-layout-owner";
        var tenantId = Guid.NewGuid();
        var idempotencyKey = Guid.NewGuid();
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        await SeedCompletedAccountAsync(factory, actorSubject);
        var service = IdentityTestHelpers.CreateService(factory);

        var updated = await service.ReplaceWorkspaceLayoutPreferencesAsync(
            actorSubject,
            tenantId,
            idempotencyKey,
            "workspace-layout-request-hash",
            0,
            "COMPACT",
            "EXPANDED",
            55,
            true,
            CancellationToken.None
        );
        var replay = await service.ReplaceWorkspaceLayoutPreferencesAsync(
            actorSubject,
            tenantId,
            idempotencyKey,
            "workspace-layout-request-hash",
            0,
            "COMPACT",
            "EXPANDED",
            55,
            true,
            CancellationToken.None
        );

        Assert.Equal(1, updated.PreferenceVersion);
        Assert.Equal(updated, replay);
        Assert.Equal("COMPACT", replay.NavigationVisibility);
        Assert.Equal("EXPANDED", replay.ProgressVisibility);
        Assert.Equal(55, replay.ConversationWidthPercent);
        Assert.True(replay.ReduceMotion);
        await using var db = factory.CreateDbContext();
        Assert.Single(await db.CustomerPortalPreferences.ToListAsync());
        Assert.Single(await db.IdempotencyLedger.ToListAsync());
        Assert.Single(await db.Registrations.ToListAsync());
    }

    [Fact]
    public async Task ReplaceRejectsStaleVersionAndDivergentReplay()
    {
        const string actorSubject = "workspace-layout-conflict";
        var tenantId = Guid.NewGuid();
        var idempotencyKey = Guid.NewGuid();
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        await SeedCompletedAccountAsync(factory, actorSubject);
        var service = IdentityTestHelpers.CreateService(factory);

        await service.ReplaceWorkspaceLayoutPreferencesAsync(
            actorSubject,
            tenantId,
            idempotencyKey,
            "workspace-layout-request-hash",
            0,
            "EXPANDED",
            "EXPANDED",
            45,
            false,
            CancellationToken.None
        );

        await Assert.ThrowsAsync<IdentityIdempotencyConflict>(() =>
            service.ReplaceWorkspaceLayoutPreferencesAsync(
                actorSubject,
                tenantId,
                idempotencyKey,
                "different-request-hash",
                1,
                "COMPACT",
                "COMPACT",
                50,
                true,
                CancellationToken.None
            )
        );
        await Assert.ThrowsAsync<IdentityPreferenceVersionConflictException>(() =>
            service.ReplaceWorkspaceLayoutPreferencesAsync(
                actorSubject,
                tenantId,
                Guid.NewGuid(),
                "new-request-hash",
                0,
                "COMPACT",
                "COMPACT",
                50,
                true,
                CancellationToken.None
            )
        );
    }

    private static async Task SeedCompletedAccountAsync(
        IDbContextFactory<IdentityDbContext> factory,
        string actorSubject
    )
    {
        await using var db = await factory.CreateDbContextAsync();
        db.Registrations.Add(
            new IdentityRegistrationRecord
            {
                ActorSubject = actorSubject,
                State = IdentityRegistrationState.Completed,
                AccountId = Guid.NewGuid(),
            }
        );
        await db.SaveChangesAsync();
    }
}
