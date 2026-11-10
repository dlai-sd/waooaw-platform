using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class WhatsAppCapabilityGateTests
{
    private static readonly DateTimeOffset Now = new(2026, 11, 2, 9, 0, 0, TimeSpan.Zero);
    private static readonly Guid Tenant = Guid.NewGuid();
    private static readonly string Digest = "sha256:" + new string('a', 64);
    private static readonly string Recipient = new('b', 64);

    [Fact]
    public void MissingConfigurationDoesNotBecomeReadyFromCredentialPresence()
    {
        var options = new WhatsAppCapabilityOptions { ProviderAvailable = true };
        var gate = Gate(options);
        Assert.Equal("BLOCKED", gate.Evaluate(Now).State);
        Assert.Throws<WhatsAppCapabilityUnavailableException>(() => gate.RequireActive(Now));
    }

    [Fact]
    public void QualifiedConfigurationStaysInactiveWithoutSeparateActivation()
    {
        var options = Configuration();
        options.Authority = null;
        Assert.Equal("READY_INACTIVE", Gate(options).Evaluate(Now).State);
        options.ProviderAvailable = false;
        Assert.Equal("UNAVAILABLE", Gate(options).Evaluate(Now).State);
    }

    [Theory]
    [InlineData(-1, false)]
    [InlineData(0, true)]
    [InlineData(59, true)]
    [InlineData(60, false)]
    [InlineData(61, false)]
    public void ActivationStartsInclusivelyAndExpiresExclusively(int seconds, bool active)
    {
        var gate = Gate(Configuration());
        var instant = Now.AddSeconds(seconds);
        Assert.Equal(active ? "ACTIVE" : "READY_INACTIVE", gate.Evaluate(instant).State);
        if (active)
            Assert.Equal(Tenant, gate.RequireActive(instant).TenantId);
        else
            Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
                gate.RequireActive(instant)
            );
    }

    [Fact]
    public void RevocationAndConfigurationChangeImmediatelyFencePreviouslyActiveGate()
    {
        var options = Configuration();
        var gate = Gate(options);
        Assert.Equal("ACTIVE", gate.Evaluate(Now).State);
        options.Revoked = true;
        Assert.Equal("BLOCKED", gate.Evaluate(Now).State);
        options.Revoked = false;
        options.ConfigurationDigest = "sha256:" + new string('c', 64);
        Assert.Equal("BLOCKED", gate.Evaluate(Now).State);
        options.ConfigurationDigest = Digest;
        options.Authority = options.Authority! with { Revoked = true };
        Assert.Equal("BLOCKED", gate.Evaluate(Now).State);
    }

    [Theory]
    [InlineData("uat")]
    [InlineData("production")]
    [InlineData("prod")]
    [InlineData("")]
    public void OtherEnvironmentsCannotActivateThroughDemoAuthority(string environment)
    {
        var options = Configuration();
        options.Environment = environment;
        Assert.Equal("BLOCKED", Gate(options).Evaluate(Now).State);
    }

    [Fact]
    public void RecipientAuthorityCannotCrossTenantOrPhoneBinding()
    {
        var gate = Gate(Configuration());
        gate.RequireRecipient(Tenant, Recipient, Now);
        Assert.Equal(
            "RECIPIENT_DENIED",
            Assert
                .Throws<WhatsAppCapabilityUnavailableException>(() =>
                    gate.RequireRecipient(Guid.NewGuid(), Recipient, Now)
                )
                .ReasonCode
        );
        Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
            gate.RequireRecipient(Tenant, new string('c', 64), Now)
        );
    }

    [Fact]
    public void PublicRecipientAuthorityAcceptsOnlyValidSenderDigestsInsideTheApprovedTenant()
    {
        var options = Configuration();
        options.PublicAdmissionIdentityKeyAvailable = true;
        options.Authority = options.Authority! with
        {
            AllowPublicAdmission = true,
            AllowProvisionalOnboarding = true,
        };
        var gate = Gate(options);
        gate.RequireRecipient(Tenant, new string('c', 64), Now);
        foreach (
            var invalid in new[] { "", new string('c', 63), new string('C', 64), "synthetic-phone" }
        )
            Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
                gate.RequireRecipient(Tenant, invalid, Now)
            );
        Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
            gate.RequireRecipient(Guid.NewGuid(), new string('c', 64), Now)
        );
        options.Authority = options.Authority with { AllowPublicAdmission = false };
        Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
            gate.RequireRecipient(Tenant, new string('c', 64), Now)
        );
    }

    [Fact]
    public void PublicAdmissionRequiresProvisionalOnboardingAndDemoAuthority()
    {
        var options = Configuration();
        options.Authority = options.Authority! with { AllowPublicAdmission = true };
        Assert.Equal("BLOCKED", Gate(options).Evaluate(Now).State);

        options.Authority = options.Authority! with { AllowProvisionalOnboarding = true };
        Assert.Equal("BLOCKED", Gate(options).Evaluate(Now).State);

        options.PublicAdmissionIdentityKeyAvailable = true;
        Assert.Equal("ACTIVE", Gate(options).Evaluate(Now).State);

        options.Authority = options.Authority! with
        {
            Environment = "uat",
            AllowProvisionalOnboarding = true,
        };
        Assert.Equal("BLOCKED", Gate(options).Evaluate(Now).State);
    }

    [Fact]
    public void EveryIndependentAuthorityAndTupleDimensionIsMandatory()
    {
        var valid = Configuration().Authority!;
        var invalid = new[]
        {
            valid with
            {
                ActivationReference = "",
            },
            valid with
            {
                ExternalTrafficReference = "",
            },
            valid with
            {
                ExternalTrafficReference = valid.ActivationReference,
            },
            valid with
            {
                ConsentReference = "",
            },
            valid with
            {
                IncidentOwnerReference = "",
            },
            valid with
            {
                AlertRouteReference = "",
            },
            valid with
            {
                Environment = "uat",
            },
            valid with
            {
                ReleaseDigest = "sha256:" + new string('c', 64),
            },
            valid with
            {
                ConfigurationDigest = "sha256:" + new string('c', 64),
            },
            valid with
            {
                CatalogDigest = "sha256:" + new string('c', 64),
            },
            valid with
            {
                RollbackDigest = "sha256:" + new string('c', 64),
            },
            valid with
            {
                TenantId = Guid.Empty,
            },
            valid with
            {
                RecipientBindingDigest = "not-a-binding",
            },
            valid with
            {
                ExpiresAt = Now,
            },
            valid with
            {
                MaximumMessages = 0,
            },
            valid with
            {
                MaximumMessagesPerMinute = 0,
            },
            valid with
            {
                MaximumMessagesPerMinute = 11,
            },
            valid with
            {
                MaximumSpendInr = 0,
            },
            valid with
            {
                MaximumCostPerMessageInr = 0,
            },
            valid with
            {
                MaximumCostPerMessageInr = 101,
            },
            valid with
            {
                Revoked = true,
            },
        };
        foreach (var authority in invalid)
        {
            var options = Configuration();
            options.Authority = authority;
            Assert.Equal("BLOCKED", Gate(options).Evaluate(Now).State);
        }
    }

    [Fact]
    public void AllRuntimeTupleDigestsAreRequired()
    {
        foreach (var field in new[] { "release", "configuration", "catalog", "rollback" })
        {
            var options = Configuration();
            switch (field)
            {
                case "release":
                    options.ReleaseDigest = "latest";
                    break;
                case "configuration":
                    options.ConfigurationDigest = "";
                    break;
                case "catalog":
                    options.CatalogDigest = new string('a', 64);
                    break;
                case "rollback":
                    options.RollbackDigest = "sha256:" + new string('A', 64);
                    break;
            }
            Assert.Equal("BLOCKED", Gate(options).Evaluate(Now).State);
        }
    }

    private static WhatsAppCapabilityGate Gate(WhatsAppCapabilityOptions options) =>
        new(new StaticOptionsMonitor<WhatsAppCapabilityOptions>(options));

    private static WhatsAppCapabilityOptions Configuration() =>
        new()
        {
            Configured = true,
            ProviderAvailable = true,
            Environment = "demo",
            ReleaseDigest = Digest,
            ConfigurationDigest = Digest,
            CatalogDigest = Digest,
            RollbackDigest = Digest,
            Authority = new()
            {
                ActivationReference = "FA-demo-activation",
                ExternalTrafficReference = "FA-demo-traffic",
                ConsentReference = "consent:demo",
                IncidentOwnerReference = "office:operations",
                AlertRouteReference = "alerts:demo",
                Environment = "demo",
                ReleaseDigest = Digest,
                ConfigurationDigest = Digest,
                CatalogDigest = Digest,
                RollbackDigest = Digest,
                TenantId = Tenant,
                RecipientBindingDigest = Recipient,
                StartsAt = Now,
                ExpiresAt = Now.AddMinutes(1),
                MaximumMessages = 10,
                MaximumMessagesPerMinute = 10,
                MaximumSpendInr = 100,
                MaximumCostPerMessageInr = 10,
            },
        };
}
