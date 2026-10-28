terraform {
  required_version = "= 1.9.8"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.14.0"
    }
  }
}

locals {
  release_members = toset([
    "constitutional-engine",
    "business-platform",
    "professional-runtime",
    "ai-runtime",
    "web",
    "billing-engine",
    "agent-runtime-adapter-digital-marketing",
  ])
  database_members = toset([
    "constitutional-engine",
    "business-platform",
    "billing-engine",
  ])
  active_members               = var.workload_enabled ? local.release_members : toset([])
  runtime_dependencies_enabled = var.dependency_activation_enabled || var.application_activation_enabled
  auth_redis_container_enabled = var.workload_enabled && contains(["demo", "uat"], var.environment)
  auth_redis_host              = "ca-${var.environment}-auth-redis"
  auth_redis_url               = var.environment == "prod" ? var.auth_abuse_redis_url : "redis://${local.auth_redis_host}:6379/0"
  auth_redis_password_secret   = var.environment == "prod" ? "auth-abuse-redis-managed-key" : "auth-abuse-redis-password"
  pgbouncer_host               = "ca-${var.environment}-pgbouncer"
  auth_abuse_limits = {
    AUTH_START      = { limit = 20, windowSeconds = 600 }
    AUTH_CALLBACK   = { limit = 30, windowSeconds = 600 }
    RECOVERY        = { limit = 5, windowSeconds = 3600 }
    PROVIDER_LINK   = { limit = 10, windowSeconds = 3600 }
    PROVIDER_UNLINK = { limit = 10, windowSeconds = 3600 }
    RESEND          = { limit = 5, windowSeconds = 900 }
    CREDENTIAL      = { limit = 10, windowSeconds = 3600 }
  }
  public_ingress = {
    "constitutional-engine"                   = false
    "ai-runtime"                              = false
    "billing-engine"                          = false
    "web"                                     = true
    "business-platform"                       = true
    "professional-runtime"                    = true
    "agent-runtime-adapter-digital-marketing" = false
  }

  member_names = {
    for member in local.release_members : member => member == "agent-runtime-adapter-digital-marketing" ? "ca-${var.environment}-dma" : "ca-${var.environment}-${member}"
  }

  container_names = {
    for member in local.release_members : member => member == "agent-runtime-adapter-digital-marketing" ? "dma" : member
  }
  target_ports = {
    "constitutional-engine"                   = 5002
    "business-platform"                       = 5001
    "professional-runtime"                    = 5003
    "ai-runtime"                              = 5004
    "web"                                     = 3000
    "billing-engine"                          = 8140
    "agent-runtime-adapter-digital-marketing" = 8443
  }
  ingress_transports = {
    "constitutional-engine"                   = "http2"
    "business-platform"                       = "auto"
    "professional-runtime"                    = "auto"
    "ai-runtime"                              = "auto"
    "web"                                     = "auto"
    "billing-engine"                          = "auto"
    "agent-runtime-adapter-digital-marketing" = "auto"
  }
  service_urls = {
    constitutional_engine = "http://ca-${var.environment}-constitutional-engine"
    business_platform     = "http://ca-${var.environment}-business-platform"
    public_api            = "https://${coalesce(var.api_custom_hostname, "ca-${var.environment}-business-platform.${var.container_app_environment_default_domain}")}"
    professional_runtime  = "http://ca-${var.environment}-professional-runtime"
    ai_runtime            = "http://ca-${var.environment}-ai-runtime"
    billing_engine        = "http://ca-${var.environment}-billing-engine"
    dma_adapter           = "http://ca-${var.environment}-dma"
    identity_edge         = "https://${coalesce(var.identity_custom_hostname, "ca-${var.environment}-identity-edge.${var.container_app_environment_default_domain}")}"
    keycloak              = "http://ca-${var.environment}-keycloak"
    keycloak_private      = "https://ca-${var.environment}-keycloak.internal.${var.container_app_environment_default_domain}"
    web                   = "https://${coalesce(var.web_custom_hostname, "ca-${var.environment}-web.${var.container_app_environment_default_domain}")}"
  }
  verification_urls = {
    business_platform    = local.service_urls.business_platform
    professional_runtime = "http://ca-${var.environment}-professional-runtime"
    ai_runtime           = "http://ca-${var.environment}-ai-runtime"
    billing_engine       = "http://ca-${var.environment}-billing-engine"
    dma_adapter          = "http://ca-${var.environment}-dma"
    identity_edge        = "https://ca-${var.environment}-identity-edge.${var.container_app_environment_default_domain}"
    web                  = "http://ca-${var.environment}-web"
  }
  readiness_paths = {
    business-platform                       = "/health/ready"
    professional-runtime                    = "/health"
    ai-runtime                              = "/health"
    web                                     = "/api/health/ready"
    billing-engine                          = "/health"
    agent-runtime-adapter-digital-marketing = "/health/live"
  }
  keycloak_realm = {
    realm                  = "waooaw"
    displayName            = "WAOOAW Platform"
    enabled                = true
    sslRequired            = "external"
    registrationAllowed    = false
    loginWithEmailAllowed  = true
    duplicateEmailsAllowed = false
    resetPasswordAllowed   = false
    editUsernameAllowed    = false
    bruteForceProtected    = true
    accessTokenLifespan    = 900
    ssoSessionMaxLifespan  = var.environment == "demo" ? 28800 : 86400
    refreshTokenMaxReuse   = 0
    revokeRefreshToken     = true
    passwordPolicy         = "length(12) and upperCase(1) and digits(1) and specialChars(1) and notUsername"
    identityProviders      = concat(local.google_identity_providers, local.facebook_identity_providers)
    authenticationFlows = var.google_login_enabled ? [{
      alias       = "google verified email first login"
      description = "Create unique Google users or link an existing account by Google's verified email."
      providerId  = "basic-flow"
      topLevel    = true
      builtIn     = false
      authenticationExecutions = [
        {
          authenticator     = "idp-create-user-if-unique"
          authenticatorFlow = false
          requirement       = "ALTERNATIVE"
          priority          = 10
          userSetupAllowed  = false
        },
        {
          authenticator     = "idp-auto-link"
          authenticatorFlow = false
          requirement       = "ALTERNATIVE"
          priority          = 20
          userSetupAllowed  = false
        },
      ]
    }] : []
    clients = concat([
      {
        clientId                  = "waooaw-web"
        name                      = "WAOOAW Web Application"
        enabled                   = true
        publicClient              = false
        secret                    = "$${KEYCLOAK_CLIENT_SECRET}"
        standardFlowEnabled       = true
        implicitFlowEnabled       = false
        directAccessGrantsEnabled = false
        redirectUris = concat(
          ["${local.service_urls.web}/api/auth/callback/keycloak"],
          var.google_login_enabled ? ["${local.service_urls.web}/api/auth/callback/keycloak-google"] : [],
          var.facebook_login_enabled ? ["${local.service_urls.web}/api/auth/callback/keycloak-facebook"] : [],
        )
        webOrigins = [local.service_urls.web]
        attributes = {
          "pkce.code.challenge.method" = "S256"
          "post.logout.redirect.uris"  = "${local.service_urls.web}/login"
        }
        protocolMappers = [
          {
            name           = "tenant_id_mapper"
            protocol       = "openid-connect"
            protocolMapper = var.environment == "demo" ? "oidc-hardcoded-claim-mapper" : "oidc-usermodel-attribute-mapper"
            config = merge({
              "claim.name"           = "tenant_id"
              "jsonType.label"       = "String"
              "id.token.claim"       = "true"
              "access.token.claim"   = "true"
              "userinfo.token.claim" = "true"
              }, var.environment == "demo" ? {
              "claim.value" = "00000000-0000-0000-0000-000000000001"
              } : {
              "user.attribute" = "tenant_id"
            })
          },
          {
            name           = "audience_mapper"
            protocol       = "openid-connect"
            protocolMapper = "oidc-audience-mapper"
            config = {
              "included.client.audience" = "waooaw-platform"
              "id.token.claim"           = "false"
              "access.token.claim"       = "true"
            }
          },
          {
            name           = "realm_roles_mapper"
            protocol       = "openid-connect"
            protocolMapper = "oidc-usermodel-realm-role-mapper"
            config = {
              "claim.name"           = "realm_access.roles"
              "jsonType.label"       = "String"
              "multivalued"          = "true"
              "id.token.claim"       = "true"
              "access.token.claim"   = "true"
              "userinfo.token.claim" = "true"
            }
          },
          {
            name           = "google_identity_provider_session"
            protocol       = "openid-connect"
            protocolMapper = "oidc-usersessionmodel-note-mapper"
            config = {
              "user.session.note"    = "identity_provider"
              "claim.name"           = "idp"
              "jsonType.label"       = "String"
              "id.token.claim"       = "true"
              "access.token.claim"   = "true"
              "userinfo.token.claim" = "false"
            }
          },
        ]
      },
      {
        clientId                  = "waooaw-platform"
        name                      = "WAOOAW Platform Services"
        enabled                   = true
        bearerOnly                = true
        publicClient              = false
        standardFlowEnabled       = false
        directAccessGrantsEnabled = false
      },
      ], var.auth_preview_origin != null ? [
      {
        clientId                  = "waooaw-web-preview"
        name                      = "WAOOAW Codespaces Authentication Preview"
        enabled                   = true
        publicClient              = true
        standardFlowEnabled       = true
        implicitFlowEnabled       = false
        directAccessGrantsEnabled = false
        redirectUris = concat(
          ["${var.auth_preview_origin}/api/auth/callback/keycloak"],
          var.google_login_enabled ? ["${var.auth_preview_origin}/api/auth/callback/keycloak-google"] : [],
          var.facebook_login_enabled ? ["${var.auth_preview_origin}/api/auth/callback/keycloak-facebook"] : [],
        )
        webOrigins = [var.auth_preview_origin]
        attributes = {
          "pkce.code.challenge.method" = "S256"
          "post.logout.redirect.uris"  = "${var.auth_preview_origin}/login"
        }
        protocolMappers = [
          {
            name           = "tenant_id_mapper"
            protocol       = "openid-connect"
            protocolMapper = "oidc-hardcoded-claim-mapper"
            config = {
              "claim.name"           = "tenant_id"
              "jsonType.label"       = "String"
              "id.token.claim"       = "true"
              "access.token.claim"   = "true"
              "userinfo.token.claim" = "true"
              "claim.value"          = "00000000-0000-0000-0000-000000000001"
            }
          },
          {
            name           = "audience_mapper"
            protocol       = "openid-connect"
            protocolMapper = "oidc-audience-mapper"
            config = {
              "included.client.audience" = "waooaw-platform"
              "id.token.claim"           = "false"
              "access.token.claim"       = "true"
            }
          },
          {
            name           = "realm_roles_mapper"
            protocol       = "openid-connect"
            protocolMapper = "oidc-usermodel-realm-role-mapper"
            config = {
              "claim.name"           = "realm_access.roles"
              "jsonType.label"       = "String"
              "multivalued"          = "true"
              "id.token.claim"       = "true"
              "access.token.claim"   = "true"
              "userinfo.token.claim" = "true"
            }
          },
          {
            name           = "identity_provider_session"
            protocol       = "openid-connect"
            protocolMapper = "oidc-usersessionmodel-note-mapper"
            config = {
              "user.session.note"    = "identity_provider"
              "claim.name"           = "idp"
              "jsonType.label"       = "String"
              "id.token.claim"       = "true"
              "access.token.claim"   = "true"
              "userinfo.token.claim" = "false"
            }
          },
        ]
      },
      ] : [], var.google_login_enabled || var.facebook_login_enabled ? [
      {
        clientId                  = "waooaw-bp-identity-reader"
        name                      = "WAOOAW Business Platform Identity Reader"
        enabled                   = true
        publicClient              = false
        serviceAccountsEnabled    = true
        standardFlowEnabled       = false
        implicitFlowEnabled       = false
        directAccessGrantsEnabled = false
        fullScopeAllowed          = false
        clientAuthenticatorType   = "client-secret"
        secret                    = "$${BP_IDENTITY_READER_CLIENT_SECRET}"
        defaultClientScopes       = ["roles"]
        optionalClientScopes      = []
        attributes = {
          "access.token.lifespan" = "60"
        }
        protocolMappers = [{
          name           = "realm-management-view-users"
          protocol       = "openid-connect"
          protocolMapper = "oidc-hardcoded-role-mapper"
          config = {
            "role" = "realm-management.view-users"
          }
        }]
      },
      {
        clientId                  = "waooaw-bp-identity-lifecycle-writer"
        name                      = "WAOOAW Business Platform Identity Lifecycle Writer"
        enabled                   = true
        publicClient              = false
        serviceAccountsEnabled    = true
        standardFlowEnabled       = false
        implicitFlowEnabled       = false
        directAccessGrantsEnabled = false
        fullScopeAllowed          = false
        clientAuthenticatorType   = "client-secret"
        secret                    = "$${BP_IDENTITY_LIFECYCLE_WRITER_CLIENT_SECRET}"
        defaultClientScopes       = ["roles"]
        optionalClientScopes      = []
        attributes = {
          "access.token.lifespan" = "60"
        }
        protocolMappers = [{
          name           = "realm-management-manage-users"
          protocol       = "openid-connect"
          protocolMapper = "oidc-hardcoded-role-mapper"
          config = {
            "role" = "realm-management.manage-users"
          }
        }]
      },
    ] : [])
    roles = {
      realm = [
        { name = "customer" },
        { name = "founder" },
      ]
    }
    defaultRoles = ["customer"]
    users = concat(var.environment == "demo" ? [
      {
        username      = "founder@waooaw.local"
        email         = "founder@waooaw.local"
        enabled       = true
        emailVerified = true
        firstName     = "Demo"
        lastName      = "Founder"
        credentials = [
          {
            type      = "password"
            value     = "$${DEMO_FOUNDER_PASSWORD}"
            temporary = false
          },
        ]
        realmRoles = ["customer", "founder"]
      },
      ] : [], var.environment == "demo" && (var.google_login_enabled || var.facebook_login_enabled) ? [{
        username               = "service-account-waooaw-bp-identity-reader"
        enabled                = true
        serviceAccountClientId = "waooaw-bp-identity-reader"
        clientRoles = {
          realm-management = ["view-users"]
        }
      },
      {
        username               = "service-account-waooaw-bp-identity-lifecycle-writer"
        enabled                = true
        serviceAccountClientId = "waooaw-bp-identity-lifecycle-writer"
        clientRoles = {
          realm-management = ["manage-users"]
        }
      }
    ] : [])
  }
  keycloak_realm_base64 = base64encode(jsonencode(local.keycloak_realm))
  keycloak_migration_optional_secrets = merge(
    var.google_login_enabled ? {
      google-client-id = {
        env_name    = "GOOGLE_CLIENT_ID"
        resource_id = local.google_secret_resource_ids["google-client-id"]
        uri         = local.google_secret_uris["google-client-id"]
      }
      google-client-secret = {
        env_name    = "GOOGLE_CLIENT_SECRET"
        resource_id = local.google_secret_resource_ids["google-client-secret"]
        uri         = local.google_secret_uris["google-client-secret"]
      }
    } : {},
    var.facebook_login_enabled ? {
      meta-login-id = {
        env_name    = "META_LOGIN_CLIENT_ID"
        resource_id = local.facebook_secret_resource_ids["meta-login-client-id"]
        uri         = local.facebook_secret_uris["meta-login-client-id"]
      }
      meta-login-secret = {
        env_name    = "META_LOGIN_CLIENT_SECRET"
        resource_id = local.facebook_secret_resource_ids["meta-login-client-secret"]
        uri         = local.facebook_secret_uris["meta-login-client-secret"]
      }
    } : {},
    var.google_login_enabled || var.facebook_login_enabled ? {
      bp-reader-secret = {
        env_name    = "BP_IDENTITY_READER_CLIENT_SECRET"
        resource_id = local.identity_reader_secret_resource_ids["bp-identity-reader-client-secret"]
        uri         = local.identity_reader_secret_uris["bp-identity-reader-client-secret"]
      }
      bp-writer-secret = {
        env_name    = "BP_IDENTITY_LIFECYCLE_WRITER_CLIENT_SECRET"
        resource_id = local.identity_lifecycle_writer_secret_resource_ids["keycloak-lifecycle-writer-client-secret"]
        uri         = local.identity_lifecycle_writer_secret_uris["keycloak-lifecycle-writer-client-secret"]
      }
    } : {},
  )
  identity_edge_config = templatefile("${path.module}/identity-edge.conf.tftpl", {
    environment    = var.environment
    default_domain = var.container_app_environment_default_domain
  })
  identity_edge_config_base64 = base64encode(local.identity_edge_config)
  runtime_environment = {
    "constitutional-engine" = {
      ASPNETCORE_URLS = "http://+:5002"
    }
    "business-platform" = merge({
      ASPNETCORE_ENVIRONMENT                          = "Production"
      ASPNETCORE_URLS                                 = "http://+:5001"
      ConstitutionalEngine__Address                   = local.service_urls.constitutional_engine
      ConstitutionalEngine__GrpcUrl                   = local.service_urls.constitutional_engine
      Keycloak__Audience                              = "waooaw-platform"
      Keycloak__Authority                             = "${local.service_urls.identity_edge}/realms/waooaw"
      Keycloak__RequireHttpsMetadata                  = "true"
      IdentityBrokerRead__Enabled                     = tostring(var.google_login_enabled || var.facebook_login_enabled)
      IdentityBrokerRead__ActorIssuer                 = "${local.service_urls.identity_edge}/realms/waooaw"
      IdentityBrokerRead__PrivateOrigin               = local.service_urls.keycloak_private
      IdentityBrokerRead__AllowedPrivateHosts__0      = "ca-${var.environment}-keycloak.internal.${var.container_app_environment_default_domain}"
      IdentityBrokerRead__AllowedAuthorizedParties__0 = "waooaw-web"
      IdentityBrokerRead__ClientId                    = "waooaw-bp-identity-reader"
      IdentityLifecycleWriter__Enabled                = tostring(var.google_login_enabled || var.facebook_login_enabled)
      IdentityLifecycleWriter__PrivateOrigin          = local.service_urls.keycloak_private
      IdentityLifecycleWriter__AllowedPrivateHosts__0 = "ca-${var.environment}-keycloak.internal.${var.container_app_environment_default_domain}"
      IdentityLifecycleWriter__ClientId               = "waooaw-bp-identity-lifecycle-writer"
      }, var.environment == "demo" ? {
      # The Demo schema lives on the provisioned persistent instance (WC-124); the image's
      # disposable-database bootstrap is only for the CI image smoke test.
      WAOOAW_DEMO_DATABASE_BOOTSTRAP = "false"
      DMA_ADMISSION_CONTENT_DIGEST   = var.dma_admission_content_digest
      DMA_ARTIFACT_DIGEST            = split("@", var.image_digests["agent-runtime-adapter-digital-marketing"])[1]
      } : {}, var.auth_preview_origin != null ? {
      IdentityBrokerRead__AllowedAuthorizedParties__1 = "waooaw-web-preview"
      } : {}, var.google_login_enabled ? {
      IdentityBrokerRead__Providers__google__ProviderNamespace = "urn:waooaw:identity:${var.environment}:google:customer-login:v1"
      IdentityBrokerRead__Providers__google__TrustConfigDigest = sha256(jsonencode({
        issuer             = "${local.service_urls.identity_edge}/realms/waooaw"
        provider_alias     = "google"
        provider_namespace = "urn:waooaw:identity:${var.environment}:google:customer-login:v1"
      }))
      } : {}, var.facebook_login_enabled ? {
      IdentityBrokerRead__Providers__facebook__ProviderNamespace = "urn:waooaw:identity:${var.environment}:facebook:customer-login:v1"
      IdentityBrokerRead__Providers__facebook__TrustConfigDigest = sha256(jsonencode({
        issuer             = "${local.service_urls.identity_edge}/realms/waooaw"
        provider_alias     = "facebook"
        provider_namespace = "urn:waooaw:identity:${var.environment}:facebook:customer-login:v1"
      }))
    } : {}, var.environment == "demo" ? local.demo_identity_runtime : {})
    "professional-runtime" = merge({
      AIR_TRANSCRIPTION_BASE_URL    = local.service_urls.ai_runtime
      CONSTITUTIONAL_ENGINE_ADDRESS = "ca-${var.environment}-constitutional-engine:80"
      DMA_ADAPTER_BASE_URL          = local.service_urls.dma_adapter
      KEYCLOAK_AUDIENCE             = "waooaw-platform"
      KEYCLOAK_ISSUER               = "${local.service_urls.identity_edge}/realms/waooaw"
      KEYCLOAK_JWKS_URL             = "${local.service_urls.identity_edge}/realms/waooaw/protocol/openid-connect/certs"
      }, var.environment == "demo" ? {
      TEMPORAL_ADDRESS   = "ca-${var.environment}-temporal:80"
      TEMPORAL_NAMESPACE = "default"
    } : {})
    "ai-runtime" = {
      BP_BASE_URL                   = local.service_urls.business_platform
      CONSTITUTIONAL_ENGINE_ADDRESS = "ca-${var.environment}-constitutional-engine:80"
      PLATFORM_PHASE                = "IMPLEMENTATION"
    }
    "web" = merge({
      AUTH_ABUSE_LIMITS_JSON                = jsonencode(local.auth_abuse_limits)
      AZURE_KEY_VAULT_URL                   = trimsuffix(var.key_vault_secret_uris["web"], "/secrets/web")
      AZURE_KEY_VAULT_WRITER_CLIENT_ID      = "710af8d6-8e2c-4f9d-9b1c-2230de9de1f8"
      AZURE_TENANT_ID                       = "0471534c-1bbe-40ab-ae65-3f721b62582c"
      BUSINESS_PLATFORM_URL                 = local.service_urls.business_platform
      KEYCLOAK_CLIENT_ID                    = "waooaw-web"
      KEYCLOAK_ISSUER                       = "${local.service_urls.identity_edge}/realms/waooaw"
      KEYCLOAK_READINESS_ISSUER             = "${local.verification_urls.identity_edge}/realms/waooaw"
      NEXTAUTH_URL                          = local.service_urls.web
      NODE_ENV                              = "production"
      REDIS_URL                             = local.auth_redis_url
      SESSION_PROTOCOL_DIGEST_WRITE_VERSION = var.web_session_protocol_digest_write_version
      SESSION_TOKEN_ENVELOPE_WRITE_VERSION  = var.web_session_token_envelope_write_version
      WAOOAW_ENVIRONMENT                    = var.environment
      WAOOAW_SERVER_SESSION_MODE            = var.web_session_mode
      # web reaches the provisioned instance through in-VNet PgBouncer, which terminates no TLS.
      # Without this, NODE_ENV=production makes postgres.js demand TLS and readiness never passes.
      WEB_SESSION_DATABASE_SSL_MODE = "disable"
      WEB_SESSION_DEPLOY_VERSION    = var.web_session_deploy_version
      }, var.web_session_mode == "disabled" ? {} : {
      SESSION_HANDLE_DIGEST_WRITE_VERSION         = var.web_session_handle_digest_write_version
      WEB_SESSION_CONFIG_DIGEST                   = var.web_session_config_digest
      WEB_SESSION_EXPECTED_CONFIG_DIGEST          = var.web_session_expected_config_digest
      WEB_SESSION_EXPECTED_TELEMETRY_ROUTE_DIGEST = var.web_session_expected_telemetry_route_digest
      WEB_SESSION_TELEMETRY_ROUTE_DIGEST          = var.web_session_telemetry_route_digest
    })
    "billing-engine" = {
      BILLING_CONTRACT_ID            = "goal006-demo"
      BILLING_DECISION_SPACE_VERSION = "1"
      CONSTITUTIONAL_ENGINE_ADDRESS  = "ca-${var.environment}-constitutional-engine:80"
      MAX_DISCOUNT_PCT               = contains(["demo", "uat"], var.environment) ? "100" : "0"
      RAZORPAY_READINESS_STATE       = contains(["demo", "uat"], var.environment) ? "READY_TEST" : "NOT_CONFIGURED"
      REDIS_URL                      = local.auth_redis_url
      WAOOAW_ENVIRONMENT             = var.environment
      WBE_INTERNAL_BASE_URL          = local.service_urls.billing_engine
    }
    "agent-runtime-adapter-digital-marketing" = {
      DMA_ADMISSION_CONTENT_DIGEST = var.dma_admission_content_digest
      DMA_ARTIFACT_DIGEST          = split("@", var.image_digests["agent-runtime-adapter-digital-marketing"])[1]
      PR_WORKLOAD_URI              = "spiffe://${var.environment}.waooaw.internal/workload/professional-runtime"
      WAOOAW_ENVIRONMENT           = var.environment
    }
  }
  credential_environment = {
    "constitutional-engine"                   = "CE_RUNTIME_CREDENTIAL"
    "business-platform"                       = "BP_SERVICE_JWT_SECRET"
    "professional-runtime"                    = "PR_SERVICE_JWT_SECRET"
    "ai-runtime"                              = "PR_SERVICE_JWT_SECRET"
    "web"                                     = "KEYCLOAK_CLIENT_SECRET"
    "billing-engine"                          = "OPS_AUTH_TOKEN"
    "agent-runtime-adapter-digital-marketing" = "PR_SERVICE_JWT_SECRET"
  }
  credential_member = {
    "constitutional-engine"                   = "constitutional-engine"
    "business-platform"                       = "business-platform"
    "professional-runtime"                    = "professional-runtime"
    "ai-runtime"                              = "professional-runtime"
    "web"                                     = "web"
    "billing-engine"                          = "billing-engine"
    "agent-runtime-adapter-digital-marketing" = "professional-runtime"
  }
  identity_hmac_secret_uris = var.environment == "demo" ? {
    identity-hmac-active = "${trimsuffix(var.key_vault_secret_uris["business-platform"], "/business-platform")}/identity-hmac-active"
  } : {}
  identity_hmac_secret_resource_ids = var.environment == "demo" ? {
    identity-hmac-active = "${trimsuffix(var.key_vault_secret_resource_ids["business-platform"], "/business-platform")}/identity-hmac-active"
  } : {}
  identity_event_secret_uris = {
    identity-event-ingest-hmac = "${trimsuffix(var.key_vault_secret_uris["business-platform"], "/business-platform")}/identity-event-ingest-hmac"
  }
  identity_event_secret_resource_ids = {
    identity-event-ingest-hmac = "${trimsuffix(var.key_vault_secret_resource_ids["business-platform"], "/business-platform")}/identity-event-ingest-hmac"
  }
  continuity_hmac_secret_uris = {
    continuity-envelope-hmac = "${trimsuffix(var.key_vault_secret_uris["business-platform"], "/business-platform")}/continuity-envelope-hmac"
  }
  continuity_hmac_secret_resource_ids = {
    continuity-envelope-hmac = "${trimsuffix(var.key_vault_secret_resource_ids["business-platform"], "/business-platform")}/continuity-envelope-hmac"
  }
  conversation_cursor_secret_uris = {
    conversation-cursor-hmac = "${trimsuffix(var.key_vault_secret_uris["business-platform"], "/business-platform")}/conversation-cursor-hmac"
  }
  conversation_cursor_secret_resource_ids = {
    conversation-cursor-hmac = "${trimsuffix(var.key_vault_secret_resource_ids["business-platform"], "/business-platform")}/conversation-cursor-hmac"
  }
  auth_abuse_secret_environment = {
    auth-abuse-digest-key              = "AUTH_ABUSE_DIGEST_KEY"
    (local.auth_redis_password_secret) = "REDIS_PASSWORD"
  }
  auth_abuse_secret_uris = {
    for name in keys(local.auth_abuse_secret_environment) :
    name => "${trimsuffix(var.key_vault_secret_uris["web"], "/web")}/${name}"
  }
  auth_abuse_secret_resource_ids = {
    for name in keys(local.auth_abuse_secret_environment) :
    name => "${trimsuffix(var.key_vault_secret_resource_ids["web"], "/web")}/${name}"
  }
  oidc_transaction_secret_environment = {
    web-session-database-url    = "WEB_SESSION_DATABASE_URL"
    web-session-protocol-digest = "SESSION_PROTOCOL_DIGEST_KEYS"
    web-session-token-envelope  = "SESSION_TOKEN_ENVELOPE_KEYS"
  }
  web_session_secret_environment = merge(local.oidc_transaction_secret_environment, {
    web-session-handle-digest = "SESSION_HANDLE_DIGEST_KEYS"
  })
  active_web_session_secret_environment = merge(
    local.oidc_transaction_secret_environment,
    var.web_session_mode == "disabled" ? {} : {
      web-session-handle-digest = "SESSION_HANDLE_DIGEST_KEYS"
    }
  )
  web_session_secret_uris = {
    for name in keys(local.active_web_session_secret_environment) :
    name => "${trimsuffix(var.key_vault_secret_uris["web"], "/web")}/${name}"
  }
  web_session_secret_resource_ids = {
    for name in keys(local.active_web_session_secret_environment) :
    name => "${trimsuffix(var.key_vault_secret_resource_ids["web"], "/web")}/${name}"
  }
  razorpay_secret_uris = contains(["demo", "uat"], var.environment) ? {
    razorpay-test-key-id         = "${trimsuffix(var.key_vault_secret_uris["billing-engine"], "/billing-engine")}/razorpay-test-key-id"
    razorpay-test-key-secret     = "${trimsuffix(var.key_vault_secret_uris["billing-engine"], "/billing-engine")}/razorpay-test-key-secret"
    razorpay-test-webhook-secret = "${trimsuffix(var.key_vault_secret_uris["billing-engine"], "/billing-engine")}/razorpay-test-webhook-secret"
  } : {}
  razorpay_secret_resource_ids = contains(["demo", "uat"], var.environment) ? {
    razorpay-test-key-id         = "${trimsuffix(var.key_vault_secret_resource_ids["billing-engine"], "/billing-engine")}/razorpay-test-key-id"
    razorpay-test-key-secret     = "${trimsuffix(var.key_vault_secret_resource_ids["billing-engine"], "/billing-engine")}/razorpay-test-key-secret"
    razorpay-test-webhook-secret = "${trimsuffix(var.key_vault_secret_resource_ids["billing-engine"], "/billing-engine")}/razorpay-test-webhook-secret"
  } : {}
  minimum_replicas = {
    "constitutional-engine"                   = var.application_activation_enabled ? var.ce_min_replicas : 0
    "professional-runtime"                    = var.application_activation_enabled ? var.pr_min_replicas : 0
    "business-platform"                       = var.application_activation_enabled ? var.bp_min_replicas : 0
    "ai-runtime"                              = 0
    "web"                                     = var.application_activation_enabled ? var.web_min_replicas : 0
    "billing-engine"                          = 0
    "agent-runtime-adapter-digital-marketing" = 0
  }
}

