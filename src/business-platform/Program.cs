// Implements: architecture/reference/components/business-platform.md § Tenant Isolation
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-03
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-08
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-13
// constitutional_basis: C-005, C-023, C-026, C-059
using System.Security.Cryptography.X509Certificates;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.Tokens;
using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using Temporalio.Extensions.Hosting;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Middleware;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.AcceptanceSynthetic;
using Waooaw.BusinessPlatform.Services.PlatformAccess;
using Waooaw.BusinessPlatform.Services.Spend;
using Waooaw.BusinessPlatform.Services.Workbench;
using Waooaw.BusinessPlatform.Workflows;
using Waooaw.ConstitutionalEngine.Grpc;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.ConfigureKestrel(options => options.Limits.MaxRequestLineSize = 65536);

var dataProtectionKeysPath = builder.Configuration["DataProtection:KeysPath"];
var dataProtectionCertificatePath = builder.Configuration["DataProtection:CertificatePath"];
var dataProtectionCertificatePassword = builder.Configuration["DataProtection:CertificatePassword"];
if (!string.IsNullOrWhiteSpace(dataProtectionKeysPath))
{
    if (
        string.IsNullOrWhiteSpace(dataProtectionCertificatePath)
        || string.IsNullOrWhiteSpace(dataProtectionCertificatePassword)
    )
    {
        throw new InvalidOperationException(
            "Persistent Data Protection requires a certificate path and password."
        );
    }

    var certificate = X509CertificateLoader.LoadPkcs12FromFile(
        dataProtectionCertificatePath,
        dataProtectionCertificatePassword
    );
    builder
        .Services.AddDataProtection()
        .SetApplicationName("WAOOAW.BusinessPlatform")
        .PersistKeysToFileSystem(new DirectoryInfo(dataProtectionKeysPath))
        .ProtectKeysWithCertificate(certificate);
}

var otlpEndpoint =
    builder.Configuration["OTEL_EXPORTER_OTLP_ENDPOINT"] ?? builder.Configuration["OTLP_ENDPOINT"];
if (Uri.TryCreate(otlpEndpoint, UriKind.Absolute, out var otlpUri))
{
    var serviceRevision = builder.Configuration["SERVICE_REVISION"] ?? "development";
    builder
        .Services.AddOpenTelemetry()
        .ConfigureResource(resource =>
            resource.AddService("waooaw-business-platform", serviceVersion: serviceRevision)
        )
        .WithTracing(tracing =>
            tracing
                .AddAspNetCoreInstrumentation(options =>
                    options.Filter = context =>
                        !context.Request.Path.StartsWithSegments(
                            "/api/v1/channels/whatsapp/webhook"
                        )
                )
                .AddHttpClientInstrumentation(options =>
                    options.EnrichWithHttpRequestMessage = JourneyHttpTelemetry.ScrubRequestUrl
                )
                .AddSource("waooaw.business-platform.*")
                .AddOtlpExporter(options => options.Endpoint = otlpUri)
        )
        .WithMetrics(metrics =>
            metrics
                .AddMeter(Waooaw.BusinessPlatform.Services.Visitor.VisitorTelemetry.MeterName)
                .AddMeter(SyntheticAcceptanceTelemetry.MeterName)
                .AddOtlpExporter(options => options.Endpoint = otlpUri)
        );
}

// ── REST + OpenAPI ────────────────────────────────────────────────────────────
builder
    .Services.AddControllers()
    .AddJsonOptions(options =>
    {
        options.JsonSerializerOptions.UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow;
        options.JsonSerializerOptions.Converters.Add(new JsonSchemaInt32Converter());
        options.JsonSerializerOptions.Converters.Add(new JsonSchemaInt64Converter());
    })
    .ConfigureApiBehaviorOptions(options =>
    {
        var defaultFactory = options.InvalidModelStateResponseFactory;
        options.InvalidModelStateResponseFactory = context =>
        {
            var path = context.HttpContext.Request.Path;
            if (path.StartsWithSegments("/api/v1/identity"))
                return IdentityProblemResponses.Create(
                    StatusCodes.Status400BadRequest,
                    "IDENTITY_REQUEST_INVALID",
                    "The identity request is invalid."
                );

            var code =
                path.StartsWithSegments("/api/v1/customer-portal/interactions/portal/messages")
                || path.Value?.Contains("/conversation", StringComparison.Ordinal) == true
                    ? "CONVERSATION_REQUEST_INVALID"
                : path.Value?.Contains("/workspace", StringComparison.Ordinal) == true
                || path.Value?.Contains("/evaluation", StringComparison.Ordinal) == true
                    ? "RELATIONSHIP_WORKSPACE_REQUEST_INVALID"
                : path.Value?.Contains("/admission/", StringComparison.Ordinal) == true
                    ? "ADMISSION_REQUEST_INVALID"
                : null;
            if (code is null)
                return defaultFactory(context);

            return new ObjectResult(
                new
                {
                    type = $"https://waooaw.com/problems/{code.ToLowerInvariant().Replace('_', '-')}",
                    title = "The request is invalid",
                    status = StatusCodes.Status400BadRequest,
                    code,
                    correlationId = Guid.NewGuid(),
                }
            )
            {
                StatusCode = StatusCodes.Status400BadRequest,
                ContentTypes = { "application/problem+json" },
            };
        };
    });
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
builder
    .Services.AddHealthChecks()
    .AddCheck<IdentitySchemaHealthCheck>("identity-schema", tags: ["ready"])
    .AddCheck<ConversationCursorHealthCheck>("conversation-cursor", tags: ["ready"])
    .AddCheck<WorkloadCredentialHealthCheck>(
        "workload-credentials",
        tags: [WorkloadCredentialHealthCheck.DetailTag]
    );

// ── JWT Authentication — Keycloak (ADR-003, C-026) ───────────────────────────
// tenant_id extracted in TenantIsolationMiddleware after token is validated.
// Invalid token → 401. Missing tenant_id claim → 403 (enforced in middleware).
builder
    .Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.Authority =
            builder.Configuration["Keycloak:Authority"]
            ?? builder.Configuration["IdentityEnvironment:Keycloak:Issuer"]
            ?? throw new InvalidOperationException(
                "Keycloak:Authority is required (C-026 — tenant isolation cannot function without JWT issuer)."
            );
        options.Audience =
            builder.Configuration["IdentityEnvironment:Keycloak:Audience"]
            ?? builder.Configuration["Keycloak:Audience"]
            ?? "waooaw-platform";
        options.RequireHttpsMetadata =
            builder.Configuration.GetValue<bool?>("Keycloak:RequireHttpsMetadata")
            ?? !builder.Environment.IsDevelopment();

        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidAlgorithms = [SecurityAlgorithms.RsaSha256],
            // Clock skew: tight on purpose — stale tokens violate tenant contract guarantees
            ClockSkew = TimeSpan.FromSeconds(30),
        };

        options.Events = new JwtBearerEvents
        {
            OnChallenge = async ctx =>
            {
                // Log every rejected token challenge for constitutional audit visibility
                var logger = ctx.HttpContext.RequestServices.GetRequiredService<ILogger<Program>>();
                logger.LogWarning(
                    "JWT challenge fired: path={Path} (C-026 enforcement)",
                    ctx.Request.Path
                );

                ctx.HandleResponse();
                ctx.Response.StatusCode = StatusCodes.Status401Unauthorized;
                await ctx.Response.WriteAsJsonAsync(
                    new
                    {
                        type = "https://waooaw.com/errors/identity/identity-session-required",
                        title = "IDENTITY_SESSION_REQUIRED",
                        status = StatusCodes.Status401Unauthorized,
                        detail = "A valid Keycloak-issued Bearer token is required.",
                        code = "IDENTITY_SESSION_REQUIRED",
                        correlationId = Guid.NewGuid(),
                    },
                    options: null,
                    contentType: "application/problem+json",
                    cancellationToken: ctx.HttpContext.RequestAborted
                );
            },
        };
    });

