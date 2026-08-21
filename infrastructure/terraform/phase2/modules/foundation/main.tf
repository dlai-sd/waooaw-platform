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

resource "azurerm_container_app_environment" "environment" {
  name                           = "cae-${local.name}"
  location                       = azurerm_resource_group.environment.location
  resource_group_name            = azurerm_resource_group.environment.name
  infrastructure_subnet_id       = azurerm_subnet.container_apps.id
  internal_load_balancer_enabled = !var.external_environment
  tags                           = local.tags
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

output "container_app_environment_name" {
  value = azurerm_container_app_environment.environment.name
}

output "container_app_environment_default_domain" {
  value = azurerm_container_app_environment.environment.default_domain
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