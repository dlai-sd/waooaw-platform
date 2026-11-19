# Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R009, WC135-R014
# Constitutional basis: C-009, C-023, C-026, C-048, C-059, C-063
# Visitor conversation settings. Only non-secret values live here: protected fields use the pinned Key Vault
# phone-subject key versions (see whatsapp.tf), and the simulator stays disabled unless a test run enables it.

variable "visitor_conversation" {
  description = "Scripted visitor conversation: LEGACY keeps the WC-134 behaviour, V2 uses the scripted content set. Lead retention is configurable per environment."
  type = object({
    mode                      = string
    default_tenant_id         = optional(string)
    lead_retention_days       = optional(number, 90)
    simulation_retention_days = optional(number, 7)
    handoff_open_base_url     = optional(string, "")
  })
  default = {
    mode = "LEGACY"
  }

  validation {
    condition = (
      contains(["LEGACY", "V2"], var.visitor_conversation.mode) &&
      (var.visitor_conversation.default_tenant_id == null || can(regex("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", coalesce(var.visitor_conversation.default_tenant_id, "x")))) &&
      var.visitor_conversation.lead_retention_days == floor(var.visitor_conversation.lead_retention_days) &&
      var.visitor_conversation.lead_retention_days >= 30 && var.visitor_conversation.lead_retention_days <= 365 &&
      var.visitor_conversation.simulation_retention_days == floor(var.visitor_conversation.simulation_retention_days) &&
      var.visitor_conversation.simulation_retention_days >= 1 && var.visitor_conversation.simulation_retention_days <= 30
    )
    error_message = "Visitor conversation mode must be LEGACY or V2, the tenant a lower-case UUID, lead retention 30 to 365 days and simulation retention 1 to 30 days."
  }
}

locals {
  visitor_conversation_runtime = merge(
    {
      VisitorConversation__Mode               = var.visitor_conversation.mode
      VisitorConversation__PublicEntryEnabled = "false"
      VisitorConversation__SimulatorEnabled   = "false"
      VisitorLeads__RetentionDays             = tostring(var.visitor_conversation.lead_retention_days)
      VisitorLeads__SimulationRetentionDays   = tostring(var.visitor_conversation.simulation_retention_days)
    },
    var.visitor_conversation.handoff_open_base_url == "" ? {} : {
      VisitorConversation__HandoffOpenBaseUrl = var.visitor_conversation.handoff_open_base_url
    },
    var.visitor_conversation.default_tenant_id == null ? {} : {
      VisitorConversation__DefaultTenantId = var.visitor_conversation.default_tenant_id
    }
  )
}