resource "azurerm_user_assigned_identity" "member" {
  for_each = local.active_members

  name                = "id-${var.environment}-${each.key}"
  location            = var.location
  resource_group_name = var.resource_group_name
}

resource "azurerm_user_assigned_identity" "auth_redis" {
  count = local.auth_redis_container_enabled ? 1 : 0

  name                = "id-${var.environment}-auth-redis"
  location            = var.location
  resource_group_name = var.resource_group_name
}

resource "azurerm_role_assignment" "member_secret" {
  for_each = local.active_members

  scope                = var.key_vault_secret_resource_ids[local.credential_member[each.key]]
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.member[each.key].principal_id
}

resource "azurerm_role_assignment" "professional_runtime_bp_secret" {
  count = var.workload_enabled ? 1 : 0

  scope                = var.key_vault_secret_resource_ids["business-platform"]
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.member["professional-runtime"].principal_id
}

resource "azurerm_role_assignment" "identity_hmac_secret" {
  for_each             = var.workload_enabled ? local.identity_hmac_secret_resource_ids : {}
  scope                = each.value
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.member["business-platform"].principal_id
}

resource "azurerm_role_assignment" "identity_lifecycle_writer_secret" {
  for_each             = var.workload_enabled ? local.identity_lifecycle_writer_secret_resource_ids : {}
  scope                = each.value
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.member["business-platform"].principal_id
}

