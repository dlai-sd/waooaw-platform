# ADR-046 Amendment 1: cloud issuance of workload credentials for every environment.
# Key Vault holds the CA keys and the published credential bundles; two scheduled jobs issue them; workloads reload
# them in process. Foundation creates the keys and the empty "UNISSUED" slots (modules/foundation/main.tf).

variable "workload_identity_alert_action_group_id" {
  description = "Optional Azure Monitor action group notified by the credential alerts; null keeps the alerts visible in Azure Monitor only."
  type        = string
  default     = null
  nullable    = true
}

variable "log_analytics_workspace_id" {
  description = "Environment Log Analytics workspace that receives issuer job output; empty skips the credential alert rules."
  type        = string
  default     = ""
}

locals {
  wid_workloads    = ["business-platform", "billing-engine", "professional-runtime", "ai-runtime"]
  wid_vault_url    = trimsuffix(var.key_vault_secret_uris["web"], "/secrets/web")
  wid_vault_id     = trimsuffix(var.key_vault_secret_resource_ids["web"], "/secrets/web")
  wid_trust_domain = "${var.environment}.waooaw.internal"
  wid_job_prefix   = "job-${var.environment}-wid-"
  wid_key_scopes = {
    for name in ["wid-root", "wid-intermediate"] : name => "${local.wid_vault_id}/keys/${name}"
  }
  wid_secret_scopes = {
    for name in concat(["wid-ca-state", "wid-trust-bundle"], [for workload in local.wid_workloads : "wid-bundle-${workload}"]) :
    name => "${local.wid_vault_id}/secrets/${name}"
  }
  # The pinned azure-cli image already carries python3.12 and cryptography; the issuer sources ship as chunked job secrets.
  wid_issuer_image = "mcr.microsoft.com/azure-cli@sha256:4faeb3c955086c3842d4f8cf0ff1d900ce3a1c68c6e6c6430c5e8a3cb882c5aa"
  wid_issuer_sources = {
    cli = base64gzip(file("${path.module}/../../../../../scripts/wid_issuer.py"))
    lib = base64gzip(file("${path.module}/../../../../../scripts/workload_identity_issuance.py"))
    reg = base64gzip(file("${path.module}/../../../../../infrastructure/workload-identity/registry.yaml"))
  }
  wid_issuer_secrets = merge([
    for key, payload in local.wid_issuer_sources : {
      for index in range(0, ceil(length(payload) / 12000)) :
      "wid-${key}-${format("%02d", index)}" => substr(payload, index * 12000, 12000)
    }
  ]...)
  wid_issuer_script = <<-EOT
    set -eu
    mkdir -p /tmp/wid
    cat /mnt/wid/wid-cli-* | base64 -d | gunzip > /tmp/wid/wid_issuer.py
    cat /mnt/wid/wid-lib-* | base64 -d | gunzip > /tmp/wid/workload_identity_issuance.py
    cat /mnt/wid/wid-reg-* | base64 -d | gunzip > /tmp/wid/registry.yaml
    export PYTHONPATH=/usr/lib64/az/lib/python3.12/site-packages
    exec python3.12 /tmp/wid/wid_issuer.py "$WID_MODE"
  EOT
  wid_jobs = {
    "ca-rotator"  = { mode = "ca", cron = "23 2 * * *" }
    "leaf-issuer" = { mode = "leaf", cron = "*/30 * * * *" }
  }
  # job -> [scope, role] pairs, least privilege. Crypto Officer manages key versions but cannot sign, so signers also hold Crypto User.
  wid_job_grants = {
    "ca-rotator" = concat(
      [
        for role in ["Key Vault Crypto User", "Key Vault Crypto Officer"] : { scope = local.wid_key_scopes["wid-root"], role = role }
      ],
      [
        for role in ["Key Vault Crypto User", "Key Vault Crypto Officer"] : { scope = local.wid_key_scopes["wid-intermediate"], role = role }
      ],
      [
        { scope = local.wid_secret_scopes["wid-ca-state"], role = "Key Vault Secrets Officer" },
        { scope = local.wid_secret_scopes["wid-trust-bundle"], role = "Key Vault Secrets Officer" },
      ],
    )
    "leaf-issuer" = concat(
      [
        { scope = local.wid_key_scopes["wid-intermediate"], role = "Key Vault Crypto User" },
        { scope = local.wid_secret_scopes["wid-ca-state"], role = "Key Vault Secrets User" },
        { scope = local.wid_secret_scopes["wid-trust-bundle"], role = "Key Vault Secrets Officer" },
      ],
      [for workload in local.wid_workloads : { scope = local.wid_secret_scopes["wid-bundle-${workload}"], role = "Key Vault Secrets Officer" }],
    )
  }
  wid_job_grant_list = flatten([
    for job, grants in local.wid_job_grants : [
      for grant in grants : { key = "${job}|${grant.scope}|${grant.role}", job = job, scope = grant.scope, role = grant.role }
    ]
  ])
  # Each workload reads only its own bundle plus the signed trust bundle.
  wid_reader_grants = var.workload_enabled ? merge([
    for workload in local.wid_workloads : {
      "${workload}|bundle" = { member = workload, scope = local.wid_secret_scopes["wid-bundle-${workload}"] }
      "${workload}|trust"  = { member = workload, scope = local.wid_secret_scopes["wid-trust-bundle"] }
    }
  ]...) : {}
  wid_service_environment = {
    for workload in local.wid_workloads : workload => merge({
      WAOOAW_WID_SOURCE          = "keyvault"
      WAOOAW_WID_VAULT_URL       = local.wid_vault_url
      WAOOAW_WID_WORKLOAD        = workload
      WAOOAW_WID_ENVIRONMENT     = var.environment
      WAOOAW_WID_TRUST_DOMAIN    = local.wid_trust_domain
      WAOOAW_WID_REFRESH_SECONDS = "300"
      }, workload == "business-platform" ? {
      # Container Apps service names; the TLS identity is checked by workload identity URI, never by host name.
      BillingEngine__RelationshipWorkspaceBaseUrl       = "https://ca-${var.environment}-billing-engine:${local.wid_private_listeners["billing-engine"]}"
      ProfessionalRuntime__RelationshipWorkspaceBaseUrl = "https://ca-${var.environment}-professional-runtime:${local.wid_private_listeners["professional-runtime"]}"
      # WC-149: the provider probe needs the AI runtime peer certificate, so it uses the private mutual-TLS listener.
      ProviderProbe__BaseUrl = "https://ca-${var.environment}-ai-runtime:${local.wid_private_listeners["ai-runtime"]}"
      # Business Platform serves /internal/v1/* to the AI runtime on its own private mutual-TLS port.
      WorkloadInbound__Port = tostring(local.wid_private_listeners["business-platform"])
      } : {}, workload == "ai-runtime" ? {
      AIR_CONVERSATION_GENERATION_OWNER_URL = "https://ca-${var.environment}-business-platform:${local.wid_private_listeners["business-platform"]}"
    } : {})
  }
  # Private mutual-TLS listeners; callers reach them by Container Apps service name, never through public ingress.
  wid_private_listeners = {
    "business-platform"    = 5445
    "billing-engine"       = 5444
    "professional-runtime" = 5443
    "ai-runtime"           = 5444
  }
}