builder.Services.AddAuthorization(options =>
{
    options.AddPolicy("InternalService", policy => policy.RequireClaim("client_type", "service"));
});

// ── Tenant Isolation — C-005, C-026, ADR-003 ─────────────────────────────────
// Registers TenantIsolationMiddleware + TenantDbConnectionInterceptor.
// Interceptor sets: SET LOCAL app.current_tenant_id = '{id}' before every DB command
// so PostgreSQL RLS policies automatically scope all queries to the caller's tenant.
builder.Services.AddTenantIsolation();

// ── HttpContextAccessor — required by TenantDbConnectionInterceptor ──────────────
builder.Services.AddHttpContextAccessor();
builder.Services.AddSingleton<IProfessionalCatalog, ProfessionalCatalog>();

var credentialOptions = WorkloadCredentialOptions.From(builder.Configuration);
var workloadCredentials = builder.Configuration["WAOOAW_WORKLOAD_CREDENTIALS"];
WorkloadIdentityClient? workloadIdentity = null;
var ownerLinks = new OwnerLinkState();
builder.Services.AddSingleton(ownerLinks);
var prWorkspaceBaseUrl = builder.Configuration["ProfessionalRuntime:RelationshipWorkspaceBaseUrl"];
var wbeWorkspaceBaseUrl = builder.Configuration["BillingEngine:RelationshipWorkspaceBaseUrl"];
if (credentialOptions.IsKeyVault)
{
    // Gateways register now and report unavailable until the first bundle verifies; the vault never gates startup.
    workloadIdentity = WorkloadIdentityClient.CreateReloadable(
        new WorkloadCredentialSettings(credentialOptions.Workload, credentialOptions.TrustDomain)
    );
    builder.Services.AddSingleton(workloadIdentity);
    builder.Services.AddSingleton(credentialOptions);
    builder.Services.AddSingleton<IWorkloadCredentialReader>(
        new KeyVaultWorkloadCredentialReader(
            new HttpClient { Timeout = TimeSpan.FromSeconds(10) },
            builder.Configuration,
            credentialOptions
        )
    );
    var ownerTargets = new List<OwnerLinkTarget>
    {
        new(
            "billing",
            "billing-engine",
            Uri.TryCreate(wbeWorkspaceBaseUrl, UriKind.Absolute, out var billingLinkUri)
                ? billingLinkUri
                : null
        ),
        new(
            "professional-runtime",
            "professional-runtime",
            Uri.TryCreate(prWorkspaceBaseUrl, UriKind.Absolute, out var runtimeLinkUri)
                ? runtimeLinkUri
                : null
        ),
    };
    foreach (var owner in ownerTargets)
        ownerLinks.Set(
            owner.Owner,
            owner.BaseUrl is null ? OwnerLinkStatus.Unconfigured : OwnerLinkStatus.Unavailable
        );
    builder.Services.AddSingleton(new OwnerLinkProber(workloadIdentity, ownerLinks, ownerTargets));
    builder.Services.AddHostedService<WorkloadCredentialRefresher>();
}
else if (!string.IsNullOrWhiteSpace(workloadCredentials))
{
    workloadIdentity = WorkloadIdentityClient.Load(workloadCredentials);
    builder.Services.AddSingleton(workloadIdentity);
}
var workloadInboundPort = WorkloadInboundListener.Configure(
    builder,
    credentialOptions,
    workloadIdentity
);
if (credentialOptions.IsKeyVault && workloadIdentity is not null)
    builder.Services.AddSingleton<Waooaw.WorkloadIdentity.IInboundCredentialSource>(
        new WorkloadInboundCredentialSource(workloadIdentity, TimeProvider.System)
    );
T Guarded<T>(T real, T unavailable)
    where T : class =>
    credentialOptions.IsKeyVault && workloadIdentity is not null
        ? OwnerGatewayGuard<T>.Create(real, unavailable, workloadIdentity)
        : real;
if (
    workloadIdentity is not null
    && Uri.TryCreate(prWorkspaceBaseUrl, UriKind.Absolute, out var prWorkspaceUri)
    && Uri.TryCreate(wbeWorkspaceBaseUrl, UriKind.Absolute, out var wbeWorkspaceUri)
)
{
    builder.Services.AddSingleton(
        Guarded<IRelationshipWorkspaceOwnerGateway>(
            new AuthenticatedRelationshipWorkspaceOwnerGateway(
                workloadIdentity,
                prWorkspaceUri,
                wbeWorkspaceUri
            ),
            new UnconfiguredRelationshipWorkspaceOwnerGateway()
        )
    );
    builder.Services.AddSingleton(services =>
        Guarded<IRelationshipTrialOwnerGateway>(
            new HttpRelationshipTrialOwnerGateway(
                services.GetRequiredService<IHttpClientFactory>(),
                workloadIdentity,
                prWorkspaceUri
            ),
            new UnconfiguredRelationshipTrialOwnerGateway()
        )
    );
}
else
{
    builder.Services.AddSingleton<
        IRelationshipWorkspaceOwnerGateway,
        UnconfiguredRelationshipWorkspaceOwnerGateway
    >();
    builder.Services.AddSingleton<
        IRelationshipTrialOwnerGateway,
        UnconfiguredRelationshipTrialOwnerGateway
    >();
}

// ── WBE (billing-engine) HttpClient — used by SubscriptionsController + Temporal activities ──
var wbeBaseUrl = builder.Configuration["BillingEngine:BaseUrl"] ?? "http://billing-engine:8140";
builder.Services.AddHttpClient(
    "WBE",
    client =>
    {
        client.BaseAddress = new Uri(wbeBaseUrl);
        client.Timeout = TimeSpan.FromSeconds(30);
        var opsToken = builder.Configuration["BillingEngine:OpsAuthToken"];
        if (!string.IsNullOrWhiteSpace(opsToken))
            client.DefaultRequestHeaders.Add("X-Ops-Token", opsToken);
    }
);

// ── Temporal worker — trial expiry saga (ADR-015, conditional on config) ─────
// Worker is skipped when Temporal:Host is not configured (e.g., in unit tests).
var temporalHost = builder.Configuration["Temporal:Host"];
if (!string.IsNullOrWhiteSpace(temporalHost))
{
    builder.Services.AddTemporalClient(opts => opts.TargetHost = temporalHost);
    builder.Services.AddSingleton<IActivationWorkflowStarter, TemporalActivationWorkflowStarter>();
    builder.Services.AddScoped<ActivationWorkflowDispatchService>();
    builder.Services.AddSingleton<TrialExpiryActivities>();
    builder.Services.AddScoped<ActivationActivities>();
    builder
        .Services.AddHostedTemporalWorker("bp-trial-worker")
        .AddWorkflow<TrialExpiryWorkflow>()
        .AddWorkflow<ActivationWorkflow>()
        .AddScopedActivities<ActivationActivities>()
        .AddSingletonActivities<TrialExpiryActivities>();
}

