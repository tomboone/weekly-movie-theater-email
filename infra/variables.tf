variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "tbc-weekly-movie-email"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus2"
}

# Existing resource references
variable "app_service_plan_name" {
  description = "Name of the existing App Service Plan"
  type        = string
}

variable "app_service_plan_rg" {
  description = "Resource group of the existing App Service Plan"
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Resource ID of the existing Log Analytics workspace"
  type        = string
}

# Existing Communication Service
variable "acs_name" {
  description = "Name of the existing Azure Communication Services instance"
  type        = string
}

variable "acs_rg" {
  description = "Resource group of the existing ACS instance"
  type        = string
}

# App configuration (sensitive)
variable "regal_cinema_id" {
  description = "Regal theater 4-digit cinema ID"
  type        = string
}

variable "tmdb_api_key" {
  description = "TMDB bearer token"
  type        = string
  sensitive   = true
}

variable "email_from" {
  description = "Sender email address from existing ACS email domain"
  type        = string
}

variable "email_to" {
  description = "Recipient email address"
  type        = string
}

variable "trigger_api_key" {
  description = "Bearer token for the /trigger endpoint"
  type        = string
  sensitive   = true
}

variable "ghcr_image" {
  description = "Full GHCR image reference (e.g. ghcr.io/user/repo:latest)"
  type        = string
}