resource "azurerm_role_assignment" "identity_event_secret" {
  for_each = var.workload_enabled ? {
    for pair in setproduct(["business-platform", "web"], keys(local.identity_event_secret_resource_ids)) :
    "${pair[0]}:${pair[1]}" => {
      member = pair[0]
      scope  = local.identity_event_secret_resource_ids[pair[1]]
    }
  } : {}
  scope                = each.value.scope
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.member[each.value.member].principal_id
}

resource "azurerm_role_assignment" "continuity_hmac_secret" {
  for_each             = var.workload_enabled ? local.continuity_hmac_secret_resource_ids : {}
  scope                = each.value
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.member["business-platform"].principal_id
}

resource "azurerm_role_assignment" "conversation_cursor_secret" {
  for_each             = var.workload_enabled ? local.conversation_cursor_secret_resource_ids : {}
  scope                = each.value
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.member["business-platform"].principal_id
}

resource "azurerm_role_assignment" "web_session_secret" {
  for_each = var.workload_enabled ? local.web_session_secret_resource_ids : {}

  scope                = each.value
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.member["web"].principal_id
}

resource "azurerm_role_assignment" "auth_abuse_web_secret" {
  for_each = var.workload_enabled ? local.auth_abuse_secret_resource_ids : {}

  scope                = each.value
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.member["web"].principal_id
}

resource "azurerm_role_assignment" "auth_abuse_redis_secret" {
  count = local.auth_redis_container_enabled ? 1 : 0

  scope                = local.auth_abuse_secret_resource_ids["auth-abuse-redis-password"]
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.auth_redis[0].principal_id
}

resource "azurerm_role_assignment" "razorpay_secret" {
  for_each = var.workload_enabled ? local.razorpay_secret_resource_ids : {}

  scope                = each.value
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.member["billing-engine"].principal_id
}