// ── Payload Store DbContext — DPDPA Right-to-Erasure (ADR-044) ───────────────
var payloadStoreConn =
    builder.Configuration.GetConnectionString("PayloadStore")
    ?? builder.Configuration.GetConnectionString("DefaultConnection")
    ?? "Host=localhost;Database=waooaw_bp;Username=bp_app;";
builder.Services.AddDbContextFactory<Waooaw.BusinessPlatform.Infrastructure.PayloadStoreDbContext>(
    opts => opts.UseNpgsql(payloadStoreConn)
);

// ── Provider Registry DbContext — runtime provider routing table (ADR-042) ───
var providerRegistryConn =
    builder.Configuration.GetConnectionString("ProviderRegistry")
    ?? builder.Configuration.GetConnectionString("DefaultConnection")
    ?? "Host=localhost;Database=waooaw_bp;Username=bp_app;";
builder.Services.AddDbContextFactory<Waooaw.BusinessPlatform.Infrastructure.ProviderRegistryDbContext>(
    opts => opts.UseNpgsql(providerRegistryConn)
);

// ── Founder provider credential registry (WC-148) — Key Vault writes stay unavailable until VaultUrl is set ──
var providerCredentialOptions = ProviderCredentialOptions.From(builder.Configuration);
builder.Services.AddSingleton(providerCredentialOptions);
if (providerCredentialOptions.VaultUri is not null)
{
    var keyVault = new KeyVaultProviderSecretStore(
        new HttpClient { Timeout = TimeSpan.FromSeconds(10) },
        builder.Configuration,
        providerCredentialOptions
    );
    builder.Services.AddSingleton<ISecretVault>(keyVault);
    builder.Services.AddSingleton<IProviderSecretStore>(keyVault);
}
else
{
    var unconfiguredVault = new UnconfiguredProviderSecretStore();
    builder.Services.AddSingleton<ISecretVault>(unconfiguredVault);
    builder.Services.AddSingleton<IProviderSecretStore>(unconfiguredVault);
}
builder.Services.AddSingleton<IProviderCredentialTester, ProviderCredentialTester>();
builder.Services.AddSingleton<IProviderCredentialAdminService, ProviderCredentialAdminService>();
if (
    workloadIdentity is not null
    && Uri.TryCreate(
        builder.Configuration["ProviderProbe:BaseUrl"],
        UriKind.Absolute,
        out var providerProbeUri
    )
)
    builder.Services.AddSingleton<IProviderProbeGateway>(
        Guarded<IProviderProbeGateway>(
            new AuthenticatedProviderProbeGateway(workloadIdentity, providerProbeUri),
            new UnconfiguredProviderProbeGateway()
        )
    );
else
    builder.Services.AddSingleton<IProviderProbeGateway, UnconfiguredProviderProbeGateway>();
builder.Services.AddSingleton<IProviderGenerationProbe, ProviderGenerationProbe>();

// ── Customer provider connections (WC-149) — Page tokens live only in Key Vault under customer-connection-* ──
var customerConnectionsConn =
    builder.Configuration.GetConnectionString("CustomerConnections")
    ?? builder.Configuration.GetConnectionString("DefaultConnection")
    ?? "Host=localhost;Database=waooaw_bp;Username=business_app;";
builder.Services.AddDbContextFactory<CustomerConnectionsDbContext>(opts =>
    opts.UseNpgsql(customerConnectionsConn)
);
var metaConnectionOptions = MetaConnectionOptions.From(builder.Configuration);
builder.Services.AddSingleton(metaConnectionOptions);
builder.Services.AddSingleton<IMetaGraphClient>(
    new MetaGraphClient(
        new HttpClient(new HttpClientHandler { AllowAutoRedirect = false })
        {
            Timeout = TimeSpan.FromSeconds(15),
        },
        metaConnectionOptions
    )
);
builder.Services.AddSingleton<IProviderConnectionService, ProviderConnectionService>();

// ── Skill Catalog DbContext — ADR-043 §2 ─────────────────────────────────────
var skillCatalogConn =
    builder.Configuration.GetConnectionString("SkillCatalog")
    ?? builder.Configuration.GetConnectionString("DefaultConnection")
    ?? "Host=localhost;Database=waooaw_bp;Username=bp_app;";
builder.Services.AddDbContextFactory<Waooaw.BusinessPlatform.Infrastructure.SkillCatalogDbContext>(
    opts => opts.UseNpgsql(skillCatalogConn)
);

// ── Employment Relationship aggregate — GOAL-005 D-03 / WC-057 ────────────
var employmentRelationshipConn =
    builder.Configuration.GetConnectionString("EmploymentRelationship")
    ?? builder.Configuration.GetConnectionString("DefaultConnection")
    ?? "Host=localhost;Database=waooaw_bp;Username=business_app;";
builder.Services.AddDbContextFactory<EmploymentRelationshipDbContext>(
    (services, options) =>
        options
            .UseNpgsql(employmentRelationshipConn)
            .AddInterceptors(services.GetRequiredService<TenantDbConnectionInterceptor>())
);
builder.Services.AddScoped<IRelationshipConstitutionalGateway, RelationshipConstitutionalGateway>();
builder.Services.AddSingleton<AgentAdmissionValidator>();
builder.Services.AddScoped<AgentAdmissionService>();
builder.Services.AddScoped<EmploymentRelationshipService>();
builder.Services.AddScoped<MyAgentsSelectionService>();
builder.Services.AddSingleton(TimeProvider.System);
builder.Services.AddScoped<
    IRelationshipEmergencyStopGateway,
    GrpcRelationshipEmergencyStopGateway
>();
builder.Services.AddScoped<RelationshipEmergencyStopService>();
builder.Services.AddScoped<RelationshipConfigurationService>();
builder.Services.AddScoped<CustomerAlertService>();
builder.Services.AddScoped<EmploymentContractService>();
builder.Services.AddScoped<EmploymentContractAcceptanceService>();
builder.Services.AddScoped<IRelationshipPaymentGateway, HttpRelationshipPaymentGateway>();
builder.Services.AddScoped<RelationshipPaymentService>();
if (
    workloadIdentity is not null
    && Uri.TryCreate(wbeWorkspaceBaseUrl, UriKind.Absolute, out var activationWbeUri)
)
    builder.Services.AddSingleton(
        Guarded<IActivationBillingGateway>(
            new AuthenticatedActivationBillingGateway(workloadIdentity, activationWbeUri),
            new UnconfiguredActivationBillingGateway()
        )
    );
else
    builder.Services.AddSingleton<
        IActivationBillingGateway,
        UnconfiguredActivationBillingGateway
    >();
