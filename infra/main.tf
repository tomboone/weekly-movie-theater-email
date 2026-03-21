# Existing resources
data "azurerm_service_plan" "existing" {
  name                = var.app_service_plan_name
  resource_group_name = var.app_service_plan_rg
}

resource "azurerm_application_insights" "main" {
  name                = "${var.project_name}-insights"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  application_type    = "web"
  workspace_id        = var.log_analytics_workspace_id
}

data "azurerm_communication_service" "existing" {
  name                = var.acs_name
  resource_group_name = var.acs_rg
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-rg"
  location = var.location
}


# App Service
resource "azurerm_linux_web_app" "main" {
  name                = var.project_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  service_plan_id     = data.azurerm_service_plan.existing.id

  site_config {
    application_stack {
      docker_image_name   = var.ghcr_image
      docker_registry_url = "https://ghcr.io"
    }
    always_on = true
  }

  app_settings = {
    REGAL_CINEMA_ID                     = var.regal_cinema_id
    TMDB_API_KEY                        = var.tmdb_api_key
    ACS_CONNECTION_STRING               = data.azurerm_communication_service.existing.primary_connection_string
    EMAIL_FROM                          = var.email_from
    EMAIL_TO                            = var.email_to
    MOVIE_STATE_PATH                    = "/home/data/movie_state.json"
    SCHEDULE_CRON                       = "0 10 * * 5"
    SCHEDULE_TIMEZONE                   = "America/New_York"
    TRIGGER_API_KEY                     = var.trigger_api_key
    WEBSITES_ENABLE_APP_SERVICE_STORAGE = "true"
    WEBSITES_PORT                       = "8000"
    APPINSIGHTS_INSTRUMENTATIONKEY      = azurerm_application_insights.main.instrumentation_key
  }

  logs {
    http_logs {
      file_system {
        retention_in_days = 7
        retention_in_mb   = 35
      }
    }
  }
}