resource "azurerm_container_app" "auth_redis" {
  count = local.auth_redis_container_enabled ? 1 : 0

  name                         = "ca-${var.environment}-auth-redis"
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  # Every app runs on the environment's only profile. Azure reports it as "Consumption" even when
  # omitted, so leaving it unset planned a 16-app no-op update (Consumption -> null) on every apply.
  workload_profile_name = "Consumption"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.auth_redis[0].id]
  }

  secret {
    name                = "auth-abuse-redis-password"
    identity            = azurerm_user_assigned_identity.auth_redis[0].id
    key_vault_secret_id = local.auth_abuse_secret_uris["auth-abuse-redis-password"]
  }

  template {
    min_replicas = local.runtime_dependencies_enabled ? 1 : 0
    max_replicas = 1

    container {
      name    = "auth-redis"
      image   = "redis@sha256:e7723ff73d963f5cc6d9c4643ea3d989527a402a319239054e9472a7fb9219a2"
      cpu     = 0.25
      memory  = "0.5Gi"
      command = ["/bin/sh", "-ec"]
      args = [<<-EOT
        umask 077
        printf 'bind 0.0.0.0\nprotected-mode yes\nport 6379\nsave ""\nappendonly no\nrequirepass %s\n' "$REDIS_PASSWORD" > /tmp/redis.conf
        redis-server /tmp/redis.conf &
        redis_pid=$!
        trap 'kill "$redis_pid"; wait "$redis_pid"' TERM INT
        for attempt in $(seq 1 30); do
          REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli ping >/dev/null 2>&1 && break
          test "$attempt" != 30 || exit 1
          sleep 1
        done
        epoch_ms="$(date +%s)000"
        REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli SET \
          "waooaw:$WAOOAW_ENVIRONMENT:auth-abuse:v1:epoch" "$epoch_ms" NX >/dev/null
        unset REDIS_PASSWORD REDISCLI_AUTH
        wait "$redis_pid"
      EOT
      ]

      env {
        name        = "REDIS_PASSWORD"
        secret_name = "auth-abuse-redis-password"
      }

      env {
        name  = "WAOOAW_ENVIRONMENT"
        value = var.environment
      }

      startup_probe {
        transport               = "TCP"
        port                    = 6379
        interval_seconds        = 5
        timeout                 = 3
        failure_count_threshold = 30
      }

      liveness_probe {
        transport               = "TCP"
        port                    = 6379
        interval_seconds        = 10
        timeout                 = 3
        failure_count_threshold = 3
      }

      readiness_probe {
        transport               = "TCP"
        port                    = 6379
        interval_seconds        = 10
        timeout                 = 3
        failure_count_threshold = 3
        success_count_threshold = 1
      }
    }
  }

  ingress {
    external_enabled = false
    exposed_port     = 6379
    target_port      = 6379
    transport        = "tcp"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  lifecycle {
    precondition {
      condition     = var.environment != "prod"
      error_message = "Production authentication limiting requires the separately approved private HA Redis foundation dependency."
    }
  }

  depends_on = [
    azurerm_role_assignment.auth_abuse_redis_secret,
  ]
}

resource "azurerm_user_assigned_identity" "pgbouncer" {
  count = var.workload_enabled && var.persistent_state_enabled ? 1 : 0

  name                = "id-${var.environment}-pgbouncer"
  location            = var.location
  resource_group_name = var.resource_group_name
}

resource "azurerm_role_assignment" "pgbouncer_database_secret" {
  count = var.workload_enabled && var.persistent_state_enabled ? 1 : 0

  scope                = var.database_secret_resource_ids["pgbouncer"]
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.pgbouncer[0].principal_id
}

resource "azurerm_container_app" "pgbouncer" {
  count = var.workload_enabled && var.persistent_state_enabled ? 1 : 0

  name                         = "ca-${var.environment}-pgbouncer"
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  # Every app runs on the environment's only profile. Azure reports it as "Consumption" even when
  # omitted, so leaving it unset planned a 16-app no-op update (Consumption -> null) on every apply.
  workload_profile_name = "Consumption"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.pgbouncer[0].id]
  }

  secret {
    name                = "pgbouncer-auth"
    identity            = azurerm_user_assigned_identity.pgbouncer[0].id
    key_vault_secret_id = var.database_secret_uris["pgbouncer"]
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "pgbouncer"
      image  = "docker.io/pgbouncer/pgbouncer@sha256:e8162131a43c54cd0ac7941e66eaaa802c5e5a49036f41b41260b70b290feea9"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name = "DATABASES"
        value = join(",", concat(
          var.environment == "demo" ? [
            "waooaw_temporal = host=${var.postgresql_server_fqdn} port=5432 pool_mode=session pool_size=8",
            "waooaw_temporal_visibility = host=${var.postgresql_server_fqdn} port=5432 pool_mode=session pool_size=8",
          ] : [],
          ["* = host=${var.postgresql_server_fqdn} port=5432"],
        ))
      }
      env {
        name  = "PGBOUNCER_AUTH_TYPE"
        value = "scram-sha-256"
      }
      env {
        name  = "PGBOUNCER_AUTH_FILE"
        value = "/mnt/secrets/pgbouncer-auth"
      }
      env {
        name  = "PGBOUNCER_STATS_USERS"
        value = var.environment == "demo" ? "temporal_runtime" : ""
      }
      env {
        name  = "PGBOUNCER_POOL_MODE"
        value = "transaction"
      }
      env {
        name  = "PGBOUNCER_LISTEN_PORT"
        value = "5432"
      }
      env {
        name  = "PGBOUNCER_MAX_CLIENT_CONN"
        value = var.environment == "demo" ? "40" : "80"
      }
      env {
        # Demo serves one replica per application to a handful of users; its transaction pools hold
        # two warm backends per role and release idle ones after 30 s. Run 39557651135 measured a
        # healthy Demo at 26 steady-state backends with 8/2 pools and a 300 s idle hold.
        name  = "PGBOUNCER_DEFAULT_POOL_SIZE"
        value = var.environment == "demo" ? "2" : "80"
      }
      env {
        name  = "PGBOUNCER_RESERVE_POOL_SIZE"
        value = var.environment == "demo" ? "0" : "20"
      }
      env {
        name  = "PGBOUNCER_RESERVE_POOL_TIMEOUT"
        value = "3"
      }
      env {
        name  = "PGBOUNCER_QUERY_WAIT_TIMEOUT"
        value = "5"
      }
      env {
        name  = "PGBOUNCER_CLIENT_IDLE_TIMEOUT"
        value = "60"
      }
      env {
        name  = "PGBOUNCER_SERVER_IDLE_TIMEOUT"
        value = var.environment == "demo" ? "30" : "300"
      }
      env {
        name  = "PGBOUNCER_SERVER_LIFETIME"
        value = "3600"
      }
      env {
        name  = "PGBOUNCER_SERVER_CONNECT_TIMEOUT"
        value = "15"
      }
      env {
        name  = "PGBOUNCER_SERVER_LOGIN_RETRY"
        value = "5"
      }
      env {
        name  = "PGBOUNCER_SERVER_TLS_SSLMODE"
        value = "verify-full"
      }
      env {
        name  = "PGBOUNCER_SERVER_TLS_CA_FILE"
        value = "/etc/ssl/certs/ca-certificates.crt"
      }
      env {
        name  = "PGBOUNCER_SERVER_RESET_QUERY"
        value = "DISCARD ALL"
      }
      env {
        name  = "PGBOUNCER_SERVER_RESET_QUERY_ALWAYS"
        value = "1"
      }

      startup_probe {
        transport               = "TCP"
        port                    = 5432
        interval_seconds        = 5
        timeout                 = 3
        failure_count_threshold = 30
      }

      readiness_probe {
        transport               = "TCP"
        port                    = 5432
        interval_seconds        = 10
        timeout                 = 3
        failure_count_threshold = 3
      }

      volume_mounts {
        name = "pgbouncer-secrets"
        path = "/mnt/secrets"
      }
    }

    volume {
      name         = "pgbouncer-secrets"
      storage_type = "Secret"
    }
  }

  ingress {
    external_enabled = false
    target_port      = 5432
    exposed_port     = 5432
    transport        = "tcp"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [azurerm_role_assignment.pgbouncer_database_secret]
}

resource "azurerm_role_assignment" "member_database_secret" {
  for_each = var.workload_enabled && var.persistent_state_enabled ? local.database_members : toset([])

  scope                = var.database_secret_resource_ids[each.key]
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.member[each.key].principal_id
}