if (
    workloadIdentity is not null
    && Uri.TryCreate(wbeWorkspaceBaseUrl, UriKind.Absolute, out var offeringWbeUri)
)
{
    var offeringGateway = new AuthenticatedOfferingUsageGateway(workloadIdentity, offeringWbeUri);
    var offeringUnavailable = new UnconfiguredOfferingUsageGateway();
    builder.Services.AddSingleton(
        Guarded<IAuthenticatedOfferingUsageGateway>(offeringGateway, offeringUnavailable)
    );
    builder.Services.AddSingleton(
        Guarded<IPlatformAccountGateway>(offeringGateway, offeringUnavailable)
    );
}
else
{
    builder.Services.AddSingleton<
        IAuthenticatedOfferingUsageGateway,
        UnconfiguredOfferingUsageGateway
    >();
    builder.Services.AddSingleton<IPlatformAccountGateway, UnconfiguredOfferingUsageGateway>();
}
if (
    workloadIdentity is not null
    && Uri.TryCreate(wbeWorkspaceBaseUrl, UriKind.Absolute, out var pricingWbeUri)
)
    builder.Services.AddSingleton(
        Guarded<IPricingAdminGateway>(
            new AuthenticatedPricingAdminGateway(workloadIdentity, pricingWbeUri),
            new UnconfiguredPricingAdminGateway()
        )
    );
else
    builder.Services.AddSingleton<IPricingAdminGateway, UnconfiguredPricingAdminGateway>();
builder.Services.Configure<PricingAdminOptions>(
    builder.Configuration.GetSection(PricingAdminOptions.SectionName)
);
builder.Services.AddSingleton<
    IEnvironmentSpendCeilingStore,
    PostgresEnvironmentSpendCeilingStore
>();
builder.Services.AddSingleton<PricingAdminWriteLimiter>();
builder.Services.AddSingleton<PricingAdminService>();
builder.Services.AddScoped<IOfferabilityGuard, PersistentOfferabilityGuard>();
builder.Services.AddScoped<OfferabilityService>();
if (
    workloadIdentity is not null
    && Uri.TryCreate(wbeWorkspaceBaseUrl, UriKind.Absolute, out var offerabilityWbeUri)
)
    builder.Services.AddSingleton(
        Guarded<IOfferabilityOwnerGateway>(
            new AuthenticatedOfferabilityOwnerGateway(workloadIdentity, offerabilityWbeUri),
            new UnconfiguredOfferabilityOwnerGateway()
        )
    );
else
    builder.Services.AddSingleton<
        IOfferabilityOwnerGateway,
        UnconfiguredOfferabilityOwnerGateway
    >();
builder.Services.AddScoped<OfferabilityOrchestrationService>();
builder.Services.AddScoped<ActivationOrchestrationService>();
builder.Services.AddScoped<RelationshipTrialService>();
builder.Services.Configure<WhatsAppJourneyOptions>(builder.Configuration.GetSection("WhatsApp"));
builder.Services.Configure<WhatsAppGuestLimitOptions>(
    builder.Configuration.GetSection(WhatsAppGuestLimitOptions.SectionName)
);
builder.Services.Configure<ProtocolOptions>(
    builder.Configuration.GetSection(ProtocolOptions.SectionName)
);
builder.Services.Configure<PhoneIdentityAdapterOptions>(
    builder.Configuration.GetSection("PhoneIdentity")
);
builder.Services.AddScoped<
    IWhatsAppRegistrationEvidenceGateway,
    WhatsAppRegistrationEvidenceGateway
>();
builder.Services.AddScoped<WhatsAppJourneyService>();
builder.Services.AddScoped<WhatsAppGuestSessionService>();
builder.Services.AddScoped<WhatsAppRelationshipStopAcknowledgementService>();
builder
    .Services.AddOptions<Waooaw.BusinessPlatform.Services.Visitor.VisitorConversationOptions>()
    .Bind(builder.Configuration.GetSection("VisitorConversation"))
    .ValidateOnStart();
builder
    .Services.AddOptions<Waooaw.BusinessPlatform.Services.Visitor.VisitorLeadOptions>()
    .Bind(builder.Configuration.GetSection("VisitorLeads"))
    .ValidateOnStart();
builder.Services.AddSingleton<
    IValidateOptions<Waooaw.BusinessPlatform.Services.Visitor.VisitorConversationOptions>,
    Waooaw.BusinessPlatform.Services.Visitor.VisitorConversationOptionsValidator
>();
builder.Services.AddSingleton<
    IValidateOptions<Waooaw.BusinessPlatform.Services.Visitor.VisitorLeadOptions>,
    Waooaw.BusinessPlatform.Services.Visitor.VisitorLeadOptionsValidator
>();
builder.Services.AddSingleton<Waooaw.BusinessPlatform.Services.Visitor.VisitorTelemetry>();
builder.Services.AddSingleton<
    Waooaw.BusinessPlatform.Services.Visitor.IVisitorContentProvider,
    Waooaw.BusinessPlatform.Services.Visitor.FileVisitorContentProvider
>();
builder.Services.AddSingleton<Waooaw.BusinessPlatform.Services.Visitor.IVisitorKeyRing>(provider =>
{
    var local = provider
        .GetRequiredService<
            IOptionsMonitor<Waooaw.BusinessPlatform.Services.Visitor.VisitorConversationOptions>
        >()
        .CurrentValue.LocalCurrentKeyVersion;
    return string.IsNullOrEmpty(local)
        ? new Waooaw.BusinessPlatform.Services.Visitor.VaultVisitorKeyRing(
            provider.GetRequiredService<WhatsAppKeyVaultCredentials>(),
            provider.GetRequiredService<IOptionsMonitor<WhatsAppProviderOptions>>()
        )
        : new Waooaw.BusinessPlatform.Services.Visitor.ConfigurationVisitorKeyRing(
            provider.GetRequiredService<
                IOptionsMonitor<Waooaw.BusinessPlatform.Services.Visitor.VisitorConversationOptions>
            >()
        );
});
builder.Services.AddSingleton<Waooaw.BusinessPlatform.Services.Visitor.VisitorFieldProtector>();
builder.Services.AddScoped<Waooaw.BusinessPlatform.Services.Visitor.VisitorConversationService>();
builder.Services.AddScoped<Waooaw.BusinessPlatform.Services.Visitor.VisitorLeadPurger>();
builder.Services.AddHostedService<Waooaw.BusinessPlatform.Services.Visitor.VisitorLeadPurgeHostedService>();
builder.Services.AddHostedService<Waooaw.BusinessPlatform.Services.Visitor.VisitorGuestCopyInitializer>();
builder.Services.Configure<ChannelContinuityOptions>(
    builder.Configuration.GetSection("ChannelContinuity")
);
builder.Services.AddScoped<ChannelContinuityService>();
builder.Services.AddScoped<IRelationshipEvidenceGateway, GrpcRelationshipEvidenceGateway>();
builder.Services.Configure<RelationshipEvidenceExportOptions>(
    builder.Configuration.GetSection("RelationshipEvidenceExport")
);
builder.Services.AddScoped<RelationshipEvidenceService>();

