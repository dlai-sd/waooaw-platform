output "web_url"                { value = "https://${azurerm_container_app.web.ingress[0].fqdn}" }
output "api_url"                { value = "https://${azurerm_container_app.business_platform.ingress[0].fqdn}" }
output "keycloak_url"           { value = "https://${azurerm_container_app.keycloak.ingress[0].fqdn}" }
output "pr_url"                 { value = "https://${azurerm_container_app.professional_runtime.ingress[0].fqdn}" }
output "postgres_fqdn"          { value = azurerm_postgresql_flexible_server.main.fqdn }
output "container_env_id"       { value = azurerm_container_app_environment.main.id }
output "key_vault_uri"          { value = azurerm_key_vault.main.vault_uri }
output "app_insights_key"       { value = azurerm_application_insights.main.instrumentation_key; sensitive = true }
output "app_insights_conn_str"  { value = azurerm_application_insights.main.connection_string; sensitive = true }
output "resource_group_name"    { value = azurerm_resource_group.main.name }