resource "azurerm_container_app" "member" {
  for_each = local.active_members

  name                         = local.member_names[each.key]
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Multiple"
  # Every app runs on the environment's only profile. Azure reports it as "Consumption" even when
  # omitted, so leaving it unset planned a 16-app no-op update (Consumption -> null) on every apply.
  workload_profile_name = "Consumption"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.member[each.key].id]
  }

  secret {
    name                = "runtime-reference"
    identity            = azurerm_user_assigned_identity.member[each.key].id
    key_vault_secret_id = var.key_vault_secret_uris[local.credential_member[each.key]]
  }

  dynamic "secret" {
    for_each = var.persistent_state_enabled && contains(local.database_members, each.key) ? [1] : []
    content {
      name                = "database-credential"
      identity            = azurerm_user_assigned_identity.member[each.key].id
      key_vault_secret_id = var.database_secret_uris[each.key]
    }
  }

  dynamic "secret" {
    for_each = each.key == "business-platform" ? local.identity_reader_secret_uris : {}
    content {
      name                = secret.key
      identity            = azurerm_user_assigned_identity.member[each.key].id
      key_vault_secret_id = secret.value
    }
  }

  dynamic "secret" {
    for_each = each.key == "business-platform" ? local.identity_hmac_secret_uris : {}
    content {
      name                = secret.key
      identity            = azurerm_user_assigned_identity.member[each.key].id
      key_vault_secret_id = secret.value
    }
  }

  dynamic "secret" {
    for_each = each.key == "business-platform" ? local.identity_lifecycle_writer_secret_uris : {}
    content {
      name                = secret.key
      identity            = azurerm_user_assigned_identity.member[each.key].id
      key_vault_secret_id = secret.value
    }
  }

  dynamic "secret" {
    for_each = contains(["business-platform", "web"], each.key) ? local.identity_event_secret_uris : {}
    content {
      name                = secret.key
      identity            = azurerm_user_assigned_identity.member[each.key].id
      key_vault_secret_id = secret.value
    }
  }

  dynamic "secret" {
    for_each = each.key == "business-platform" ? local.continuity_hmac_secret_uris : {}
    content {
      name                = secret.key
      identity            = azurerm_user_assigned_identity.member[each.key].id
      key_vault_secret_id = secret.value
    }
  }

  dynamic "secret" {
    for_each = each.key == "business-platform" ? local.conversation_cursor_secret_uris : {}
    content {
      name                = secret.key
      identity            = azurerm_user_assigned_identity.member[each.key].id
      key_vault_secret_id = secret.value
    }
  }

  dynamic "secret" {
    for_each = each.key == "web" ? local.auth_abuse_secret_uris : {}
    content {
      name                = secret.key
      identity            = azurerm_user_assigned_identity.member[each.key].id
      key_vault_secret_id = secret.value
    }
  }

  dynamic "secret" {
    for_each = each.key == "web" ? local.web_session_secret_uris : {}
    content {
      name                = secret.key
      identity            = azurerm_user_assigned_identity.member[each.key].id
      key_vault_secret_id = secret.value
    }
  }

  dynamic "secret" {
    for_each = each.key == "billing-engine" ? local.razorpay_secret_uris : {}
    content {
      name                = secret.key
      identity            = azurerm_user_assigned_identity.member[each.key].id
      key_vault_secret_id = secret.value
    }
  }

  dynamic "secret" {
    for_each = each.key == "professional-runtime" ? [1] : []
    content {
      name                = "bp-service-credential"
      identity            = azurerm_user_assigned_identity.member[each.key].id
      key_vault_secret_id = var.key_vault_secret_uris["business-platform"]
    }
  }

  template {
    min_replicas = local.minimum_replicas[each.key]
    max_replicas = var.max_replicas

    container {
      name   = local.container_names[each.key]
      image  = var.image_digests[each.key]
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = local.credential_environment[each.key]
        secret_name = "runtime-reference"
      }

      dynamic "env" {
        for_each = each.key == "professional-runtime" ? [1] : []
        content {
          name        = "BP_SERVICE_JWT_SECRET"
          secret_name = "bp-service-credential"
        }
      }

      dynamic "env" {
        for_each = each.key == "web" ? [1] : []
        content {
          name        = "NEXTAUTH_SECRET"
          secret_name = "runtime-reference"
        }
      }

      dynamic "env" {
        for_each = var.persistent_state_enabled && contains(local.database_members, each.key) ? [1] : []
        content {
          name        = each.key == "billing-engine" ? "DATABASE_URL" : "ConnectionStrings__DefaultConnection"
          secret_name = "database-credential"
        }
      }

      dynamic "env" {
        for_each = each.key == "business-platform" ? local.identity_reader_secret_uris : {}
        content {
          name        = "IdentityBrokerRead__ClientSecret"
          secret_name = env.key
        }
      }

      dynamic "env" {
        for_each = each.key == "business-platform" ? local.identity_hmac_secret_uris : {}
        content {
          name        = "Identity__Hmac__Key"
          secret_name = env.key
        }
      }

      dynamic "env" {
        for_each = each.key == "business-platform" ? local.identity_lifecycle_writer_secret_uris : {}
        content {
          name        = "IdentityLifecycleWriter__ClientSecret"
          secret_name = env.key
        }
      }

      dynamic "env" {
        for_each = contains(["business-platform", "web"], each.key) ? local.identity_event_secret_uris : {}
        content {
          name        = each.key == "web" ? "IDENTITY_EVENT_SIGNING_KEY" : "IdentitySecurityEvents__Ingest__SigningKey"
          secret_name = env.key
        }
      }

      dynamic "env" {
        for_each = each.key == "business-platform" ? local.continuity_hmac_secret_uris : {}
        content {
          name        = "ChannelContinuity__EnvelopeHmacKey"
          secret_name = env.key
        }
      }

      dynamic "env" {
        for_each = each.key == "business-platform" ? local.conversation_cursor_secret_uris : {}
        content {
          name        = "Conversation__CursorHmacKey"
          secret_name = env.key
        }
      }

      dynamic "env" {
        for_each = each.key == "web" ? local.auth_abuse_secret_environment : {}
        content {
          name        = env.value
          secret_name = env.key
        }
      }

      dynamic "env" {
        for_each = each.key == "web" ? local.active_web_session_secret_environment : {}
        content {
          name        = env.value
          secret_name = env.key
        }
      }

      dynamic "env" {
        for_each = each.key == "billing-engine" ? {
          RAZORPAY_KEY_ID         = "razorpay-test-key-id"
          RAZORPAY_KEY_SECRET     = "razorpay-test-key-secret"
          RAZORPAY_WEBHOOK_SECRET = "razorpay-test-webhook-secret"
        } : {}
        content {
          name        = env.key
          secret_name = env.value
        }
      }

      dynamic "env" {
        for_each = each.key == "business-platform" ? [1] : []
        content {
          name  = "Identity__Hmac__ActiveVersion"
          value = var.identity_hmac_active_version
        }
      }

      dynamic "env" {
        for_each = local.runtime_environment[each.key]
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        # Successful probe requests dominated Demo ingestion; application/audit categories remain unchanged.
        for_each = var.environment == "demo" && contains(["business-platform", "constitutional-engine"], each.key) ? {
          "Logging__LogLevel__Microsoft.AspNetCore.Hosting.Diagnostics"        = "Warning"
          "Logging__LogLevel__Microsoft.AspNetCore.Routing.EndpointMiddleware" = "Warning"
        } : {}
        content {
          name  = env.key
          value = env.value
        }
      }

      startup_probe {
        transport               = "TCP"
        port                    = local.target_ports[each.key]
        interval_seconds        = 5
        timeout                 = 3
        failure_count_threshold = 30
      }

      dynamic "liveness_probe" {
        for_each = each.key == "web" ? [1] : []
        content {
          transport               = "HTTP"
          port                    = local.target_ports[each.key]
          path                    = "/api/health/live"
          interval_seconds        = 10
          timeout                 = 3
          failure_count_threshold = 3
        }
      }

      dynamic "readiness_probe" {
        for_each = each.key == "constitutional-engine" ? [] : [1]
        content {
          transport               = "HTTP"
          port                    = local.target_ports[each.key]
          path                    = local.readiness_paths[each.key]
          interval_seconds        = 10
          timeout                 = 3
          failure_count_threshold = 3
          success_count_threshold = 1
        }
      }

      dynamic "readiness_probe" {
        for_each = each.key == "constitutional-engine" ? [1] : []
        content {
          transport               = "TCP"
          port                    = local.target_ports[each.key]
          interval_seconds        = 10
          timeout                 = 3
          failure_count_threshold = 3
          success_count_threshold = 1
        }
      }
    }

  }

  ingress {
    external_enabled = local.public_ingress[each.key]
    target_port      = local.target_ports[each.key]
    transport        = local.ingress_transports[each.key]

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }

  }

  lifecycle {
    precondition {
      condition = var.environment != "demo" || (
        local.demo_identity_manifest.origins.web == local.service_urls.web &&
        local.demo_identity_manifest.origins.identity == local.service_urls.identity_edge &&
        local.demo_identity_manifest.origins.api == local.service_urls.public_api
      )
      error_message = "Demo deployment origins must match the reviewed identity manifest; domain changes require manifest and callback approval."
    }
    precondition {
      condition     = toset(keys(var.image_digests)) == local.release_members
      error_message = "Release membership must be exactly CE, BP, PR, AIR, Web, and Billing."
    }

    precondition {
      condition     = !var.workload_enabled || var.ghcr_packages_public
      error_message = "Enabled workloads require administrator verification that all exact-seven GHCR packages allow anonymous digest pulls."
    }
  }

  depends_on = [
    azurerm_role_assignment.member_secret,
    azurerm_role_assignment.professional_runtime_bp_secret,
    azurerm_role_assignment.identity_reader_secret,
    azurerm_role_assignment.identity_hmac_secret,
    azurerm_role_assignment.identity_event_secret,
    azurerm_role_assignment.continuity_hmac_secret,
    azurerm_role_assignment.conversation_cursor_secret,
    azurerm_role_assignment.auth_abuse_web_secret,
    azurerm_role_assignment.razorpay_secret,
    azurerm_role_assignment.member_database_secret,
    azurerm_container_app.pgbouncer,
    azurerm_container_app.auth_redis,
    azurerm_container_app.temporal,
  ]
}

resource "azurerm_container_app_custom_domain" "public_member" {
  for_each = var.workload_enabled ? {
    for member, hostname in {
      web               = var.web_custom_hostname
      business-platform = var.api_custom_hostname
    } : member => hostname if hostname != null
  } : {}

  name             = each.value
  container_app_id = azurerm_container_app.member[each.key].id

  lifecycle {
    ignore_changes = [certificate_binding_type, container_app_environment_certificate_id]
  }
}

resource "azurerm_user_assigned_identity" "temporal" {
  count = var.workload_enabled && var.environment == "demo" ? 1 : 0

  name                = "id-${var.environment}-temporal"
  location            = var.location
  resource_group_name = var.resource_group_name
}

resource "azurerm_role_assignment" "temporal_secret" {
  count = var.workload_enabled && var.environment == "demo" ? 1 : 0

  scope                = var.database_secret_resource_ids["temporal"]
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.temporal[0].principal_id
}

resource "azurerm_user_assigned_identity" "temporal_migration" {
  count = var.workload_enabled && var.environment == "demo" ? 1 : 0

  name                = "id-${var.environment}-temporal-migration"
  location            = var.location
  resource_group_name = var.resource_group_name
}

resource "azurerm_role_assignment" "temporal_migration_database_secret" {
  count = var.workload_enabled && var.environment == "demo" ? 1 : 0

  scope                = var.database_secret_resource_ids["temporal-migration"]
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.temporal_migration[0].principal_id
}

resource "azurerm_container_app_job" "temporal_migration" {
  count = var.workload_enabled && var.environment == "demo" ? 1 : 0

  name                         = "job-${var.environment}-temporal-migration"
  location                     = var.location
  resource_group_name          = var.resource_group_name
  container_app_environment_id = var.container_app_environment_id
  replica_retry_limit          = 1
  replica_timeout_in_seconds   = 1200

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.temporal_migration[0].id]
  }

  secret {
    name                = "migration-database"
    identity            = azurerm_user_assigned_identity.temporal_migration[0].id
    key_vault_secret_id = var.database_secret_uris["temporal-migration"]
  }

  manual_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
  }

  template {
    container {
      name    = "temporal-migration"
      image   = "temporalio/auto-setup@sha256:98cdb6b5e02d64cb933864a9ba91cb66065eb320623a0dafdf44beba535bca88"
      cpu     = 0.5
      memory  = "1Gi"
      command = ["/bin/bash", "-c"]
      args = [<<-EOT
        set -euo pipefail
        export SQL_PASSWORD="$POSTGRES_PWD"
        migrate() {
          database="$1"
          schema_directory="$2"
          temporal-sql-tool \
            --plugin postgres12 \
            --endpoint "$POSTGRES_SEEDS" \
            --port 5432 \
            --user temporal_migrator \
            --database "$database" \
            --tls \
            --tls-ca-file /etc/ssl/certs/ca-certificates.crt \
            --tls-server-name "$POSTGRES_SEEDS" \
            setup-schema --version 0.0
          temporal-sql-tool \
            --plugin postgres12 \
            --endpoint "$POSTGRES_SEEDS" \
            --port 5432 \
            --user temporal_migrator \
            --database "$database" \
            --tls \
            --tls-ca-file /etc/ssl/certs/ca-certificates.crt \
            --tls-server-name "$POSTGRES_SEEDS" \
            update-schema --schema-dir "$schema_directory"
        }
        migrate waooaw_temporal /etc/temporal/schema/postgresql/v12/temporal/versioned
        migrate waooaw_temporal_visibility /etc/temporal/schema/postgresql/v12/visibility/versioned
      EOT
      ]

      env {
        name  = "POSTGRES_SEEDS"
        value = var.postgresql_server_fqdn
      }
      env {
        name        = "POSTGRES_PWD"
        secret_name = "migration-database"
      }
    }
  }

  depends_on = [
    azurerm_role_assignment.temporal_migration_database_secret,
  ]
}