var voicePrBaseUrl = builder.Configuration["ProfessionalRuntime:VoiceBaseUrl"];
var voicePrSecret = builder.Configuration["Voice:ProfessionalRuntimeJwtSecret"];
if (
    Uri.TryCreate(voicePrBaseUrl, UriKind.Absolute, out var voicePrUri)
    && !string.IsNullOrWhiteSpace(voicePrSecret)
)
{
    builder.Services.AddHttpClient(
        "VoiceProfessionalRuntime",
        client =>
        {
            client.BaseAddress = voicePrUri;
            client.Timeout = TimeSpan.FromSeconds(15);
        }
    );
    builder.Services.AddScoped<IVoiceTranscriptionGateway, HttpVoiceTranscriptionGateway>();
}
else
{
    builder.Services.AddScoped<IVoiceTranscriptionGateway, UnconfiguredVoiceTranscriptionGateway>();
}

// ── Identity Boundary — WC-034 F2 (identity-boundary.md) ─────────────────
// Pre-account registration paths use actor subject (JWT sub); no tenant_id required.
// Account-link and mobile-verification paths require full tenant JWT.
var identityConn =
    builder.Configuration.GetConnectionString("Identity")
    ?? builder.Configuration.GetConnectionString("DefaultConnection")
    ?? "Host=localhost;Database=waooaw_bp;Username=business_app;";
if (new Npgsql.NpgsqlConnectionStringBuilder(identityConn).NoResetOnClose)
    throw new InvalidOperationException("Identity connections require pool reset on close.");
builder.Services.AddDbContextFactory<Waooaw.BusinessPlatform.Infrastructure.IdentityDbContext>(
    options => options.UseNpgsql(identityConn)
);
builder
    .Services.AddOptions<IdentityBrokerReadOptions>()
    .Bind(
        builder.Configuration.GetSection(IdentityBrokerReadOptions.SectionName),
        options => options.ErrorOnUnknownConfiguration = true
    )
    .Validate(
        options => !options.Enabled || options.IsConfigured,
        "Enabled customer identity requires explicit approved private broker-read configuration."
    )
    .ValidateOnStart();
builder
    .Services.AddHttpClient<VerifiedIdentityProofAdapter>(client =>
        client.Timeout = TimeSpan.FromSeconds(10)
    )
    .ConfigurePrimaryHttpMessageHandler(() =>
        new HttpClientHandler { AllowAutoRedirect = false, UseCookies = false }
    )
    .RemoveAllLoggers();
builder
    .Services.AddOptions<IdentityLifecycleWriterOptions>()
    .Bind(
        builder.Configuration.GetSection(IdentityLifecycleWriterOptions.SectionName),
        options => options.ErrorOnUnknownConfiguration = true
    )
    .Validate(
        options => !options.Enabled || options.IsConfigured,
        "Enabled identity lifecycle writer requires the accepted private Keycloak writer configuration."
    )
    .ValidateOnStart();
builder
    .Services.AddHttpClient<IKeycloakIdentityLifecycleWriter, KeycloakIdentityLifecycleWriter>(
        client => client.Timeout = TimeSpan.FromSeconds(10)
    )
    .ConfigurePrimaryHttpMessageHandler(() =>
        new HttpClientHandler { AllowAutoRedirect = false, UseCookies = false }
    )
    .RemoveAllLoggers();
builder.Services.AddScoped<CustomerIdentityJourneyService>();
builder.Services.Configure<Waooaw.BusinessPlatform.Services.IdentityHmacOptions>(
    builder.Configuration.GetSection("Identity:Hmac")
);
builder.Services.AddSingleton<
    IValidateOptions<IdentityEnvironmentOptions>,
    IdentityEnvironmentOptionsValidator
>();
builder
    .Services.AddOptions<IdentityEnvironmentOptions>()
    .Bind(
        builder.Configuration.GetSection(IdentityEnvironmentOptions.SectionName),
        options => options.ErrorOnUnknownConfiguration = true
    )
    .ValidateOnStart();
builder.Services.AddSingleton<IdentityProviderProjectionService>();
var localIdentityVerificationEnabled = builder.Configuration.GetValue<bool>(
    "IdentityVerification:LocalDispatchEnabled"
);
if (localIdentityVerificationEnabled && !builder.Environment.IsDevelopment())
    throw new InvalidOperationException(
        "Local identity verification dispatch is restricted to Development."
    );
if (localIdentityVerificationEnabled)
    builder.Services.AddSingleton<
        Waooaw.BusinessPlatform.Services.IIdentityVerificationDispatcher,
        Waooaw.BusinessPlatform.Services.LocalIdentityVerificationDispatcher
    >();
else
    builder.Services.AddScoped<
        Waooaw.BusinessPlatform.Services.IIdentityVerificationDispatcher,
        Waooaw.BusinessPlatform.Services.WhatsAppIdentityVerificationDispatcher
    >();
builder.Services.Configure<WhatsAppAuthenticationTemplateOptions>(
    builder.Configuration.GetSection("IdentityVerification:WhatsApp")
);
builder.Services.AddScoped<
    IWhatsAppAuthenticationTemplateVerifier,
    WhatsAppAuthenticationTemplateVerifier
>();
builder.Services.AddScoped<IWhatsAppRegistrationVerificationBudget>(services =>
    services.GetRequiredService<WhatsAppTrafficBudget>()
);
builder.Services.AddScoped<Waooaw.BusinessPlatform.Services.IdentityService>();
builder.Services.AddScoped<IWhatsAppRegistrationRecognition, WhatsAppRegistrationRecognition>();
builder.Services.AddScoped<IWhatsAppAccountLinkConfirmation>(services =>
    services.GetRequiredService<IdentityService>()
);
builder.Services.AddScoped<Waooaw.BusinessPlatform.Services.IdentityLifecycleService>();
builder.Services.AddScoped<
    Waooaw.BusinessPlatform.Services.IIdentityConstitutionalGateway,
    Waooaw.BusinessPlatform.Services.GrpcIdentityConstitutionalGateway
>();
builder.Services.AddScoped<Waooaw.BusinessPlatform.Services.IdentitySecurityEventService>();
builder.Services.Configure<Waooaw.BusinessPlatform.Controllers.IdentitySecurityEventIngestOptions>(
    builder.Configuration.GetSection(
        Waooaw.BusinessPlatform.Controllers.IdentitySecurityEventIngestOptions.SectionName
    )
);

// ── Conversation Core — WC-034 F3 ───────────────────────────────────────────
var conversationConn =
    builder.Configuration.GetConnectionString("Conversation")
    ?? builder.Configuration.GetConnectionString("DefaultConnection")
    ?? "Host=localhost;Database=waooaw_bp;Username=business_app;";
builder.Services.AddDbContextFactory<ConversationStoreDbContext>(
    (services, options) =>
        options
            .UseNpgsql(conversationConn)
            .AddInterceptors(services.GetRequiredService<TenantDbConnectionInterceptor>())
);
builder.Services.AddSingleton<
    IValidateOptions<ConversationCursorOptions>,
    ConversationCursorOptionsValidator
>();
builder
    .Services.AddOptions<ConversationCursorOptions>()
    .Bind(builder.Configuration.GetSection("Conversation"))
    .ValidateOnStart();

// ── Platform access — WC-137: staff roles from stored grants, Founder from configuration ──────────
builder.Services.AddMemoryCache();
builder.Services.AddSingleton<
    IValidateOptions<PlatformAccessOptions>,
    PlatformAccessOptionsValidator