resource "azurerm_user_assigned_identity" "wid_job" {
  for_each = var.workload_enabled ? local.wid_jobs : {}

  name                = "id-${var.environment}-wid-${each.key}"
  location            = var.location
  resource_group_name = var.resource_group_name
}

resource "azurerm_role_assignment" "wid_job" {
  for_each = var.workload_enabled ? { for grant in local.wid_job_grant_list : grant.key => grant } : {}

  scope                = each.value.scope
  role_definition_name = each.value.role
  principal_id         = azurerm_user_assigned_identity.wid_job[each.value.job].principal_id
}

resource "azurerm_role_assignment" "wid_reader" {
  for_each = local.wid_reader_grants

  scope                = each.value.scope
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.member[each.value.member].principal_id
}

resource "azurerm_container_app_job" "wid" {
  for_each = var.workload_enabled ? local.wid_jobs : {}

  name                         = "${local.wid_job_prefix}${each.key}"
  location                     = var.location
  resource_group_name          = var.resource_group_name
  container_app_environment_id = var.container_app_environment_id
  replica_retry_limit          = 1
  replica_timeout_in_seconds   = 300

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.wid_job[each.key].id]
  }

  schedule_trigger_config {
    cron_expression          = each.value.cron
    parallelism              = 1
    replica_completion_count = 1
  }

  dynamic "secret" {
    for_each = local.wid_issuer_secrets
    content {
      name  = secret.key
      value = secret.value
    }
  }

  template {
    volume {
      name         = "wid-source"
      storage_type = "Secret"
    }

    container {
      name    = "issuer"
      image   = local.wid_issuer_image
      cpu     = 0.25
      memory  = "0.5Gi"
      command = ["/bin/sh", "-c"]
      args    = [local.wid_issuer_script]

      volume_mounts {
        name = "wid-source"
        path = "/mnt/wid"
      }

      env {
        name  = "WID_MODE"
        value = each.value.mode
      }
      env {
        name  = "WID_ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "WID_VAULT_URL"
        value = local.wid_vault_url
      }
      env {
        name  = "WID_MANAGED_IDENTITY_CLIENT_ID"
        value = azurerm_user_assigned_identity.wid_job[each.key].client_id
      }
      env {
        name  = "WID_WORKLOADS"
        value = join(",", local.wid_workloads)
      }
      env {
        name  = "WID_REGISTRY_PATH"
        value = "/tmp/wid/registry.yaml"
      }
    }
  }

  lifecycle {
    precondition {
      condition     = length(local.wid_issuer_secrets) <= 18
      error_message = "Issuer sources exceed the Container Apps secret budget; raise the chunk size or move the sources into an image."
    }
  }

  depends_on = [azurerm_role_assignment.wid_job]
}

