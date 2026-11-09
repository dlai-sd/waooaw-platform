variable "whatsapp_monitoring_workspace_id" {
  description = "Canonical foundation workspace; unavailable old state fails monitoring deployment closed."
  type        = string
  default     = ""
}

variable "whatsapp_monitoring" {
  description = "Optional reviewed Demo-only alert plan. Null creates no resources; this is not traffic or spend authority."
  type = object({
    workspace_id         = string
    action_group_id      = string
    approval_reference   = string
    query_digest         = string
    activation_digest    = string
    release_digest       = string
    configuration_digest = string
    starts_at            = string
    expires_at           = string
  })
  default  = null
  nullable = true

  validation {
    condition = var.whatsapp_monitoring == null ? true : (
      var.environment == "demo" &&
      can(regex("^/subscriptions/[0-9a-f-]{36}/resourceGroups/waooaw-demo-rg/providers/Microsoft[.]OperationalInsights/workspaces/[A-Za-z0-9_-]+$", var.whatsapp_monitoring.workspace_id)) &&
      can(regex("^/subscriptions/[0-9a-f-]{36}/resourceGroups/waooaw-demo-rg/providers/Microsoft[.]Insights/actionGroups/[A-Za-z0-9_-]+$", var.whatsapp_monitoring.action_group_id)) &&
      try(split("/", var.whatsapp_monitoring.workspace_id)[2] == split("/", var.whatsapp_monitoring.action_group_id)[2], false) &&
      can(regex("^[A-Za-z0-9][A-Za-z0-9:._/-]{0,255}$", var.whatsapp_monitoring.approval_reference)) &&
      var.whatsapp_monitoring.query_digest == "sha256:${filesha256("${path.module}/../../../../operations/wc134-whatsapp-monitor.kql")}" &&
      can(regex("^[0-9a-f]{64}$", var.whatsapp_monitoring.activation_digest)) &&
      alltrue([for digest in [var.whatsapp_monitoring.release_digest, var.whatsapp_monitoring.configuration_digest] : can(regex("^sha256:[0-9a-f]{64}$", digest))]) &&
      endswith(var.image_digests["business-platform"], "@${var.whatsapp_monitoring.release_digest}") &&
      can(regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$", var.whatsapp_monitoring.starts_at)) &&
      can(regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$", var.whatsapp_monitoring.expires_at)) &&
      try(timecmp(var.whatsapp_monitoring.starts_at, var.whatsapp_monitoring.expires_at) < 0, false)
    )
    error_message = "WhatsApp monitoring requires a reviewed Demo workspace/action-group tuple, exact release/configuration/activation digests and a bounded UTC window."
  }
}

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "whatsapp_operations" {
  count                   = var.workload_enabled && var.whatsapp_monitoring != null ? 1 : 0
  name                    = "waooaw-demo-whatsapp-operations"
  resource_group_name     = var.resource_group_name
  location                = var.location
  scopes                  = [var.whatsapp_monitoring.workspace_id]
  description             = "WC-134 bounded operational breaches and missing evaluator/exporter heartbeat. Human acknowledgement and Stop remain operator actions."
  enabled                 = true
  severity                = 1
  evaluation_frequency    = "PT1M"
  window_duration         = "PT5M"
  auto_mitigation_enabled = true

  criteria {
    query = templatefile("${path.module}/../../../../operations/wc134-whatsapp-monitor.kql", {
      starts_at            = var.whatsapp_monitoring.starts_at
      expires_at           = var.whatsapp_monitoring.expires_at
      activation_digest    = var.whatsapp_monitoring.activation_digest
      release_digest       = var.whatsapp_monitoring.release_digest
      configuration_digest = var.whatsapp_monitoring.configuration_digest
    })
    time_aggregation_method = "Count"
    operator                = "GreaterThan"
    threshold               = 0
    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [var.whatsapp_monitoring.action_group_id]
    custom_properties = {
      workContract        = "WC-134"
      environment         = "demo"
      activationDigest    = var.whatsapp_monitoring.activation_digest
      releaseDigest       = var.whatsapp_monitoring.release_digest
      configurationDigest = var.whatsapp_monitoring.configuration_digest
      queryDigest         = var.whatsapp_monitoring.query_digest
    }
  }

  tags = {
    work_contract      = "WC-134"
    approval_reference = var.whatsapp_monitoring.approval_reference
  }

  lifecycle {
    precondition {
      condition     = var.resource_group_name == "waooaw-demo-rg"
      error_message = "WhatsApp operational monitoring must not mutate an unrelated resource group."
    }
    precondition {
      condition     = var.whatsapp_monitoring.workspace_id == var.whatsapp_monitoring_workspace_id
      error_message = "WhatsApp monitoring requires the current canonical foundation workspace output."
    }
  }
}