resource "azurerm_container_app_job" "temporal_startup_qualification" {
  count = var.workload_enabled && var.environment == "demo" ? 1 : 0

  name                         = "job-${var.environment}-temporal-startup"
  location                     = var.location
  resource_group_name          = var.resource_group_name
  container_app_environment_id = var.container_app_environment_id
  replica_retry_limit          = 0
  replica_timeout_in_seconds   = 300

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.temporal[0].id]
  }

  secret {
    name                = "postgres-password"
    identity            = azurerm_user_assigned_identity.temporal[0].id
    key_vault_secret_id = var.database_secret_uris["temporal"]
  }

  manual_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
  }

  template {
    container {
      name    = "temporal-startup-qualification"
      image   = "temporalio/auto-setup@sha256:98cdb6b5e02d64cb933864a9ba91cb66065eb320623a0dafdf44beba535bca88"
      cpu     = 1
      memory  = "2Gi"
      command = ["/bin/bash", "-c"]
      args = [<<-EOT
        set -euo pipefail
        log=/tmp/temporal-startup.log
        # The Temporal image has no psql (run 40542694439 exited 127). The pool-sampler container in
        # this replica samples PgBouncer and returns the raw samples as a tar stream on loopback
        # port 17300; this container signals its own exit to the sampler on loopback port 17301.
        samples=/tmp/pool-samples
        mkdir -p "$samples"
        nc -l -p 17300 > /tmp/pool-samples.tar &
        receiver_pid=$!
        readiness_pid=
        export TEMPORAL_BROADCAST_ADDRESS="$(hostname -i | awk '{print $1}')"
        export TEMPORAL_ADDRESS="127.0.0.1:7233"
        /etc/temporal/entrypoint.sh autosetup >"$log" 2>&1 &
        temporal_pid=$!
        cleanup() {
          printf 'exited\n' | nc -w 2 127.0.0.1 17301 >/dev/null 2>&1 || true
          kill "$receiver_pid" 2>/dev/null || true
          if [ -n "$readiness_pid" ]; then kill "$readiness_pid" 2>/dev/null || true; fi
          kill "$temporal_pid" 2>/dev/null || true
          wait "$temporal_pid" 2>/dev/null || true
          # Keep the 60 samples/result inside Azure's 300-line console retrieval limit.
          tail -n 150 "$log"
          cat "$samples/sampler.log" 2>/dev/null || true
        }
        trap cleanup EXIT
        ready=false
        for attempt in $(seq 1 30); do
          kill -0 "$temporal_pid"
          if timeout 2 temporal operator cluster health --address 127.0.0.1:7233 >>"$log" 2>&1; then
            ready=true
            break
          fi
          sleep 3
        done
        test "$ready" = true
        nc -l -p 17302 >/dev/null &
        readiness_pid=$!
        sampler_finished=false
        for tick in $(seq 1 120); do
          kill -0 "$temporal_pid"
          timeout 3 bash -c 'exec 3<>/dev/tcp/127.0.0.1/7233'
          if ! kill -0 "$receiver_pid" 2>/dev/null; then
            sampler_finished=true
            break
          fi
          sleep 1
        done
        test "$sampler_finished" = true
        tar -xf /tmp/pool-samples.tar -C "$samples"
        if [ -e "$samples/sampler.failed" ]; then
          echo "WC-124 pool sampler failed with status $(cat "$samples/sampler.failed")" >&2
          cat "$samples/sampler.log" >&2
          exit 1
        fi
        test -e "$samples/sampler.done"
        max_waiting=0
        max_wait_seconds=0
        min_headroom=999
        for sample in $(seq 1 60); do
          pools="$samples/pools-$sample.csv"
          waiting=$(awk -F, '
            NR == 1 {
              for (i = 1; i <= NF; i++) column[$i] = i
              if (!("cl_waiting" in column)) exit 2
              next
            }
            ($1 == "waooaw_temporal" || $1 == "waooaw_temporal_visibility") {
              if ($(column["cl_waiting"]) > maximum) maximum = $(column["cl_waiting"])
            }
            END {print maximum + 0}
          ' "$pools")
          wait_seconds=$(awk -F, '
            NR == 1 {
              for (i = 1; i <= NF; i++) column[$i] = i
              if (!("maxwait" in column)) exit 2
              next
            }
            ($1 == "waooaw_temporal" || $1 == "waooaw_temporal_visibility") {
              if ($(column["maxwait"]) > maximum) maximum = $(column["maxwait"])
            }
            END {print maximum + 0}
          ' "$pools")
          headroom=$(cat "$samples/headroom-$sample.txt")
          [[ "$headroom" =~ ^-?[0-9]+$ ]]
          if (( waiting > max_waiting )); then max_waiting=$waiting; fi
          if (( wait_seconds > max_wait_seconds )); then max_wait_seconds=$wait_seconds; fi
          if (( headroom < min_headroom )); then min_headroom=$headroom; fi
          printf 'WC124_POOL_SAMPLE sample=%d cl_waiting=%d maxwait=%d postgres_headroom=%d\n' \
            "$sample" "$waiting" "$wait_seconds" "$headroom"
        done
        printf 'WC124_POOL_SUMMARY max_waiting=%d max_wait_seconds=%d minimum_headroom=%d\n' \
          "$max_waiting" "$max_wait_seconds" "$min_headroom"
        test "$max_waiting" = 0
        test "$max_wait_seconds" = 0
        test "$min_headroom" -ge 5
        ! grep -Eq 'driver: bad connection|query_wait_timeout' "$log"
        printf '{"schema":"waooaw.wc124-temporal-startup/v1","qualification_seconds":60,"max_waiting_clients":%d,"max_wait_seconds":%d,"minimum_postgresql_headroom":%d,"status":"passed"}\n' \
          "$max_waiting" "$max_wait_seconds" "$min_headroom"
      EOT
      ]

      env {
        name  = "BIND_ON_IP"
        value = "0.0.0.0"
      }
      env {
        name  = "DB"
        value = "postgres12"
      }
      env {
        name  = "DB_PORT"
        value = "5432"
      }
      env {
        name  = "DBNAME"
        value = "waooaw_temporal"
      }
      env {
        name  = "VISIBILITY_DBNAME"
        value = "waooaw_temporal_visibility"
      }
      env {
        name  = "POSTGRES_USER"
        value = "temporal_runtime"
      }
      env {
        name        = "POSTGRES_PWD"
        secret_name = "postgres-password"
      }
      env {
        name  = "POSTGRES_SEEDS"
        value = local.pgbouncer_host
      }
      env {
        name  = "SKIP_SCHEMA_SETUP"
        value = "true"
      }
      env {
        name  = "SKIP_DB_CREATE"
        value = "true"
      }
      env {
        name  = "SQL_MAX_CONNS"
        value = "1"
      }
      env {
        name  = "SQL_MAX_IDLE_CONNS"
        value = "1"
      }
      env {
        name  = "SQL_VIS_MAX_CONNS"
        value = "1"
      }
      env {
        name  = "SQL_VIS_MAX_IDLE_CONNS"
        value = "1"
      }
    }

    container {
      name    = "pool-sampler"
      image   = "docker.io/library/postgres@sha256:0cefaabd882e42bcb2a2f3dc56d3ce4770560ba62fd7f197f1a2e008fd5731ab"
      cpu     = 0.25
      memory  = "0.5Gi"
      command = ["/bin/sh", "-c"]
      args = [<<-EOT
        set -eu
        out=/tmp/pool-samples
        mkdir -p "$out"
        : > /tmp/temporal-exited
        nc -l -p 17301 > /tmp/temporal-exited &
        deliver() {
          tar -C "$out" -cf - . | nc -w 5 127.0.0.1 17300
        }
        trap 'status=$?; if [ "$status" -ne 0 ]; then echo "$status" > "$out/sampler.failed"; deliver || true; fi' EXIT
        ready=false
        for attempt in $(seq 1 240); do
          if [ -s /tmp/temporal-exited ]; then
            echo "Temporal exited before accepting connections on 7233" >&2
            exit 1
          fi
          if nc -z -w 3 127.0.0.1 17302; then
            ready=true
            break
          fi
          sleep 1
        done
        test "$ready" = true
        export PGPASSWORD="$POSTGRES_PWD"
        # A listening Temporal frontend is not a settled PgBouncer pool. Retain every warmup
        # observation; require five clean seconds within 30 before the separate strict window.
        clean=0
        for warmup in $(seq 1 30); do
          nc -z -w 3 127.0.0.1 7233
          psql --no-psqlrc --set ON_ERROR_STOP=1 \
            --host "$POSTGRES_SEEDS" --port 5432 --username temporal_runtime \
            --dbname pgbouncer --csv --command 'SHOW POOLS;' \
            > "$out/warmup-$warmup.csv" 2>> "$out/sampler.log"
          if awk -F, '
            NR == 1 {for (i=1; i<=NF; i++) column[$i]=i; next}
            ($1 == "waooaw_temporal" || $1 == "waooaw_temporal_visibility") {
              seen++
              if (!("cl_waiting" in column) || !("maxwait" in column) ||
                  $(column["cl_waiting"]) != 0 || $(column["maxwait"]) != 0) bad=1
            }
            END {exit (seen < 2 || bad)}
          ' "$out/warmup-$warmup.csv"; then
            clean=$((clean + 1))
          else
            clean=0
          fi
          sleep 1
          if [ "$clean" -ge 5 ]; then break; fi
        done
        echo "WC124_POOL_WARMUP samples=$warmup clean_seconds=$clean" >> "$out/sampler.log"
        if [ "$clean" -lt 5 ]; then
          echo "PgBouncer did not settle within the 30-second warmup" >> "$out/sampler.log"
          exit 1
        fi
        for sample in $(seq 1 60); do
          nc -z -w 3 127.0.0.1 7233
          echo "WC124_POOL_PHASE sample=$sample phase=show_pools" >> "$out/sampler.log"
          psql --no-psqlrc --set ON_ERROR_STOP=1 \
            --host "$POSTGRES_SEEDS" --port 5432 --username temporal_runtime \
            --dbname pgbouncer --csv --command 'SHOW POOLS;' \
            > "$out/pools-$sample.csv" 2>> "$out/sampler.log"
          echo "WC124_POOL_PHASE sample=$sample phase=direct_headroom" >> "$out/sampler.log"
          PGSSLMODE=require PGCONNECT_TIMEOUT=5 psql --no-psqlrc --set ON_ERROR_STOP=1 \
            --host "$MONITOR_POSTGRES_HOST" --port 5432 --username temporal_runtime \
            --dbname waooaw_temporal --tuples-only --no-align --command "
              SELECT current_setting('max_connections')::int
                   - current_setting('superuser_reserved_connections')::int
                   - current_setting('reserved_connections')::int
                   - count(*)
              FROM pg_stat_activity
              WHERE backend_type = 'client backend';
            " > "$out/headroom-$sample.txt" 2>> "$out/sampler.log"
          sleep 1
        done
        : > "$out/sampler.done"
        deliver
      EOT
      ]

      env {
        name        = "POSTGRES_PWD"
        secret_name = "postgres-password"
      }
      env {
        name  = "POSTGRES_SEEDS"
        value = local.pgbouncer_host
      }
      env {
        name  = "MONITOR_POSTGRES_HOST"
        value = var.postgresql_server_fqdn
      }
    }
  }

  depends_on = [
    azurerm_role_assignment.temporal_secret,
  ]
}

resource "azurerm_role_assignment" "keycloak_database_secret" {
  count = var.workload_enabled && var.persistent_state_enabled ? 1 : 0

  scope                = var.database_secret_resource_ids["keycloak"]
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.member["web"].principal_id
}

resource "azurerm_user_assigned_identity" "keycloak_migration" {
  count = var.workload_enabled && var.persistent_state_enabled ? 1 : 0

  name                = "id-${var.environment}-keycloak-migration"
  location            = var.location
  resource_group_name = var.resource_group_name
}

resource "azurerm_role_assignment" "keycloak_migration_database_secret" {
  count = var.workload_enabled && var.persistent_state_enabled ? 1 : 0

  scope                = var.database_secret_resource_ids["keycloak-migration"]
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.keycloak_migration[0].principal_id
}

resource "azurerm_role_assignment" "keycloak_migration_realm_credential" {
  count = var.workload_enabled && var.persistent_state_enabled ? 1 : 0

  scope                = var.key_vault_secret_resource_ids["web"]
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.keycloak_migration[0].principal_id
}

resource "azurerm_role_assignment" "keycloak_migration_realm_secrets" {
  for_each = var.workload_enabled && var.persistent_state_enabled ? local.keycloak_migration_optional_secrets : {}

  scope                = each.value.resource_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.keycloak_migration[0].principal_id
}

resource "azurerm_container_app_job" "keycloak_migration" {
  count = var.workload_enabled && var.persistent_state_enabled ? 1 : 0

  name                         = "job-${var.environment}-keycloak-migration"
  location                     = var.location
  resource_group_name          = var.resource_group_name
  container_app_environment_id = var.container_app_environment_id
  replica_retry_limit          = 1
  replica_timeout_in_seconds   = 1200

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.keycloak_migration[0].id]
  }

  secret {
    name                = "migration-database"
    identity            = azurerm_user_assigned_identity.keycloak_migration[0].id
    key_vault_secret_id = var.database_secret_uris["keycloak-migration"]
  }

  secret {
    name                = "realm-credential"
    identity            = azurerm_user_assigned_identity.keycloak_migration[0].id
    key_vault_secret_id = var.key_vault_secret_uris["web"]
  }

  dynamic "secret" {
    for_each = local.keycloak_migration_optional_secrets
    content {
      name                = secret.key
      identity            = azurerm_user_assigned_identity.keycloak_migration[0].id
      key_vault_secret_id = secret.value.uri
    }
  }

  manual_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
  }

  template {
    container {
      name    = "keycloak-migration"
      image   = "quay.io/keycloak/keycloak@sha256:82c5b7a110456dbd42b86ea572e728878549954cc8bd03cd65410d75328095d2"
      cpu     = 1
      memory  = "2Gi"
      command = ["/bin/bash", "-c"]
      args = [<<-EOT
        set -euo pipefail
        json_escape() {
          value="$1"
          value="$${value//\\/\\\\}"
          value="$${value//\"/\\\"}"
          value="$${value//$'\n'/\\n}"
          value="$${value//$'\r'/\\r}"
          value="$${value//$'\t'/\\t}"
          printf '%s' "$value"
        }
        replace_secret() {
          name="$1"
          escaped=$(json_escape "$2")
          placeholder='$''{'"$name"'}'
          realm="$${realm//$placeholder/$escaped}"
        }
        realm=$(printf '%s' '${local.keycloak_realm_base64}' | base64 --decode)
        replace_secret KEYCLOAK_CLIENT_SECRET "$KEYCLOAK_CLIENT_SECRET"
        ${var.environment == "demo" ? "replace_secret DEMO_FOUNDER_PASSWORD \"$DEMO_FOUNDER_PASSWORD\"" : ""}
        ${var.google_login_enabled ? "replace_secret GOOGLE_CLIENT_ID \"$GOOGLE_CLIENT_ID\"\n        replace_secret GOOGLE_CLIENT_SECRET \"$GOOGLE_CLIENT_SECRET\"" : ""}
        ${var.facebook_login_enabled ? "replace_secret META_LOGIN_CLIENT_ID \"$META_LOGIN_CLIENT_ID\"\n        replace_secret META_LOGIN_CLIENT_SECRET \"$META_LOGIN_CLIENT_SECRET\"" : ""}
        ${var.google_login_enabled || var.facebook_login_enabled ? "replace_secret BP_IDENTITY_READER_CLIENT_SECRET \"$BP_IDENTITY_READER_CLIENT_SECRET\"\n        replace_secret BP_IDENTITY_LIFECYCLE_WRITER_CLIENT_SECRET \"$BP_IDENTITY_LIFECYCLE_WRITER_CLIENT_SECRET\"" : ""}
        if printf '%s' "$realm" | grep -Eq '\$\{[A-Z0-9_]+\}'; then
          echo "Keycloak realm contains unresolved secret placeholders" >&2
          exit 1
        fi
        printf '%s' "$realm" > /tmp/waooaw-realm.json
        exec /opt/keycloak/bin/kc.sh import --file /tmp/waooaw-realm.json --override true
      EOT
      ]

      env {
        name  = "KC_DB"
        value = "postgres"
      }
      env {
        name  = "KC_DB_URL_HOST"
        value = var.postgresql_server_fqdn
      }
      env {
        name  = "KC_DB_URL_PORT"
        value = "5432"
      }
      env {
        name  = "KC_DB_URL_DATABASE"
        value = "waooaw_keycloak"
      }
      env {
        name  = "KC_DB_URL_PROPERTIES"
        value = "?sslmode=verify-full&sslrootcert=/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem&prepareThreshold=0"
      }
      env {
        name  = "KC_DB_USERNAME"
        value = "keycloak_migrator"
      }
      # Connection budget on the single provisioned instance (Demo usable slots = 40 - reserved 15).
      env {
        name  = "KC_DB_POOL_INITIAL_SIZE"
        value = "1"
      }
      env {
        name  = "KC_DB_POOL_MIN_SIZE"
        value = "1"
      }
      env {
        name  = "KC_DB_POOL_MAX_SIZE"
        value = "5"
      }
      env {
        name        = "KC_DB_PASSWORD"
        secret_name = "migration-database"
      }
      env {
        name        = "KEYCLOAK_CLIENT_SECRET"
        secret_name = "realm-credential"
      }
      dynamic "env" {
        for_each = var.environment == "demo" ? [1] : []
        content {
          name        = "DEMO_FOUNDER_PASSWORD"
          secret_name = "realm-credential"
        }
      }
      dynamic "env" {
        for_each = local.keycloak_migration_optional_secrets
        content {
          name        = env.value.env_name
          secret_name = env.key
        }
      }
      env {
        name  = "KC_SPI_CONNECTIONS_JPA_QUARKUS_MIGRATION_STRATEGY"
        value = "update"
      }
      env {
        name  = "KC_SPI_CONNECTIONS_JPA_QUARKUS_INITIALIZE_EMPTY"
        value = "true"
      }
    }
  }

  depends_on = [
    azurerm_role_assignment.keycloak_migration_database_secret,
    azurerm_role_assignment.keycloak_migration_realm_credential,
    azurerm_role_assignment.keycloak_migration_realm_secrets,
  ]
}