resource "azurerm_role_assignment" "wid_job_operator" {
  for_each = var.workload_enabled && var.verification_principal_id != null ? local.wid_jobs : {}

  scope                = azurerm_container_app_job.wid[each.key].id
  role_definition_name = "Container Apps Jobs Operator"
  principal_id         = var.verification_principal_id
}

# A full PUT from the azurerm provider drops additional ports, so the PATCH is re-applied whenever the app inputs change.
resource "azapi_resource_action" "wid_private_listener" {
  for_each = var.workload_enabled ? local.wid_private_listeners : {}

  type        = "Microsoft.App/containerApps@2024-03-01"
  resource_id = azurerm_container_app.member[each.key].id
  method      = "PATCH"
  when        = "apply"
  headers = {
    "x-waooaw-listener-sync" = sha256(jsonencode({
      image       = local.image_refs[each.key]
      environment = local.runtime_environment[each.key]
      port        = each.value
    }))
  }
  body = {
    properties = {
      configuration = {
        ingress = {
          additionalPortMappings = [{
            external    = false
            targetPort  = each.value
            exposedPort = each.value
          }]
        }
      }
    }
  }
}

locals {
  wid_alert_rules = var.workload_enabled && var.log_analytics_workspace_id != "" ? {
    "wid-issuer-failed" = {
      description = "ADR-046 Amendment 1: an issuer or rotator execution failed."
      severity    = 1
      frequency   = "PT5M"
      window      = "PT15M"
      query       = <<-EOT
        union isfuzzy=true ContainerAppConsoleLogs, ContainerAppConsoleLogs_CL
        | extend Job = tostring(column_ifexists("ContainerJobName", column_ifexists("ContainerJobName_s", ""))),
            Line = tostring(column_ifexists("Log", column_ifexists("Log_s", "")))
        | where Job startswith "${local.wid_job_prefix}" and Line startswith "wid_issuer " and Line has "result=failed"
      EOT
    }
    "wid-leaf-issuer-silent" = {
      description = "ADR-046 Amendment 1: no successful leaf issuance for 2 hours."
      severity    = 1
      frequency   = "PT15M"
      window      = "PT2H"
      query       = <<-EOT
        let Successes = toscalar(
          union isfuzzy=true ContainerAppConsoleLogs, ContainerAppConsoleLogs_CL
          | extend Line = tostring(column_ifexists("Log", column_ifexists("Log_s", "")))
          | where Line startswith "wid_issuer mode=leaf result=ok"
          | count);
        print Reason = "NO_SUCCESSFUL_LEAF_ISSUANCE" | where Successes == 0
      EOT
    }
    "wid-credential-warning" = {
      description = "ADR-046 Amendment 1: a published workload credential has under 12 hours remaining."
      severity    = 2
      frequency   = "PT15M"
      window      = "PT1H"
      query       = <<-EOT
        union isfuzzy=true ContainerAppConsoleLogs, ContainerAppConsoleLogs_CL
        | extend Line = tostring(column_ifexists("Log", column_ifexists("Log_s", "")))
        | where Line startswith "wid_status workload="
        | extend Workload = extract(@"workload=(\S+)", 1, Line), Remaining = toint(extract(@"remaining_seconds=(\d+)", 1, Line))
        | summarize arg_max(TimeGenerated, Remaining) by Workload
        | where Remaining < 12 * 3600
      EOT
    }
    "wid-credential-critical" = {
      description = "ADR-046 Amendment 1: a published workload credential has under 4 hours remaining."
      severity    = 0
      frequency   = "PT5M"
      window      = "PT1H"
      query       = <<-EOT
        union isfuzzy=true ContainerAppConsoleLogs, ContainerAppConsoleLogs_CL
        | extend Line = tostring(column_ifexists("Log", column_ifexists("Log_s", "")))
        | where Line startswith "wid_status workload="
        | extend Workload = extract(@"workload=(\S+)", 1, Line), Remaining = toint(extract(@"remaining_seconds=(\d+)", 1, Line))
        | summarize arg_max(TimeGenerated, Remaining) by Workload
        | where Remaining < 4 * 3600
      EOT
    }
    "wid-ca-expiry" = {
      description = "ADR-046 Amendment 1: the intermediate or root CA certificate has under 14 days remaining."
      severity    = 1
      frequency   = "PT1H"
      window      = "P2D"
      query       = <<-EOT
        union isfuzzy=true ContainerAppConsoleLogs, ContainerAppConsoleLogs_CL
        | extend Line = tostring(column_ifexists("Log", column_ifexists("Log_s", "")))
        | where Line startswith "wid_status ca "
        | extend Intermediate = toint(extract(@"intermediate_days=(\d+)", 1, Line)), Root = toint(extract(@"root_days=(\d+)", 1, Line))
        | summarize arg_max(TimeGenerated, Intermediate, Root)
        | where Intermediate < 14 or Root < 14
      EOT
    }
  } : {}
}

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "wid" {
  for_each = local.wid_alert_rules

  name                    = "waooaw-${var.environment}-${each.key}"
  resource_group_name     = var.resource_group_name
  location                = var.location
  scopes                  = [var.log_analytics_workspace_id]
  description             = each.value.description
  enabled                 = true
  severity                = each.value.severity
  evaluation_frequency    = each.value.frequency
  window_duration         = each.value.window
  auto_mitigation_enabled = true

  criteria {
    query                   = each.value.query
    time_aggregation_method = "Count"
    operator                = "GreaterThan"
    threshold               = 0
    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  dynamic "action" {
    for_each = var.workload_identity_alert_action_group_id == null ? [] : [1]
    content {
      action_groups = [var.workload_identity_alert_action_group_id]
    }
  }

  tags = {
    adr = "ADR-046-amendment-1"
  }
}
