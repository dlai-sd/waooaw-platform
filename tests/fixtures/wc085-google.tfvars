environment                              = "demo"
google_login_enabled                     = true
resource_group_name                      = "waooaw-demo-rg"
location                                 = "centralindia"
container_app_environment_id              = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/waooaw-demo-rg/providers/Microsoft.App/managedEnvironments/fixture"
container_app_environment_default_domain  = "local.waooaw.test"
founder_ipv4_cidr                         = "203.0.113.10/32"
workload_enabled                         = false
image_digests = {
  constitutional-engine = "fixture/ce@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  business-platform     = "fixture/bp@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  professional-runtime  = "fixture/pr@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  ai-runtime            = "fixture/ai@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  web                   = "fixture/web@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  billing-engine        = "fixture/billing@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}
key_vault_secret_uris = {
  constitutional-engine = "https://kv-waooaw-demo.vault.azure.net/secrets/constitutional-engine"
  business-platform     = "https://kv-waooaw-demo.vault.azure.net/secrets/business-platform"
  professional-runtime  = "https://kv-waooaw-demo.vault.azure.net/secrets/professional-runtime"
  ai-runtime            = "https://kv-waooaw-demo.vault.azure.net/secrets/ai-runtime"
  web                   = "https://kv-waooaw-demo.vault.azure.net/secrets/web"
  billing-engine        = "https://kv-waooaw-demo.vault.azure.net/secrets/billing-engine"
}
key_vault_secret_resource_ids = {
  constitutional-engine = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/waooaw-demo-rg/providers/Microsoft.KeyVault/vaults/kv-waooaw-demo/secrets/constitutional-engine"
  business-platform     = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/waooaw-demo-rg/providers/Microsoft.KeyVault/vaults/kv-waooaw-demo/secrets/business-platform"
  professional-runtime  = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/waooaw-demo-rg/providers/Microsoft.KeyVault/vaults/kv-waooaw-demo/secrets/professional-runtime"
  ai-runtime            = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/waooaw-demo-rg/providers/Microsoft.KeyVault/vaults/kv-waooaw-demo/secrets/ai-runtime"
  web                   = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/waooaw-demo-rg/providers/Microsoft.KeyVault/vaults/kv-waooaw-demo/secrets/web"
  billing-engine        = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/waooaw-demo-rg/providers/Microsoft.KeyVault/vaults/kv-waooaw-demo/secrets/billing-engine"
}