resource "azurerm_container_app" "temporal" {
  count = var.workload_enabled && var.environment == "demo" ? 1 : 0

  name                         = "ca-${var.environment}-temporal"
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  # Every app runs on the environment's only profile. Azure reports it as "Consumption" even when
  # omitted, so leaving it unset planned a 16-app no-op update (Consumption -> null) on every apply.
  workload_profile_name = "Consumption"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.temporal[0].id]
  }

  secret {
    name                = "postgres-password"
    identity            = azurerm_user_assigned_identity.temporal[0].id
    key_vault_secret_id = var.database_secret_uris["temporal"]
  }

  template {
    min_replicas = local.runtime_dependencies_enabled ? 1 : 0
    max_replicas = 1

    container {
      name   = "temporal"
      image  = "temporalio/auto-setup@sha256:98cdb6b5e02d64cb933864a9ba91cb66065eb320623a0dafdf44beba535bca88"
      cpu    = 1
      memory = "2Gi"
      # The image binds every listener to the replica IP only (BIND_ON_IP from getent), which
      # Container Apps' TCP probes cannot reach over loopback: every single-container revision
      # failed its startup probe while the frontend answered gRPC health from the network. Bind
      # on all interfaces, keep ringpop advertising the routable replica address, and point the
      # auto-setup CLI at loopback.
      command = ["/bin/bash", "-c"]
      args = [<<-EOT
        set -euo pipefail
        export TEMPORAL_BROADCAST_ADDRESS="$(hostname -i | awk '{print $1}')"
        export TEMPORAL_ADDRESS="127.0.0.1:7233"
        exec /etc/temporal/entrypoint.sh autosetup
      EOT
      ]
      env {
        name  = "BIND_ON_IP"
        value = "0.0.0.0"
      }

      env {
        name  = "DB"
        value = "postgres12"
      }
      env {
        name  = "DB_PORT"
        value = "5432"
      }
      env {
        name  = "DBNAME"
        value = "waooaw_temporal"
      }
      env {
        name  = "VISIBILITY_DBNAME"
        value = "waooaw_temporal_visibility"
      }
      env {
        name  = "POSTGRES_USER"
        value = "temporal_runtime"
      }
      env {
        name        = "POSTGRES_PWD"
        secret_name = "postgres-password"
      }
      env {
        name  = "POSTGRES_SEEDS"
        value = local.pgbouncer_host
      }
      env {
        name  = "SKIP_SCHEMA_SETUP"
        value = "true"
      }
      env {
        name  = "SKIP_DB_CREATE"
        value = "true"
      }
      # Temporal pools session-mode connections through PgBouncer against the single provisioned
      # instance (Demo: max_client_conn 40, server max_connections 50). The image default of 20
      # connections per store, per internal service (frontend/history/matching/worker x default +
      # visibility), exhausts both and starves every other runtime; bound each pool to 1. With 2 the
      # Demo steady state measured 28-29 backends against 25 ordinary slots (run 39460884155).
      env {
        name  = "SQL_MAX_CONNS"
        value = "1"
      }
      env {
        name  = "SQL_MAX_IDLE_CONNS"
        value = "1"
      }
      env {
        name  = "SQL_VIS_MAX_CONNS"
        value = "1"
      }
      env {
        name  = "SQL_VIS_MAX_IDLE_CONNS"
        value = "1"
      }
      # azurerm 4.14 caps failure_count_threshold at 30 (provider IntBetween(1, 30)); the plan,
      # not validate, rejects a higher value because this resource is count-gated. 30 x 6 s keeps
      # the 180 s startup window that auto-setup needs on a cold Demo PostgreSQL.
      startup_probe {
        transport               = "TCP"
        port                    = 7233
        interval_seconds        = 6
        timeout                 = 3
        failure_count_threshold = 30
      }
      readiness_probe {
        transport               = "TCP"
        port                    = 7233
        interval_seconds        = 10
        timeout                 = 3
        failure_count_threshold = 3
        success_count_threshold = 1
      }
      liveness_probe {
        transport               = "TCP"
        port                    = 7233
        interval_seconds        = 30
        timeout                 = 3
        failure_count_threshold = 3
      }
    }
  }

  depends_on = [
    azurerm_role_assignment.temporal_secret,
    azurerm_container_app.pgbouncer,
  ]

  ingress {
    external_enabled = false
    target_port      = 7233
    transport        = "http2"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}

