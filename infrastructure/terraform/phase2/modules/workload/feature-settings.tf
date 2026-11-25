# Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R001, WC137-R002
# Constitutional basis: C-009, C-023, C-059, C-063
# Per-environment feature settings and platform access. Only non-secret values live here. The module defaults
# are the safe, off values; each environment's workload-configuration.json decides what is turned on, so
# switching a feature for Demo, UAT or Production is a configuration edit and never a code change.

variable "feature_settings" {
  description = "Closed set of non-secret feature switches. Every value defaults to the pre-WC-136 behaviour."
  type = object({
    workbench_enabled                     = optional(bool, false)
    wallet_authority                      = optional(string, "LEGACY")
    trial_identity_binding_mode           = optional(string, "RECORD")
    whatsapp_stop_acknowledgement_enabled = optional(bool, false)
    # Demo and UAT only (ADR-055 decision 4); the validation below refuses it for Production.
    acceptance_synthetic_tenants_enabled = optional(bool, false)
    # WC-170: the employment protocol gate and its rollback epoch. The epoch is never reused; raising it blocks in-flight commands.
    employment_protocol_enabled        = optional(bool, false)
    employment_protocol_rollback_epoch = optional(number, 0)
    # WC-170: the web switch that moves the conversation stories from the stream route to the events route.
    web_conversation_enabled = optional(bool, false)
  })
  default = {}

  validation {
    condition = (
      contains(["LEGACY", "SHADOW", "WALLET"], var.feature_settings.wallet_authority) &&
      contains(["OFF", "RECORD", "ENFORCE"], var.feature_settings.trial_identity_binding_mode)
    )
    error_message = "wallet_authority must be LEGACY, SHADOW or WALLET and trial_identity_binding_mode must be OFF, RECORD or ENFORCE."
  }

  validation {
    condition = (
      var.feature_settings.employment_protocol_rollback_epoch >= 0 &&
      var.feature_settings.employment_protocol_rollback_epoch == floor(var.feature_settings.employment_protocol_rollback_epoch)
    )
    error_message = "employment_protocol_rollback_epoch must be a whole number of at least 0."
  }

  validation {
    condition     = var.environment != "prod" || !var.feature_settings.acceptance_synthetic_tenants_enabled
    error_message = "acceptance_synthetic_tenants_enabled exists only for Demo and UAT and cannot be enabled in Production."
  }
}

variable "platform_access" {
  description = "Founder identities for this environment. The Business Platform re-asserts them at every start, so they survive redeploys, database resets and fresh databases."
  type = object({
    founders = optional(list(object({
      email           = string
      subject         = optional(string)
      rebind_on_start = optional(bool, false)
    })), [])
  })
  default = {}

  validation {
    condition = alltrue([
      for founder in var.platform_access.founders :
      can(regex("^[a-z0-9._%+-]+@[a-z0-9.-]+[.][a-z]{2,}$", founder.email)) &&
      (founder.subject == null ? true : can(regex("^[A-Za-z0-9._:@-]{8,128}$", founder.subject))) &&
      !(founder.rebind_on_start && founder.subject != null)
    ])
    error_message = "Every Founder needs a lower-case email address; an optional identity-provider subject must be 8 to 128 safe characters, and rebind_on_start cannot be combined with a subject."
  }
}

locals {
  feature_settings_runtime = {
    "business-platform" = merge(
      {
        Workbench__Enabled                           = tostring(var.feature_settings.workbench_enabled)
        Protocol__WhatsAppStopAcknowledgementEnabled = tostring(var.feature_settings.whatsapp_stop_acknowledgement_enabled)
        AcceptanceSyntheticTenants__Enabled          = tostring(var.feature_settings.acceptance_synthetic_tenants_enabled)
        EmploymentProtocol__GateId                   = "conversational-employment-candidate-v1"
        EmploymentProtocol__Enabled                  = tostring(var.feature_settings.employment_protocol_enabled)
        EmploymentProtocol__RollbackEpoch            = tostring(var.feature_settings.employment_protocol_rollback_epoch)
        EmploymentReadiness__Environment             = var.environment
        EmploymentReadiness__ProfessionalRuntimeUrl  = local.service_urls.professional_runtime
        EmploymentReadiness__AiRuntimeUrl            = local.service_urls.ai_runtime
        EmploymentReadiness__DomainAdapterUrl        = local.service_urls.dma_adapter
      },
      merge([
        for index, founder in var.platform_access.founders : merge(
          { "PlatformAccess__Founders__${index}__Email" = founder.email },
          founder.subject == null ? {} : { "PlatformAccess__Founders__${index}__Subject" = founder.subject },
          founder.rebind_on_start ? { "PlatformAccess__Founders__${index}__RebindOnStart" = "true" } : {}
        )
      ]...)
    )
    "web" = {
      WC120_CONVERSATION_ENABLED = tostring(var.feature_settings.web_conversation_enabled)
    }
    "billing-engine" = {
      WALLET_AUTHORITY            = var.feature_settings.wallet_authority
      TRIAL_IDENTITY_BINDING_MODE = var.feature_settings.trial_identity_binding_mode
    }
  }
}
