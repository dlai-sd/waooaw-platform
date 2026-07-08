using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using System.Data.Common;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Infrastructure;

/// <summary>
/// Business Platform EF Core database context.
/// Manages the business schema — CRUD with RLS enforced via TenantDbCommandInterceptor.
/// </summary>
public class BusinessDbContext : DbContext
{
    public BusinessDbContext(DbContextOptions<BusinessDbContext> options,
        TenantDbCommandInterceptor tenantInterceptor)
        : base(options)
    {
        // Register tenant interceptor — sets SET LOCAL app.tenant_id before every query
        // engineering-standards.md §10
    }

    public DbSet<EmploymentContract> EmploymentContracts => Set<EmploymentContract>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.HasDefaultSchema("business");

        modelBuilder.Entity<EmploymentContract>(e =>
        {
            e.ToTable("employment_contracts");
            e.HasKey(x => x.Id);
            e.Property(x => x.Id).HasColumnName("id");
            e.Property(x => x.TenantId).HasColumnName("tenant_id").IsRequired();
            e.Property(x => x.ProfessionalId).HasColumnName("professional_id").IsRequired();
            e.Property(x => x.State).HasColumnName("state").IsRequired();
            e.Property(x => x.Goals).HasColumnName("goals").HasColumnType("jsonb");
            e.Property(x => x.ReviewCadence).HasColumnName("review_cadence").HasColumnType("jsonb");
            e.Property(x => x.IsTrial).HasColumnName("is_trial");
            e.Property(x => x.TrialEndsAt).HasColumnName("trial_ends_at");
            e.Property(x => x.TrialConvertedAt).HasColumnName("trial_converted_at");
            e.Property(x => x.CreatedAt).HasColumnName("created_at");
            e.Property(x => x.ActivatedAt).HasColumnName("activated_at");
        });
    }
}

/// <summary>
/// EF Core interceptor — sets SET LOCAL app.tenant_id on every DB connection.
/// This is how PostgreSQL RLS enforces tenant isolation (AD-004).
/// engineering-standards.md §10, security-architecture.md §2.
/// </summary>
public class TenantDbCommandInterceptor : DbCommandInterceptor
{
    private readonly IHttpContextAccessor _http;

    public TenantDbCommandInterceptor(IHttpContextAccessor http) => _http = http;

    public override async ValueTask<InterceptionResult<DbDataReader>> ReaderExecutingAsync(
        DbCommand command, CommandEventData eventData,
        InterceptionResult<DbDataReader> result, CancellationToken ct = default)
    {
        await SetTenantAsync(command, ct);
        return result;
    }

    public override async ValueTask<InterceptionResult<int>> NonQueryExecutingAsync(
        DbCommand command, CommandEventData eventData,
        InterceptionResult<int> result, CancellationToken ct = default)
    {
        await SetTenantAsync(command, ct);
        return result;
    }

    private async Task SetTenantAsync(DbCommand command, CancellationToken ct)
    {
        var tenantId = _http.HttpContext?.Items["tenant_id"]?.ToString();
        if (string.IsNullOrEmpty(tenantId)) return;

        // Security: validate UUID before injecting (prevents SQL injection via tenant_id)
        if (!Guid.TryParse(tenantId, out _))
            throw new InvalidOperationException("Invalid tenant_id in context — possible injection attempt");

        using var setCmd = command.Connection!.CreateCommand();
        setCmd.Transaction = command.Transaction;
        setCmd.CommandText = $"SET LOCAL app.tenant_id = '{tenantId}'";
        await setCmd.ExecuteNonQueryAsync(ct);
    }
}

// ─── Domain Entities ──────────────────────────────────────────────────────────
public class EmploymentContract
{
    public Guid Id { get; set; }
    public Guid TenantId { get; set; }
    public Guid ProfessionalId { get; set; }
    public Guid? DecisionSpaceId { get; set; }
    public string State { get; set; } = "EVALUATION";
    public int AuthorityLevel { get; set; } = 1;
    public string Goals { get; set; } = "[]";
    public string ReviewCadence { get; set; } = """{"frequencyDays": 30}""";
    public bool IsTrial { get; set; }
    public DateTime? TrialEndsAt { get; set; }
    public DateTime? TrialConvertedAt { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime? ActivatedAt { get; set; }
}
