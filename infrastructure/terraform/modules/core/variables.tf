variable "environment"             { type = string }
variable "location"               { type = string }
variable "postgres_sku_name"      { type = string }
variable "postgres_storage_mb"    { type = number }
variable "postgres_admin_password"{ type = string; sensitive = true }
variable "postgres_version"       { type = string }
variable "keycloak_admin_password"{ type = string; sensitive = true }
variable "ghcr_server"            { type = string }
variable "ghcr_username"          { type = string }
variable "ghcr_token"             { type = string; sensitive = true }
variable "image_org"              { type = string }
variable "image_tag"              { type = string }
variable "ce_min_replicas"        { type = number }
variable "ce_max_replicas"        { type = number }
variable "default_min_replicas"   { type = number }
variable "default_max_replicas"   { type = number }
variable "log_retention_days"     { type = number }
variable "tags"                   { type = map(string) }

# ─── LLM Provider variables (ADR-029 — Multi-Provider Strategy) ──────────────
# FA-021: Google Vertex AI (primary MID_TIER + FRONTIER)
variable "google_vertex_project_id" {
  type        = string
  description = "GCP project ID with Vertex AI API enabled (FA-021). Set to 'placeholder' until FA-021 complete."
  default     = "placeholder-fa021-required"
}
variable "google_vertex_sa_key" {
  type        = string
  sensitive   = true
  description = "Google Cloud service account JSON key for Vertex AI (FA-021). Never commit this value."
  default     = "{}"
}
# FA-022: Sarvam AI (MID_TIER Agricultural override)
variable "sarvam_api_key" {
  type        = string
  sensitive   = true
  description = "Sarvam AI API key for Saaras model (FA-022). Register at sarvam.ai."
  default     = "placeholder-fa022-required"
}