resource "azurerm_container_app" "keycloak" {
  count = var.workload_enabled ? 1 : 0

  name                         = "ca-${var.environment}-keycloak"
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  # Every app runs on the environment's only profile. Azure reports it as "Consumption" even when
  # omitted, so leaving it unset planned a 16-app no-op update (Consumption -> null) on every apply.
  workload_profile_name = "Consumption"

  identity {
    type = "UserAssigned"
    identity_ids = concat(
      [azurerm_user_assigned_identity.member["web"].id],
      azurerm_user_assigned_identity.google_broker[*].id,
      azurerm_user_assigned_identity.facebook_broker[*].id,
      var.google_login_enabled || var.facebook_login_enabled ? [azurerm_user_assigned_identity.member["business-platform"].id] : [],
    )
  }

  secret {
    name                = "keycloak-credential"
    identity            = azurerm_user_assigned_identity.member["web"].id
    key_vault_secret_id = var.key_vault_secret_uris["web"]
  }

  dynamic "secret" {
    for_each = var.persistent_state_enabled ? [1] : []
    content {
      name                = "keycloak-database-credential"
      identity            = azurerm_user_assigned_identity.member["web"].id
      key_vault_secret_id = var.database_secret_uris["keycloak"]
    }
  }

  dynamic "secret" {
    for_each = local.google_secret_uris
    content {
      name                = secret.key
      identity            = azurerm_user_assigned_identity.google_broker[0].id
      key_vault_secret_id = secret.value
    }
  }

  dynamic "secret" {
    for_each = local.facebook_secret_uris
    content {
      name                = secret.key
      identity            = azurerm_user_assigned_identity.facebook_broker[0].id
      key_vault_secret_id = secret.value
    }
  }

  dynamic "secret" {
    for_each = local.identity_reader_secret_uris
    content {
      name                = secret.key
      identity            = azurerm_user_assigned_identity.member["business-platform"].id
      key_vault_secret_id = secret.value
    }
  }

  dynamic "secret" {
    for_each = local.identity_lifecycle_writer_secret_uris
    content {
      name                = secret.key
      identity            = azurerm_user_assigned_identity.member["business-platform"].id
      key_vault_secret_id = secret.value
    }
  }

  template {
    min_replicas = local.runtime_dependencies_enabled ? 1 : 0
    max_replicas = 1

    container {
      name    = "keycloak"
      image   = "quay.io/keycloak/keycloak@sha256:82c5b7a110456dbd42b86ea572e728878549954cc8bd03cd65410d75328095d2"
      cpu     = 1
      memory  = "2Gi"
      command = ["/bin/sh", "-c"]
      args = [<<-EOT
        set -eu
        ${var.google_login_enabled ? ": \"$${GOOGLE_CLIENT_ID:?Google client ID is required}\" \"$${GOOGLE_CLIENT_SECRET:?Google client secret is required}\"" : ""}
        ${var.facebook_login_enabled ? ": \"$${META_LOGIN_CLIENT_ID:?Meta login client ID is required}\" \"$${META_LOGIN_CLIENT_SECRET:?Meta login client secret is required}\"" : ""}
        ${var.google_login_enabled ? ": \"$${BP_IDENTITY_READER_CLIENT_SECRET:?BP identity reader client secret is required}\"" : ""}
        exec /opt/keycloak/bin/kc.sh start-dev --http-enabled=true --hostname-strict=false
      EOT
      ]

      startup_probe {
        transport               = "HTTP"
        port                    = 8080
        path                    = "/realms/waooaw/.well-known/openid-configuration"
        interval_seconds        = 5
        timeout                 = 3
        failure_count_threshold = 30
      }

      readiness_probe {
        transport               = "HTTP"
        port                    = 8080
        path                    = "/realms/waooaw/.well-known/openid-configuration"
        interval_seconds        = 10
        timeout                 = 3
        failure_count_threshold = 3
        success_count_threshold = 1
      }

      env {
        name  = "KEYCLOAK_ADMIN"
        value = "demo-admin"
      }
      env {
        name        = "KEYCLOAK_ADMIN_PASSWORD"
        secret_name = "keycloak-credential"
      }
      env {
        name        = "KEYCLOAK_CLIENT_SECRET"
        secret_name = "keycloak-credential"
      }
      env {
        name        = "DEMO_FOUNDER_PASSWORD"
        secret_name = "keycloak-credential"
      }
      env {
        name  = "KC_HOSTNAME"
        value = local.service_urls.identity_edge
      }
      env {
        name  = "KC_PROXY_HEADERS"
        value = "xforwarded"
      }
      env {
        name  = "KC_DB"
        value = "postgres"
      }
      env {
        name  = "KC_DB_URL_HOST"
        value = local.pgbouncer_host
      }
      env {
        name  = "KC_DB_URL_PORT"
        value = "5432"
      }
      env {
        name  = "KC_DB_URL_DATABASE"
        value = "waooaw_keycloak"
      }
      env {
        name  = "KC_DB_URL_PROPERTIES"
        value = "?prepareThreshold=0"
      }
      env {
        name  = "KC_DB_USERNAME"
        value = "keycloak_runtime"
      }
      # Connection budget on the single provisioned instance (Demo usable slots = 40 - reserved 15).
      env {
        name  = "KC_DB_POOL_INITIAL_SIZE"
        value = "1"
      }
      env {
        name  = "KC_DB_POOL_MIN_SIZE"
        value = "1"
      }
      env {
        name  = "KC_DB_POOL_MAX_SIZE"
        value = var.environment == "demo" ? "2" : "5"
      }
      env {
        name  = "KC_SPI_CONNECTIONS_JPA_QUARKUS_MIGRATION_STRATEGY"
        value = "validate"
      }
      env {
        name  = "KC_SPI_CONNECTIONS_JPA_QUARKUS_INITIALIZE_EMPTY"
        value = "false"
      }
      dynamic "env" {
        for_each = var.persistent_state_enabled ? [1] : []
        content {
          name        = "KC_DB_PASSWORD"
          secret_name = "keycloak-database-credential"
        }
      }

      dynamic "env" {
        for_each = local.google_secret_uris
        content {
          name        = upper(replace(env.key, "-", "_"))
          secret_name = env.key
        }
      }

      dynamic "env" {
        for_each = local.facebook_secret_uris
        content {
          name        = upper(replace(env.key, "-", "_"))
          secret_name = env.key
        }
      }

      dynamic "env" {
        for_each = local.identity_reader_secret_uris
        content {
          name        = "BP_IDENTITY_READER_CLIENT_SECRET"
          secret_name = env.key
        }
      }

      dynamic "env" {
        for_each = local.identity_lifecycle_writer_secret_uris
        content {
          name        = "BP_IDENTITY_LIFECYCLE_WRITER_CLIENT_SECRET"
          secret_name = env.key
        }
      }

    }
  }

  ingress {
    external_enabled = false
    target_port      = 8080

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }

  }

  depends_on = [
    azurerm_role_assignment.member_secret,
    azurerm_role_assignment.google_broker_secret,
    azurerm_role_assignment.facebook_broker_secret,
    azurerm_role_assignment.identity_reader_secret,
    azurerm_role_assignment.keycloak_database_secret,
    azurerm_container_app.pgbouncer,
  ]
}

resource "azurerm_container_app" "identity_edge" {
  count = var.workload_enabled ? 1 : 0

  name                         = "ca-${var.environment}-identity-edge"
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  # Every app runs on the environment's only profile. Azure reports it as "Consumption" even when
  # omitted, so leaving it unset planned a 16-app no-op update (Consumption -> null) on every apply.
  workload_profile_name = "Consumption"

  template {
    min_replicas = local.runtime_dependencies_enabled ? 1 : 0
    max_replicas = 1

    container {
      name    = "identity-edge"
      image   = "nginxinc/nginx-unprivileged@sha256:62a904036bfc0e4a4f2b556e34cbf17bc136b47fde8cdb4628762725f48c5782"
      cpu     = 0.25
      memory  = "0.5Gi"
      command = ["/bin/sh", "-c"]
      args = [<<-EOT
        set -eu
        printf '%s' '${local.identity_edge_config_base64}' | base64 -d > /tmp/nginx.conf
        exec nginx -c /tmp/nginx.conf -g 'daemon off;'
      EOT
      ]
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8080

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [azurerm_container_app.keycloak]
}

resource "azurerm_container_app_custom_domain" "identity_edge" {
  count = var.workload_enabled && var.identity_custom_hostname != null ? 1 : 0

  name             = var.identity_custom_hostname
  container_app_id = azurerm_container_app.identity_edge[0].id

  lifecycle {
    ignore_changes = [certificate_binding_type, container_app_environment_certificate_id]
  }
}

resource "azurerm_user_assigned_identity" "billing_migration" {
  count = var.workload_enabled && var.persistent_state_enabled ? 1 : 0

  name                = "id-${var.environment}-billing-migration"
  location            = var.location
  resource_group_name = var.resource_group_name
}

resource "azurerm_role_assignment" "billing_migration_database_secret" {
  count = var.workload_enabled && var.persistent_state_enabled ? 1 : 0

  scope                = var.database_secret_resource_ids["billing-migration"]
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.billing_migration[0].principal_id
}

resource "azurerm_container_app_job" "billing_migration" {
  count = var.workload_enabled && var.persistent_state_enabled ? 1 : 0

  name                         = "job-${var.environment}-wc124-billing-migration"
  location                     = var.location
  resource_group_name          = var.resource_group_name
  container_app_environment_id = var.container_app_environment_id
  replica_retry_limit          = 1
  replica_timeout_in_seconds   = 1200

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.billing_migration[0].id]
  }

  secret {
    name                = "migration-database"
    identity            = azurerm_user_assigned_identity.billing_migration[0].id
    key_vault_secret_id = var.database_secret_uris["billing-migration"]
  }

  manual_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
  }

  template {
    container {
      name    = "billing-migration"
      image   = var.image_digests["billing-engine"]
      cpu     = 0.5
      memory  = "1Gi"
      command = ["python", "migrate.py"]

      env {
        name        = "DATABASE_URL"
        secret_name = "migration-database"
      }

      env {
        name  = "MIGRATION_PATTERN"
        value = "59-wc124-billing-authority.sql"
      }

      env {
        name  = "MIGRATION_SCHEMA"
        value = "billing"
      }
    }
  }

  depends_on = [
    azurerm_container_app.pgbouncer,
    azurerm_role_assignment.billing_migration_database_secret,
  ]
}

resource "azurerm_container_app_job" "verification" {
  count = var.workload_enabled && var.verification_principal_id != null ? 1 : 0

  name                         = "job-${var.environment}-deployment-verification"
  location                     = var.location
  resource_group_name          = var.resource_group_name
  container_app_environment_id = var.container_app_environment_id
  replica_retry_limit          = 1
  replica_timeout_in_seconds   = 300

  manual_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
  }

  template {
    container {
      name    = "http-probes"
      image   = "mcr.microsoft.com/azure-cli@sha256:4faeb3c955086c3842d4f8cf0ff1d900ce3a1c68c6e6c6430c5e8a3cb882c5aa"
      cpu     = 0.25
      memory  = "0.5Gi"
      command = ["/bin/sh", "-c"]
      args = [<<-EOT
        set -eu
        probe() {
          name="$1"
          url="$2"
          for attempt in 1 2 3 4 5 6 7 8 9 10; do
            http_code=$(curl --silent --show-error --max-time 15 --output /dev/null --write-out '%%{http_code}' "$url") && curl_exit=0 || curl_exit=$?
            if [ "$curl_exit" -eq 0 ] && [ "$http_code" -ge 200 ] && [ "$http_code" -lt 400 ]; then
              echo "probe_result name=$name status=succeeded http_code=$http_code attempt=$attempt url=$url"
              return 0
            fi
            echo "probe_attempt name=$name status=failed curl_exit=$curl_exit http_code=$http_code attempt=$attempt url=$url" >&2
            sleep 6
          done
          echo "probe_result name=$name status=failed url=$url" >&2
          return 1
        }
        probe_identity_provider() {
          provider="$1"
          url="${local.verification_urls.business_platform}/api/v1/identity/providers"
          response=$(mktemp)
          for attempt in 1 2 3 4 5 6 7 8 9 10; do
            http_code=$(curl --silent --show-error --max-time 15 --output "$response" --write-out '%%{http_code}' "$url") && curl_exit=0 || curl_exit=$?
            if [ "$curl_exit" -eq 0 ] && [ "$http_code" -eq 200 ] \
              && jq -e --arg provider "$provider" '.providers[] | select(.id == $provider and .availability == "AVAILABLE")' "$response" >/dev/null; then
              echo "provider_probe_result provider=$provider status=succeeded http_code=$http_code attempt=$attempt url=$url"
              rm -f "$response"
              return 0
            fi
            echo "provider_probe_attempt provider=$provider status=failed curl_exit=$curl_exit http_code=$http_code attempt=$attempt url=$url" >&2
            sleep 6
          done
          rm -f "$response"
          echo "provider_probe_result provider=$provider status=failed url=$url" >&2
          return 1
        }
        probe web "${local.verification_urls.web}/" & web_pid=$!
        probe business-platform "${local.verification_urls.business_platform}/health/ready" & business_platform_pid=$!
        probe professional-runtime "${local.verification_urls.professional_runtime}/health" & professional_runtime_pid=$!
        probe ai-runtime "${local.verification_urls.ai_runtime}/health" & ai_runtime_pid=$!
        probe billing-engine "${local.verification_urls.billing_engine}/health" & billing_engine_pid=$!
        probe dma-adapter "${local.verification_urls.dma_adapter}/health/live" & dma_adapter_pid=$!
        probe identity-edge "${local.verification_urls.identity_edge}/realms/waooaw/.well-known/openid-configuration" & identity_edge_pid=$!
        probe_status=0
        for probe_pid in "$web_pid" "$business_platform_pid" "$professional_runtime_pid" "$ai_runtime_pid" "$billing_engine_pid" "$dma_adapter_pid" "$identity_edge_pid"; do
          wait "$probe_pid" || probe_status=1
        done
        if [ "${var.environment}" = "demo" ]; then
          probe_identity_provider "GOOGLE" || probe_status=1
          probe_identity_provider "FACEBOOK" || probe_status=1
        fi
        exit "$probe_status"
      EOT
      ]
    }

    container {
      name    = "constitutional-health"
      image   = var.image_digests["constitutional-engine"]
      cpu     = 0.25
      memory  = "0.5Gi"
      command = ["/bin/sh", "-c"]
      args    = ["for attempt in 1 2 3 4 5 6 7 8 9 10; do grpc_health_probe -addr=ca-${var.environment}-constitutional-engine:80 -connect-timeout=10s -rpc-timeout=10s && exit 0; sleep 6; done; exit 1"]
    }
  }

  depends_on = [azurerm_container_app.member, azurerm_container_app.temporal, azurerm_container_app.keycloak, azurerm_container_app.identity_edge]
}

resource "azurerm_role_assignment" "verification_job_operator" {
  count = length(azurerm_container_app_job.verification)

  scope                = azurerm_container_app_job.verification[0].id
  role_definition_name = "Container Apps Jobs Operator"
  principal_id         = var.verification_principal_id
}

output "web_url" {
  value = var.workload_enabled ? "https://${coalesce(var.web_custom_hostname, "ca-${var.environment}-web.${var.container_app_environment_default_domain}")}" : null
}