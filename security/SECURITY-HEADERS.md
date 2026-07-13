# WAOOAW — Security Headers and HTTP Security Policy

**Version:** 1.0
**Date:** 2026-07-13
**Applies to:** Business Platform (port 5001), Professional Runtime (port 5003), Web application (port 3000)
**Reference:** OWASP Secure Headers Project; Mozilla Observatory

---

## Required HTTP Security Headers

All WAOOAW HTTP responses must include the following headers. These are configured in:
- `.NET services:` ASP.NET Core middleware (Program.cs)
- `Next.js web:` next.config.js headers configuration
- `Azure Container Apps:` Ingress configuration for additional global headers

### Mandatory Headers

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
  Reason: Forces HTTPS for 1 year. Prevents SSL stripping attacks.
  Implementation: .NET middleware; also configured in Azure Container Apps ingress.

Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:; font-src 'self'; connect-src 'self' wss:;
  frame-ancestors 'none'; base-uri 'self'; form-action 'self'
  Reason: Prevents XSS and data injection. Must be tuned for the portal's actual needs.
  Note: 'unsafe-inline' for style is acceptable if nonces are not implemented.
  Implementation: Next.js next.config.js + .NET SecurityHeaders middleware.

X-Frame-Options: DENY
  Reason: Prevents clickjacking. Superseded by CSP frame-ancestors but kept for older browsers.

X-Content-Type-Options: nosniff
  Reason: Prevents MIME type sniffing attacks.

Referrer-Policy: strict-origin-when-cross-origin
  Reason: Limits referrer information leakage to other origins.

Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
  Reason: Explicitly disables browser features WAOOAW does not use.
  Note: camera=() is especially important given C-060 (no camera for minor students).

X-XSS-Protection: 0
  Reason: Modern browsers have built-in XSS protection. The old header can cause issues.
  Setting to 0 disables the broken IE/old-Chrome XSS auditor.
```

### Headers to Remove

```
Server: (remove — do not expose server technology)
X-Powered-By: (remove — do not expose framework version)
X-AspNet-Version: (remove — .NET specific, must be suppressed)
X-AspNetMvc-Version: (remove)
```

### API Responses Additional Headers

```
Cache-Control: no-store
  Reason: API responses containing customer data must not be cached by browsers or proxies.
  Applies to: All /api/v1/* endpoints.

X-Request-ID: {uuid}
  Reason: Traceability. Every API response carries a unique request ID for log correlation.
  Implementation: .NET middleware generates and attaches; OpenTelemetry trace ID used.
```

---

## CORS Policy

### Business Platform API

```csharp
// Program.cs
builder.Services.AddCors(options =>
{
    options.AddPolicy("PortalOnly", policy =>
    {
        policy
            .WithOrigins(
                "https://waooaw.com",
                "https://app.waooaw.com",
                Environment.GetEnvironmentVariable("ADDITIONAL_CORS_ORIGIN") ?? ""
            )
            .AllowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
            .AllowedHeaders("Authorization", "Content-Type", "X-Request-ID")
            .AllowCredentials()  // Required for cookies/auth
            .SetPreflightMaxAge(TimeSpan.FromHours(1));
    });
});
// Apply: app.UseCors("PortalOnly");
```

**Prohibited:** `AllowAnyOrigin()` — never use in any environment except isolated local dev.

### WhatsApp Webhook Endpoint

```
/api/v1/whatsapp/webhook — CORS does not apply
  This endpoint is called by Meta's servers, not by browsers.
  Authentication: Meta HMAC-SHA256 signature validation (ADR-023).
  IP allowlist: Meta's published webhook source IPs (optional additional layer).
```

---

## Error Response Policy

**Auditors specifically look for information leakage in error responses.** WAOOAW API errors must never expose:

```yaml
forbidden_in_error_responses:
  - Stack traces (no exception details in production responses)
  - Database connection strings or query details
  - Internal service hostnames or ports
  - File system paths
  - Framework version information
  - User enumeration (login endpoint must return same response for invalid user and wrong password)

required_error_format:
  production:
    body: '{"error": "REQUEST_FAILED", "request_id": "uuid", "timestamp": "ISO8601"}'
    status: appropriate HTTP status code
    detail: NONE (no internal information)
    
  development_only:
    body: '{"error": "VALIDATION_ERROR", "detail": "...", "stack": "..."}'
    note: "Development-only — must be behind ASPNETCORE_ENVIRONMENT=Development check"
```

**User enumeration prevention:**
```
POST /api/v1/auth/login with valid email + wrong password → 401 "Invalid credentials"
POST /api/v1/auth/login with invalid email + any password → 401 "Invalid credentials"
[Same response body for both — prevents user enumeration]
```

---

## Cookie Security Policy

WAOOAW uses tokens (JWT Bearer), not session cookies, for API authentication. If any cookies are set:

```
Set-Cookie: session=...; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=3600
  HttpOnly: prevents JavaScript access
  Secure: HTTPS only
  SameSite=Strict: prevents CSRF
```

---

## Implementation Reference

```csharp
// Business Platform — Program.cs security middleware
app.Use(async (context, next) =>
{
    context.Response.Headers.Add("X-Content-Type-Options", "nosniff");
    context.Response.Headers.Add("X-Frame-Options", "DENY");
    context.Response.Headers.Add("Referrer-Policy", "strict-origin-when-cross-origin");
    context.Response.Headers.Add("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
    context.Response.Headers.Remove("Server");
    context.Response.Headers.Remove("X-Powered-By");
    context.Response.Headers.Add("X-Request-ID", context.TraceIdentifier);
    await next();
});
```

```javascript
// Next.js — next.config.js
const securityHeaders = [
  { key: 'X-DNS-Prefetch-Control', value: 'on' },
  { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains; preload' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=(), payment=()' },
  { key: 'Content-Security-Policy', value: ContentSecurityPolicy },
];
```

---

## Mozilla Observatory Target Grade: A+

WAOOAW targets Mozilla Observatory grade A+ before commercial launch. Verification:
- Run: https://observatory.mozilla.org/analyze/waooaw.com
- Target score: ≥100/100
