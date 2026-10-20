terraform {
  required_version = "= 1.9.8"

  required_providers {
    azurerm = {
      source                = "hashicorp/azurerm"
      version               = "= 4.14.0"
      configuration_aliases = [azurerm.deployment]
    }
    random = {
      source  = "hashicorp/random"
      version = "= 3.6.3"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "= 2.2.0"
    }
  }
}

locals {
  name = "waooaw-${var.environment}"
  address_spaces = {
    demo = "10.60.0.0/16"
    uat  = "10.61.0.0/16"
    prod = "10.62.0.0/16"
  }
  tags = {
    environment    = var.environment
    managed_by     = "terraform"
    release_system = "goal-006"
  }
}

resource "azurerm_resource_group" "environment" {
  name     = "${local.name}-rg"
  location = var.location
  tags     = local.tags
}

resource "azurerm_user_assigned_identity" "deployment" {
  name                = "id-${local.name}-deployment"
  location            = azurerm_resource_group.environment.location
  resource_group_name = azurerm_resource_group.environment.name
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "verification" {
  name                = "id-${local.name}-verification"
  location            = azurerm_resource_group.environment.location
  resource_group_name = azurerm_resource_group.environment.name
  tags                = local.tags
}

resource "azurerm_role_assignment" "deployment_contributor" {
  scope                = azurerm_resource_group.environment.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.deployment.principal_id
}

resource "azurerm_role_assignment" "deployment_rbac" {
  scope                = azurerm_resource_group.environment.id
  role_definition_name = "Role Based Access Control Administrator"
  principal_id         = azurerm_user_assigned_identity.deployment.principal_id
}

resource "azurerm_role_assignment" "deployment_state" {
  scope                = var.tfstate_storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.deployment.principal_id
}

resource "azurerm_role_assignment" "verification_reader" {
  scope                = azurerm_resource_group.environment.id
  role_definition_name = "Reader"
  principal_id         = azurerm_user_assigned_identity.verification.principal_id
}

resource "azurerm_virtual_network" "environment" {
  name                = "vnet-${local.name}"
  location            = azurerm_resource_group.environment.location
  resource_group_name = azurerm_resource_group.environment.name
  address_space       = [local.address_spaces[var.environment]]
  tags                = local.tags
}

resource "azurerm_subnet" "container_apps" {
  name                 = "snet-container-apps"
  resource_group_name  = azurerm_resource_group.environment.name
  virtual_network_name = azurerm_virtual_network.environment.name
  address_prefixes     = [cidrsubnet(local.address_spaces[var.environment], 7, 0)]

  delegation {
    name = "container-apps"
    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_subnet" "private_endpoints" {
  name                 = "snet-private-endpoints"
  resource_group_name  = azurerm_resource_group.environment.name
  virtual_network_name = azurerm_virtual_network.environment.name
  address_prefixes     = [cidrsubnet(local.address_spaces[var.environment], 8, 2)]
}

resource "azurerm_subnet" "postgresql" {
  count = var.persistent_state_enabled ? 1 : 0

  name                 = "snet-postgresql"
  resource_group_name  = azurerm_resource_group.environment.name
  virtual_network_name = azurerm_virtual_network.environment.name
  address_prefixes     = [cidrsubnet(local.address_spaces[var.environment], 8, 3)]

  delegation {
    name = "postgresql-flexible-server"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_network_security_group" "container_apps" {
  name                = "nsg-${local.name}-container-apps"
  location            = azurerm_resource_group.environment.location
  resource_group_name = azurerm_resource_group.environment.name
  tags                = local.tags

  security_rule {
    name                       = "allow-private-egress"
    priority                   = 100
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "VirtualNetwork"
  }

  security_rule {
    name                       = "allow-platform-dns"
    priority                   = 110
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Udp"
    source_port_range          = "*"
    destination_port_range     = "53"
    source_address_prefix      = "*"
    destination_address_prefix = "168.63.129.16/32"
  }

  security_rule {
    name                       = "allow-https-egress"
    priority                   = 120
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "Internet"
  }

  security_rule {
    name                       = "deny-unapproved-egress"
    priority                   = 4096
    direction                  = "Outbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_network_security_group" "private_endpoints" {
  name                = "nsg-${local.name}-private-endpoints"
  location            = azurerm_resource_group.environment.location
  resource_group_name = azurerm_resource_group.environment.name
  tags                = local.tags

  security_rule {
    name                       = "deny-unapproved-egress"
    priority                   = 4096
    direction                  = "Outbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "container_apps" {
  subnet_id                 = azurerm_subnet.container_apps.id
  network_security_group_id = azurerm_network_security_group.container_apps.id
}

resource "azurerm_subnet_network_security_group_association" "private_endpoints" {
  subnet_id                 = azurerm_subnet.private_endpoints.id
  network_security_group_id = azurerm_network_security_group.private_endpoints.id
}

resource "azurerm_federated_identity_credential" "deployment" {
  name                = "github-${var.repository_environment}-deployment"
  resource_group_name = azurerm_resource_group.environment.name
  parent_id           = azurerm_user_assigned_identity.deployment.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:${var.repository_id}:environment:${var.repository_environment}"
}

resource "azurerm_federated_identity_credential" "verification" {
  name                = "github-${var.repository_environment}-verification"
  resource_group_name = azurerm_resource_group.environment.name
  parent_id           = azurerm_user_assigned_identity.verification.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:${var.repository_id}:environment:${var.repository_environment}-verification"
}

resource "azurerm_key_vault" "environment" {
  name                          = "kv-${local.name}"
  location                      = azurerm_resource_group.environment.location
  resource_group_name           = azurerm_resource_group.environment.name
  tenant_id                     = azurerm_user_assigned_identity.deployment.tenant_id
  sku_name                      = "standard"
  enable_rbac_authorization     = true
  purge_protection_enabled      = true
  soft_delete_retention_days    = 90
  public_network_access_enabled = false
  tags                          = local.tags

  network_acls {
    bypass         = "AzureServices"
    default_action = "Deny"
  }
}

resource "azurerm_role_assignment" "deployment_secret_officer" {
  scope                = azurerm_key_vault.environment.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = azurerm_user_assigned_identity.deployment.principal_id
}

resource "azurerm_private_endpoint" "key_vault" {
  name                = "pe-${local.name}-vault"
  location            = azurerm_resource_group.environment.location
  resource_group_name = azurerm_resource_group.environment.name
  subnet_id           = azurerm_subnet.private_endpoints.id
  tags                = local.tags

  private_service_connection {
    name                           = "psc-${local.name}-vault"
    private_connection_resource_id = azurerm_key_vault.environment.id
    subresource_names              = ["vault"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "zone-${local.name}-vault"
    private_dns_zone_ids = [azurerm_private_dns_zone.key_vault.id]
  }
}

resource "azurerm_private_dns_zone" "key_vault" {
  name                = "privatelink.vaultcore.azure.net"
  resource_group_name = azurerm_resource_group.environment.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "key_vault" {
  name                  = "link-${local.name}-vault"
  resource_group_name   = azurerm_resource_group.environment.name
  private_dns_zone_name = azurerm_private_dns_zone.key_vault.name
  virtual_network_id    = azurerm_virtual_network.environment.id
  tags                  = local.tags
}

resource "azurerm_user_assigned_identity" "database_bootstrap" {
  count = var.persistent_state_enabled ? 1 : 0

  name                = "id-${local.name}-db-bootstrap"
  location            = azurerm_resource_group.environment.location
  resource_group_name = azurerm_resource_group.environment.name
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "database_provisioner" {
  count = var.persistent_state_enabled ? 1 : 0

  name                = "id-${local.name}-db-provisioner"
  location            = azurerm_resource_group.environment.location
  resource_group_name = azurerm_resource_group.environment.name
  tags                = local.tags
}

resource "azurerm_role_assignment" "database_provisioner_vault" {
  count = var.persistent_state_enabled && var.database_provisioner_vault_access_enabled ? 1 : 0

  scope                = azurerm_key_vault.environment.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = azurerm_user_assigned_identity.database_provisioner[0].principal_id
}

resource "azurerm_private_dns_zone" "postgresql" {
  count = var.persistent_state_enabled ? 1 : 0

  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.environment.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgresql" {
  count = var.persistent_state_enabled ? 1 : 0

  name                  = "link-${local.name}-postgresql"
  resource_group_name   = azurerm_resource_group.environment.name
  private_dns_zone_name = azurerm_private_dns_zone.postgresql[0].name
  virtual_network_id    = azurerm_virtual_network.environment.id
  tags                  = local.tags
}

resource "random_password" "postgresql_breakglass_administrator" {
  count = var.persistent_state_enabled && var.postgresql_password_auth_enabled ? 1 : 0

  length           = 40
  special          = true
  override_special = "_%@-"
}

resource "azurerm_key_vault_secret" "postgresql_breakglass_administrator" {
  count = var.persistent_state_enabled && var.postgresql_password_auth_enabled ? 1 : 0

  provider     = azurerm.deployment
  name         = "db-server-breakglass-admin"
  value        = random_password.postgresql_breakglass_administrator[0].result
  key_vault_id = azurerm_key_vault.environment.id
  content_type = "PostgreSQL sealed break-glass administrator credential"
  tags         = merge(local.tags, { authority = "break-glass-only" })

  depends_on = [azurerm_role_assignment.deployment_secret_officer]
}

resource "azurerm_postgresql_flexible_server" "persistent_state" {
  count = var.persistent_state_enabled ? 1 : 0

  name                          = "psql-${local.name}-state"
  resource_group_name           = azurerm_resource_group.environment.name
  location                      = azurerm_resource_group.environment.location
  version                       = "16"
  delegated_subnet_id           = azurerm_subnet.postgresql[0].id
  private_dns_zone_id           = azurerm_private_dns_zone.postgresql[0].id
  public_network_access_enabled = false
  sku_name                      = "B_Standard_B1ms"
  storage_mb                    = 32768
  auto_grow_enabled             = false
  backup_retention_days         = 35
  geo_redundant_backup_enabled  = false
  zone                          = "1"
  tags                          = merge(local.tags, { authority = "persistent-state", cost_center = "demo-uat-retained-data" })

  authentication {
    active_directory_auth_enabled = true
    password_auth_enabled         = var.postgresql_password_auth_enabled
    tenant_id                     = azurerm_user_assigned_identity.deployment.tenant_id
  }

  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      administrator_login,
      administrator_password,
      authentication[0].password_auth_enabled,
    ]
  }

  depends_on = [azurerm_private_dns_zone_virtual_network_link.postgresql]
}

resource "azapi_update_resource" "postgresql_plan_b_authentication" {
  count = var.persistent_state_enabled && var.postgresql_password_auth_enabled ? 1 : 0

  type        = "Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01"
  resource_id = azurerm_postgresql_flexible_server.persistent_state[0].id
  body = {
    properties = {
      administratorLogin         = "wc124_breakglass_admin"
      administratorLoginPassword = random_password.postgresql_breakglass_administrator[0].result
      authConfig = {
        activeDirectoryAuth = "Enabled"
        passwordAuth        = "Enabled"
        tenantId            = azurerm_user_assigned_identity.deployment.tenant_id
      }
    }
  }

  depends_on = [azurerm_key_vault_secret.postgresql_breakglass_administrator]
}

resource "azurerm_postgresql_flexible_server_active_directory_administrator" "bootstrap" {
  count = var.persistent_state_enabled && var.database_bootstrap_admin_enabled ? 1 : 0

  server_name         = azurerm_postgresql_flexible_server.persistent_state[0].name
  resource_group_name = azurerm_resource_group.environment.name
  tenant_id           = azurerm_user_assigned_identity.database_bootstrap[0].tenant_id
  object_id           = azurerm_user_assigned_identity.database_bootstrap[0].principal_id
  principal_name      = azurerm_user_assigned_identity.database_bootstrap[0].name
  principal_type      = "ServicePrincipal"
}

resource "azurerm_postgresql_flexible_server_database" "persistent_state" {
  for_each = var.persistent_state_enabled ? toset(
    var.environment == "demo"
    ? ["waooaw_application", "waooaw_keycloak", "waooaw_temporal", "waooaw_temporal_visibility"]
    : ["waooaw_application", "waooaw_keycloak"]
  ) : toset([])

  name      = each.value
  server_id = azurerm_postgresql_flexible_server.persistent_state[0].id
  charset   = "UTF8"
  collation = "en_US.utf8"

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_postgresql_flexible_server_configuration" "extensions" {
  count = var.persistent_state_enabled ? 1 : 0

  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.persistent_state[0].id
  value     = "BTREE_GIN,VECTOR"
}

resource "azurerm_postgresql_flexible_server_configuration" "max_connections" {
  count = var.persistent_state_enabled ? 1 : 0

  name      = "max_connections"
  server_id = azurerm_postgresql_flexible_server.persistent_state[0].id
  value     = var.environment == "demo" ? "40" : "100"
}

resource "azurerm_redis_cache" "auth_abuse" {
  count = var.auth_redis_ha_enabled ? 1 : 0

  name                          = "redis-${local.name}-auth"
  location                      = azurerm_resource_group.environment.location
  resource_group_name           = azurerm_resource_group.environment.name
  capacity                      = 1
  family                        = "P"
  sku_name                      = "Premium"
  non_ssl_port_enabled          = false
  minimum_tls_version           = "1.2"
  public_network_access_enabled = false
  redis_version                 = "6"
  replicas_per_master           = 1
  zones                         = ["1", "2"]
  tags                          = local.tags

  redis_configuration {}

  lifecycle {
    precondition {
      condition     = var.environment == "prod"
      error_message = "Managed HA authentication Redis is a Production foundation dependency."
    }
  }
}

resource "azurerm_private_dns_zone" "redis" {
  count = var.auth_redis_ha_enabled ? 1 : 0

  name                = "privatelink.redis.cache.windows.net"
  resource_group_name = azurerm_resource_group.environment.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "redis" {
  count = var.auth_redis_ha_enabled ? 1 : 0

  name                  = "link-${local.name}-redis"
  resource_group_name   = azurerm_resource_group.environment.name
  private_dns_zone_name = azurerm_private_dns_zone.redis[0].name
  virtual_network_id    = azurerm_virtual_network.environment.id
  tags                  = local.tags
}

resource "azurerm_private_endpoint" "auth_redis" {
  count = var.auth_redis_ha_enabled ? 1 : 0

  name                = "pe-${local.name}-auth-redis"
  location            = azurerm_resource_group.environment.location
  resource_group_name = azurerm_resource_group.environment.name
  subnet_id           = azurerm_subnet.private_endpoints.id
  tags                = local.tags

  private_service_connection {
    name                           = "psc-${local.name}-auth-redis"
    private_connection_resource_id = azurerm_redis_cache.auth_abuse[0].id
    subresource_names              = ["redisCache"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "zone-${local.name}-auth-redis"
    private_dns_zone_ids = [azurerm_private_dns_zone.redis[0].id]
  }
}

resource "azurerm_private_endpoint" "key_vault_runner" {
  name                = "pe-${local.name}-vault-runner"
  location            = azurerm_resource_group.environment.location
  resource_group_name = var.runner_resource_group_name
  subnet_id           = var.runner_private_endpoints_subnet_id
  tags                = local.tags

  private_service_connection {
    name                           = "psc-${local.name}-vault-runner"
    private_connection_resource_id = azurerm_key_vault.environment.id
    subresource_names              = ["vault"]
    is_manual_connection           = false
  }
}

resource "azurerm_private_dns_a_record" "key_vault_runner" {
  name                = azurerm_key_vault.environment.name
  zone_name           = azurerm_private_dns_zone.key_vault.name
  resource_group_name = var.runner_resource_group_name
  ttl                 = 10
  records             = [azurerm_private_endpoint.key_vault_runner.private_service_connection[0].private_ip_address]
}

resource "azurerm_log_analytics_workspace" "environment" {
  name                = coalesce(var.log_analytics_workspace_name, "law-${local.name}")
  location            = azurerm_resource_group.environment.location
  resource_group_name = azurerm_resource_group.environment.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

resource "azurerm_container_app_environment" "environment" {
  name                           = "cae-${local.name}"
  location                       = azurerm_resource_group.environment.location
  resource_group_name            = azurerm_resource_group.environment.name
  infrastructure_subnet_id       = azurerm_subnet.container_apps.id
  internal_load_balancer_enabled = !var.external_environment
  log_analytics_workspace_id     = azurerm_log_analytics_workspace.environment.id
  tags                           = local.tags

  lifecycle {
    ignore_changes = [infrastructure_resource_group_name]
  }
}

output "resource_group_name" {
  value = azurerm_resource_group.environment.name
}

output "container_app_environment_id" {
  value = azurerm_container_app_environment.environment.id
}

output "key_vault_id" {
  value = azurerm_key_vault.environment.id
}

output "key_vault_name" {
  value = azurerm_key_vault.environment.name
}

output "key_vault_uri" {
  value = azurerm_key_vault.environment.vault_uri
}

output "runner_key_vault_dns_record_id" {
  value = azurerm_private_dns_a_record.key_vault_runner.id
}

output "runner_key_vault_private_endpoint_id" {
  value = azurerm_private_endpoint.key_vault_runner.id
}

output "container_app_environment_name" {
  value = azurerm_container_app_environment.environment.name
}

output "container_app_environment_default_domain" {
  value = azurerm_container_app_environment.environment.default_domain
}

output "log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.environment.id
}

output "location" {
  value = azurerm_resource_group.environment.location
}

output "deployment_client_id" {
  value = azurerm_user_assigned_identity.deployment.client_id
}

output "deployment_identity_id" {
  value = azurerm_user_assigned_identity.deployment.id
}

output "verification_client_id" {
  value = azurerm_user_assigned_identity.verification.client_id
}

output "verification_principal_id" {
  value = azurerm_user_assigned_identity.verification.principal_id
}

output "auth_abuse_redis_url" {
  value     = var.auth_redis_ha_enabled ? "rediss://${azurerm_redis_cache.auth_abuse[0].hostname}:${azurerm_redis_cache.auth_abuse[0].ssl_port}/0" : null
  sensitive = true
}

output "postgresql_server_id" {
  value = var.persistent_state_enabled ? azurerm_postgresql_flexible_server.persistent_state[0].id : null
}

output "postgresql_server_fqdn" {
  value = var.persistent_state_enabled ? azurerm_postgresql_flexible_server.persistent_state[0].fqdn : null
}

output "database_bootstrap_client_id" {
  value = var.persistent_state_enabled ? azurerm_user_assigned_identity.database_bootstrap[0].client_id : null
}

output "database_bootstrap_identity_id" {
  value = var.persistent_state_enabled ? azurerm_user_assigned_identity.database_bootstrap[0].id : null
}

output "database_provisioner_client_id" {
  value = var.persistent_state_enabled ? azurerm_user_assigned_identity.database_provisioner[0].client_id : null
}

output "database_provisioner_identity_id" {
  value = var.persistent_state_enabled ? azurerm_user_assigned_identity.database_provisioner[0].id : null
}