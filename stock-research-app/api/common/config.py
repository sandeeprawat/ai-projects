import os

def _val(name: str, default: str = "") -> str:
    v = os.getenv(name, default)
    v = (v or "").strip()
    return "" if v in ("", "REPLACE_ME") else v

class Settings:
    FUNCTIONS_WORKER_RUNTIME = os.getenv("FUNCTIONS_WORKER_RUNTIME", "python")
    AzureWebJobsStorage = os.getenv("AzureWebJobsStorage", "UseDevelopmentStorage=true")

    AZURE_OPENAI_ENDPOINT = _val("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY = _val("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    AZURE_OPENAI_DEPLOYMENT = _val("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

    BING_V7_ENDPOINT = os.getenv("BING_V7_ENDPOINT", "https://api.bing.microsoft.com")
    BING_V7_KEY = _val("BING_V7_KEY")

    COSMOS_DB_URL = os.getenv("COSMOS_DB_URL", "")
    COSMOS_DB_KEY = _val("COSMOS_DB_KEY")
    COSMOS_DB_NAME = os.getenv("COSMOS_DB_NAME", "stockresearch")

    REPORTS_CONTAINER = os.getenv("REPORTS_CONTAINER", "reports")
    REPORT_RETENTION_DAYS = os.getenv("REPORT_RETENTION_DAYS", "0")

    ACS_CONNECTION_STRING = _val("ACS_CONNECTION_STRING")
    EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")

    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:7071")
    AZURE_OAI_ASSISTANT_ID = _val("AZURE_OAI_ASSISTANT_ID")

    # Azure AI Projects (used for Agents via azure-ai-projects SDK)
    AZURE_AI_PROJECTS_ENDPOINT = _val("AZURE_AI_PROJECTS_ENDPOINT")
    AZURE_AI_PROJECTS_PROJECT = _val("AZURE_AI_PROJECTS_PROJECT")
    AZURE_AI_PROJECTS_AGENT_ID = _val("AZURE_AI_PROJECTS_AGENT_ID")


def get_storage_connection_string() -> str:
    """
    Returns the Azure Storage connection string for Functions bindings and blob ops.
    Defaults to Azurite when not provided.
    """
    return os.getenv("AzureWebJobsStorage", "UseDevelopmentStorage=true")