>();
builder
    .Services.AddOptions<PlatformAccessOptions>()
    .Bind(builder.Configuration.GetSection(PlatformAccessOptions.SectionName))
    .ValidateOnStart();
builder.Services.AddSingleton<IPlatformAccessStore, PostgresPlatformAccessStore>();
builder.Services.AddSingleton<IClaimsTransformation, PlatformRoleClaimsTransformation>();
builder.Services.AddHostedService<PlatformFounderBootstrapService>();

// ── Synthetic acceptance tenants — WC-159 / ADR-055: default off, Demo and UAT only ──────────────────
builder.Services.AddSingleton<
    IValidateOptions<AcceptanceSyntheticOptions>,
    AcceptanceSyntheticOptionsValidator
>();
builder
    .Services.AddOptions<AcceptanceSyntheticOptions>()
    .Bind(builder.Configuration.GetSection(AcceptanceSyntheticOptions.SectionName))
    .ValidateOnStart();
builder.Services.AddSingleton<ISyntheticAcceptanceRegistry, PostgresSyntheticAcceptanceRegistry>();
builder.Services.AddSingleton<SyntheticTenantInheritance>();
builder.Services.AddSingleton<ISyntheticDeliveryGate, SyntheticDeliveryGate>();
builder.Services.AddSingleton<
    IValidateOptions<ConversationBatchingOptions>,
    ConversationBatchingOptionsValidator
>();
builder
    .Services.AddOptions<ConversationBatchingOptions>()
    .Bind(
        builder.Configuration.GetSection("ConversationBatching"),
        options => options.ErrorOnUnknownConfiguration = true
    )
    .ValidateOnStart();
builder.Services.AddSingleton<
    IValidateOptions<EnvironmentSpendOptions>,
    EnvironmentSpendOptionsValidator
>();
builder
    .Services.AddOptions<EnvironmentSpendOptions>()
    .Bind(
        builder.Configuration.GetSection(EnvironmentSpendOptions.SectionName),
        options => options.ErrorOnUnknownConfiguration = true
    )
    .ValidateOnStart();
builder.Services.AddSingleton(services =>
    services.GetRequiredService<IOptions<EnvironmentSpendOptions>>().Value
);
builder.Services.AddSimulatorSpendHeader(builder.Configuration);
builder.Services.AddSingleton<ISpendAccountResolver>(_ => new ObservingSpendAccountResolver(
    new SpendAccountResolver(SpendPurposeMap.LoadDefault())
));
builder.Services.AddSingleton<IEnvironmentSpendLeaseStore, PostgresEnvironmentSpendLeaseStore>();
builder.Services.AddSingleton<EnvironmentSpendLeaseService>();
builder.Services.AddSingleton<ConversationCursorCodec>();
var conversationPrBaseUrl =
    builder.Configuration["Conversation:ProfessionalRuntimeBaseUrl"]
    ?? "https://professional-runtime:5443";
builder
    .Services.AddHttpClient(
        "ConversationProfessionalRuntime",
        client =>
        {
            var address = new Uri(conversationPrBaseUrl);
            if (address.Scheme != Uri.UriSchemeHttps)
                throw new InvalidOperationException("Conversation runtime requires HTTPS.");
            client.BaseAddress = address;
            client.Timeout = TimeSpan.FromSeconds(10);
        }
    )
    .ConfigurePrimaryHttpMessageHandler(services =>
        services.GetRequiredService<WorkloadIdentityClient>().CreateHandler("professional-runtime")
    );
builder.Services.AddScoped<HttpConversationExecutionGateway>();
builder.Services.AddScoped<IConversationExecutionGateway>(services =>
    services.GetRequiredService<HttpConversationExecutionGateway>()
);
builder.Services.AddScoped<IConversationBatchExecutionGateway>(services =>
    services.GetRequiredService<HttpConversationExecutionGateway>()
);
builder.Services.AddScoped<IConversationExecutionEventSource>(services =>
    services.GetRequiredService<HttpConversationExecutionGateway>()
);
builder.Services.AddScoped<OperationalMandateResolver>();
builder.Services.AddScoped<IOperationalMandateResolver>(services =>
    services.GetRequiredService<OperationalMandateResolver>()
);
builder.Services.AddScoped<IConversationBatchTaskResolver, ConversationBatchTaskResolver>();
builder.Services.AddScoped<PerformanceReviewService>();
builder.Services.AddScoped<ConversationService>();
builder.Services.AddScoped<ConversationRuntimeEventIngestion>();
builder.Services.AddSingleton<InferenceWorkloadAuthority>();
builder.Services.AddSingleton<ProviderCredentialWorkloadAuthority>();
builder.Services.AddSingleton<IProviderCredentialResolver, ProviderCredentialResolver>();
builder.Services.AddSingleton<Waooaw.WorkloadIdentity.InferenceWorkloadValidator>();
Waooaw.WorkloadIdentity.InferenceWorkloadValidator.ConfigureTransport(
    builder,
    "business-platform",
    "ai-runtime"
);
builder.Services.AddScoped<ConversationInferenceEvidence>();
builder.Services.AddScoped<ConversationEnvironmentSpendOwner>();
builder.Services.AddScoped<IConversationInferenceOwner, ConversationInferenceOwner>();
builder.Services.AddScoped<ConversationRuntimeIdentityAuthority>();
builder.Services.AddScoped<ConversationReconciliationService>();
builder.Services.AddScoped<IConversationExecutionReconciliationGateway>(services =>
    services.GetRequiredService<HttpConversationExecutionGateway>()
);
builder.Services.AddSingleton<ConversationRuntimeWorkScope>();
builder.Services.AddScoped<ConversationRuntimeWorkDirectory>();
builder.Services.AddScoped<ConversationRuntimeEventWorker>();
builder.Services.AddHostedService<ConversationRuntimeEventHostedService>();
builder.Services.AddSingleton<ConversationBatchWorkScope>();
builder.Services.AddScoped<ConversationBatchWorkDirectory>();
builder.Services.AddScoped<ConversationBatchDispatchWorker>();
builder.Services.AddHostedService<ConversationBatchDispatchHostedService>();
builder.Services.AddScoped<CustomerEngagementWorkspaceService>();
builder.Services.AddScoped<CustomerEngagementAdmissionService>();
builder.Services.Configure<Wc120ConversationOptions>(
    builder.Configuration.GetSection("Wc120Conversation")
);
builder.Services.AddScoped<ConversationContextProfileService>();
builder.Services.AddScoped<IConversationReferenceResolver>(services =>
    services.GetRequiredService<ConversationContextProfileService>()
);
builder.Services.AddScoped<ConversationStopFence>();
builder.Services.AddScoped<WhatsAppOutboxService>();
builder.Services.Configure<WhatsAppCapabilityOptions>(
    builder.Configuration.GetSection("WhatsAppCapability")
);
builder.Services.AddSingleton<IWhatsAppCapabilityGate, WhatsAppCapabilityGate>();
builder.Services.Configure<WhatsAppProviderOptions>(
    builder.Configuration.GetSection("WhatsAppProvider")
);
builder.Services.AddSingleton<WhatsAppKeyVaultCredentials>();
builder.Services.AddSingleton<IWhatsAppProviderCredentials>(services =>
    services.GetRequiredService<WhatsAppKeyVaultCredentials>()
);
builder.Services.AddSingleton<IWhatsAppWebhookCredentials>(services =>
    services.GetRequiredService<WhatsAppKeyVaultCredentials>()
);
builder.Services.AddSingleton<WhatsAppTenantExecutionScope>();
builder.Services.AddScoped<WhatsAppTrafficBudget>();
builder.Services.AddScoped<WhatsAppRelationshipRouting>();
builder.Services.AddScoped<WhatsAppDeliveryObservationRouting>();
builder.Services.AddScoped<WhatsAppGuestTrafficBudget>();
builder.Services.AddScoped<IWhatsAppProviderAdapter, WhatsAppCloudProviderAdapter>();
builder
    .Services.AddHttpClient(
        "WhatsAppProtected",
        client => client.Timeout = TimeSpan.FromSeconds(15)
    )
    .RemoveAllLoggers()
    .ConfigurePrimaryHttpMessageHandler(() =>
        new HttpClientHandler { AllowAutoRedirect = false, UseCookies = false }
    );
