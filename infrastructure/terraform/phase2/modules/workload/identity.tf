locals {
  demo_identity_manifest = jsondecode(file("${path.module}/../../../../identity-config/environments/demo.json"))
  demo_identity_runtime = merge(
    {
      IdentityEnvironment__SchemaVersion = local.demo_identity_manifest.schemaVersion
      IdentityEnvironment__Environment   = local.demo_identity_manifest.environment
    },
    merge([for group in ["origins", "keycloak", "channels", "cookie", "identityEdge", "phoneIdentity"] : {
      for name, value in local.demo_identity_manifest[group] : "IdentityEnvironment__${group}__${name}" => tostring(value)
    }]...),
    merge([for index, client in local.demo_identity_manifest.clients : merge(
      { for name in ["id", "channel", "pkceRequired"] : "IdentityEnvironment__clients__${index}__${name}" => tostring(client[name]) },
      merge([for name in ["redirectUris", "postLogoutRedirectUris", "allowedOrigins", "scopes"] : {
        for position, value in client[name] : "IdentityEnvironment__clients__${index}__${name}__${position}" => value
      }]...)
    )]...),
    merge([for index, provider in local.demo_identity_manifest.providers : merge(
      {
        "IdentityEnvironment__providers__${index}__readinessEvidenceReference" = ""
        "IdentityEnvironment__providers__${index}__unavailableReason"          = ""
      },
      { for name, value in provider : "IdentityEnvironment__providers__${index}__${name}" => tostring(value) if name != "scopes" },
      { for position, value in provider.scopes : "IdentityEnvironment__providers__${index}__scopes__${position}" => value }
    )]...)
  )
}