builder.Services.AddHostedService<WhatsAppOutboxHostedService>();
builder.Services.AddScoped<WhatsAppOutboxWorker>();
builder.Services.AddScoped<WhatsAppOutboxWorkDirectory>();
builder.Services.AddScoped<ConversationOutboundContributionService>();
builder.Services.AddScoped<WhatsAppMediaQuarantineService>();
builder.Services.AddScoped<ConversationOperationsService>();
builder.Services.AddHostedService<WhatsAppOperationsHostedService>();
builder.Services.AddScoped<PortalInteractionService>();
builder.Services.AddScoped<IGuestConversation>(provider =>
    provider.GetRequiredService<PortalInteractionService>()
);
builder.Services.AddSingleton<
    IValidateOptions<EmploymentProtocolOptions>,
    EmploymentProtocolOptionsValidator
>();
builder
    .Services.AddOptions<EmploymentProtocolOptions>()
    .Bind(builder.Configuration.GetSection("EmploymentProtocol"))
    .ValidateOnStart();
builder.Services.AddSingleton<IEmploymentProtocolGate, EmploymentProtocolGate>();
builder.Services.AddSingleton<IConversationalEmploymentPersistence>(
    new PostgresConversationalEmploymentPersistence(employmentRelationshipConn)
);
builder.Services.AddSingleton<ConversationalEmploymentService>();
builder.Services.AddSingleton<PostgresComponentUnitOutbox>(
    new PostgresComponentUnitOutbox(employmentRelationshipConn)
);
builder.Services.AddSingleton<IComponentUnitOutbox>(services =>
    services.GetRequiredService<PostgresComponentUnitOutbox>()
);
builder.Services.AddSingleton<IComponentUnitCompletionSink>(services =>
    services.GetRequiredService<PostgresComponentUnitOutbox>()
);
if (
    workloadIdentity is not null
    && Uri.TryCreate(wbeWorkspaceBaseUrl, UriKind.Absolute, out var componentUnitWbeUri)
)
    builder.Services.AddSingleton(
        Guarded<IComponentUnitGateway>(
            new AuthenticatedComponentUnitGateway(workloadIdentity, componentUnitWbeUri),
            new UnconfiguredComponentUnitGateway()
        )
    );
else
    builder.Services.AddSingleton<IComponentUnitGateway, UnconfiguredComponentUnitGateway>();
builder.Services.AddHostedService<ComponentUnitCompletionWorker>();
if (
    workloadIdentity is not null
    && Uri.TryCreate(wbeWorkspaceBaseUrl, UriKind.Absolute, out var packageCatalogWbeUri)
)
    builder.Services.AddSingleton(
        Guarded<IPackageCatalogGateway>(
            new AuthenticatedPackageCatalogGateway(workloadIdentity, packageCatalogWbeUri),
            new UnconfiguredPackageCatalogGateway()
        )
    );
else
    builder.Services.AddSingleton<IPackageCatalogGateway, UnconfiguredPackageCatalogGateway>();
builder.Services.AddSingleton<IPackageComponentLabelSource, HumanizedComponentLabelSource>();
builder.Services.AddSingleton<PackageCatalogService>();
var employmentDomainBaseUrl = builder.Configuration["AgentAdapters:EmploymentBaseUrl"];
if (
    workloadIdentity is not null
    && Uri.TryCreate(employmentDomainBaseUrl, UriKind.Absolute, out var employmentDomainUri)
    && Uri.TryCreate(wbeWorkspaceBaseUrl, UriKind.Absolute, out var employmentWbeUri)
)
{
    builder.Services.AddScoped(services =>
        Guarded<IEmploymentCommandOwnerGateway>(
            new GeneratedEmploymentCommandOwnerGateway(
                workloadIdentity,
                workloadIdentity.CreateClient(employmentDomainUri, "domain-adapter"),
                workloadIdentity.CreateClient(employmentWbeUri, "billing-engine"),
                services.GetRequiredService<IRelationshipConstitutionalGateway>(),
                services.GetRequiredService<IConversationalEmploymentPersistence>()
            ),
            new UnconfiguredEmploymentCommandOwnerGateway()
        )
    );
}
else
    builder.Services.AddScoped<
        IEmploymentCommandOwnerGateway,
        UnconfiguredEmploymentCommandOwnerGateway
    >();
builder.Services.AddScoped<IEmploymentCommandCoordinator, EmploymentCommandCoordinator>();
builder.Services.AddSingleton<EmploymentCompatibilityService>();

// ── Common agent workbench — WC-136 C6 ──────────────────────────────────────
builder
    .Services.AddOptions<WorkbenchOptions>()
    .Bind(builder.Configuration.GetSection(WorkbenchOptions.SectionName));
if (
    workloadIdentity is not null
    && Uri.TryCreate(employmentDomainBaseUrl, UriKind.Absolute, out var workbenchDomainUri)
)
    builder.Services.AddSingleton(
        Guarded<IAdmittedExperienceManifestSource>(
            new DomainAdapterExperienceManifestSource(workloadIdentity, workbenchDomainUri),
            new UnconfiguredAdmittedExperienceManifestSource()
        )
    );
else
    builder.Services.AddSingleton<
        IAdmittedExperienceManifestSource,
        UnconfiguredAdmittedExperienceManifestSource
    >();
if (
    workloadIdentity is not null
    && Uri.TryCreate(wbeWorkspaceBaseUrl, UriKind.Absolute, out var workbenchWbeUri)
)
    builder.Services.AddSingleton(
        Guarded<IWorkbenchCommercialReader>(
            new AuthenticatedWorkbenchCommercialReader(workloadIdentity, workbenchWbeUri),
            new UnconfiguredWorkbenchCommercialReader()
        )
    );
else
    builder.Services.AddSingleton<
        IWorkbenchCommercialReader,
        UnconfiguredWorkbenchCommercialReader
    >();
builder.Services.AddSingleton<IWorkbenchLedgerStore, PostgresWorkbenchLedgerStore>();
builder.Services.AddSingleton<IWorkbenchHandoffStore, PostgresWorkbenchHandoffStore>();
builder.Services.AddSingleton<IWorkbenchGoalHistoryStore, PostgresWorkbenchGoalHistoryStore>();
builder.Services.AddSingleton<WorkbenchCommandLedger>();
builder.Services.AddSingleton<WorkbenchHandoffService>();
builder.Services.AddScoped<WorkbenchProjectionService>();
builder.Services.AddScoped<WorkbenchCommandService>();
builder.Services.AddScoped<IWorkbenchWhatsAppResponder, WorkbenchWhatsAppResponder>();

// ── Voice Contributions — WC-062 / GOAL-005 F6 ─────────────────────────────
var voiceConn =
    builder.Configuration.GetConnectionString("VoiceContribution")
    ?? builder.Configuration.GetConnectionString("DefaultConnection")
    ?? "Host=localhost;Database=waooaw_bp;Username=business_app;";
builder.Services.AddDbContextFactory<VoiceContributionDbContext>(
    (services, options) =>
        options
            .UseNpgsql(voiceConn)
            .AddInterceptors(services.GetRequiredService<TenantDbConnectionInterceptor>())
);
if (
    !string.IsNullOrWhiteSpace(builder.Configuration["Voice:Media:FfprobePath"])
    && !string.IsNullOrWhiteSpace(builder.Configuration["Voice:Media:ClamAvHost"])
    && !string.IsNullOrWhiteSpace(builder.Configuration["Voice:Media:PayloadRoot"])
    && !string.IsNullOrWhiteSpace(builder.Configuration["Voice:Media:EncryptionKey"])
)
{
    builder.Services.AddSingleton<ConfiguredVoiceMediaGateway>();
    builder.Services.AddSingleton<IVoiceMediaGateway>(services =>
        services.GetRequiredService<ConfiguredVoiceMediaGateway>()
    );
    builder.Services.AddHostedService<VoiceMediaRetentionWorker>();
}
else
{
    builder.Services.AddSingleton<IVoiceMediaGateway, UnconfiguredVoiceMediaGateway>();
}
builder.Services.AddSingleton<IVoiceContentProtector, AesVoiceContentProtector>();
builder.Services.AddScoped<VoiceContributionService>();

// ─────────────────────────────────────────────────────────────────────────────
var app = builder.Build();
if (workloadInboundPort is { } privatePort)
    app.Use(
        async (context, next) =>
        {
            if (
                context.Connection.LocalPort == privatePort
                && !context.Request.Path.StartsWithSegments(WorkloadInboundListener.RoutePrefix)
            )
            {
                context.Response.StatusCode = StatusCodes.Status404NotFound;
                return;
            }
            await next();
        }
    );
app.UseMiddleware<WhatsAppCallbackHostMiddleware>();

// ── Middleware pipeline (order is constitutional — do NOT reorder) ────────────
//   1. Swagger UI (dev only)
//   2. Routing
//   3. Authentication  ← must precede Authorization (ASP.NET Core requirement)
//   4. Authorization   ← must precede TenantIsolation (tenant id lives in validated JWT)
//   5. TenantIsolation ← extracts tenant_id from validated JWT, sets RLS session var
//   6. Controllers

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseRouting();
app.UseStatusCodePages(async statusCodeContext =>
{
    var httpContext = statusCodeContext.HttpContext;
    var response = httpContext.Response;
    var status = response.StatusCode;
    var path = httpContext.Request.Path;
    var isInvalidRequest = status == StatusCodes.Status405MethodNotAllowed;
    var code = path.StartsWithSegments("/api/v1/identity")
        ? isInvalidRequest
            ? "IDENTITY_REQUEST_INVALID"
            : "IDENTITY_RESOURCE_NOT_ACCESSIBLE"
        : path.StartsWithSegments("/api/v1/customer-portal/interactions/portal/messages")
        || path.Value?.Contains("/conversation", StringComparison.Ordinal) == true
            ? isInvalidRequest
                ? "CONVERSATION_REQUEST_INVALID"
                : "CONVERSATION_NOT_ACCESSIBLE"
            : path.Value?.Contains("/workspace", StringComparison.Ordinal) == true
            || path.Value?.Contains("/evaluation", StringComparison.Ordinal) == true
                ? isInvalidRequest
                    ? "RELATIONSHIP_WORKSPACE_REQUEST_INVALID"
                    : "RELATIONSHIP_WORKSPACE_NOT_ACCESSIBLE"
                : path.Value?.Contains("/admission/", StringComparison.Ordinal) == true
                    ? isInvalidRequest
                        ? "ADMISSION_REQUEST_INVALID"
                        : "ADMISSION_NOT_FOUND"
                    : isInvalidRequest
                        ? "REQUEST_INVALID"
                        : "RESOURCE_NOT_FOUND";
    var title = status switch
    {
        StatusCodes.Status404NotFound => "Resource not found",
        StatusCodes.Status405MethodNotAllowed => "Method not allowed",
        _ => "Request failed",
    };
    await response.WriteAsJsonAsync(
        new
        {
            type = $"https://waooaw.com/problems/{code.ToLowerInvariant().Replace('_', '-')}",
            title,
            status,
            code,
            correlationId = Guid.NewGuid(),
        },
        options: null,
        contentType: "application/problem+json",
        cancellationToken: httpContext.RequestAborted
    );
});
app.UseMiddleware<JourneyTelemetryMiddleware>();

// C-026: authentication MUST be validated before any tenant context is extracted.
// An unauthenticated request must never reach TenantIsolationMiddleware with
// a user-supplied x-tenant-id — it would bypass RLS.
app.UseAuthentication();
app.UseAuthorization();

// WC-136 C7-02: test-only X-Spend-Account-Class for the authenticated visitor-simulator role; default off.
app.UseSimulatorSpendHeader();

// C-005 / C-026: sets PostgreSQL session variable from JWT tenant_id claim.
// Returns 403 if tenant_id claim is absent from a successfully authenticated token.
app.UseMiddleware<CustomerMembershipMiddleware>();
app.UseWhen(
    context =>
        !context.Items.ContainsKey(CustomerMembershipMiddleware.JourneyItem)
        && !context.Items.ContainsKey(CustomerMembershipMiddleware.StaffItem)
        // The internal acceptance route carries no tenant; its guard decides authority before anything is read.
        && context.GetEndpoint()?.Metadata.GetMetadata<AcceptanceProvisionerRouteAttribute>()
            is null,
    branch => branch.UseTenantIsolation()
);

app.MapControllers();
app.MapHealthChecks("/health").WithMetadata(new HttpMethodMetadata(["GET"]));
app.MapHealthChecks("/health/live", new HealthCheckOptions { Predicate = _ => false })
    .WithMetadata(new HttpMethodMetadata(["GET"]));
app.MapHealthChecks(
        "/health/ready",
        new HealthCheckOptions { Predicate = registration => registration.Tags.Contains("ready") }
    )
    .WithMetadata(new HttpMethodMetadata(["GET"]));
app.MapHealthChecks(
        "/health/detail",
        new HealthCheckOptions
        {
            Predicate = registration =>
                registration.Tags.Contains(WorkloadCredentialHealthCheck.DetailTag),
            ResponseWriter = WorkloadCredentialHealthCheck.WriteDetailAsync,
        }
    )
    .WithMetadata(new HttpMethodMetadata(["GET"]));

app.Run();

// Required for WebApplicationFactory in tests (CCT-MT-01)
public partial class Program { }
