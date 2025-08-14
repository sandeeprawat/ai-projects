import os
from typing import Optional


def env(name: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    val = os.environ.get(name, default)
    if required and not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


class Settings:
    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT = env("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY = env("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_API_VERSION = env("AZURE_OPENAI_API_VERSION", "2024-06-01")
    AZURE_OPENAI_DEPLOYMENT = env("AZURE_OPENAI_DEPLOYMENT")  # model deployment name

    # Bing Search (Azure AI Services)
    BING_V7_ENDPOINT = env("BING_V7_ENDPOINT", "https://api.bing.microsoft.com")
    BING_V7_KEY = env("BING_V7_KEY")

    # Storage (reports)
    REPORTS_CONTAINER = env("REPORTS_CONTAINER", "reports")
    BLOB_CONNECTION_STRING = env("BLOB_CONNECTION_STRING")  # optional; fall back to AzureWebJobsStorage
    AZURE_WEBJOBS_STORAGE = env("AzureWebJobsStorage")  # Functions default storage

    # Cosmos DB
    COSMOS_DB_URL = env("COSMOS_DB_URL")
    COSMOS_DB_KEY = env("COSMOS_DB_KEY")
    COSMOS_DB_NAME = env("COSMOS_DB_NAME", "stockresearch")
    COSMOS_CONTAINER_SCHEDULES = env("COSMOS_CONTAINER_SCHEDULES", "schedules")
    COSMOS_CONTAINER_RUNS = env("COSMOS_CONTAINER_RUNS", "runs")
    COSMOS_CONTAINER_REPORTS = env("COSMOS_CONTAINER_REPORTS", "reports")

    # Email (Azure Communication Services)
    ACS_CONNECTION_STRING = env("ACS_CONNECTION_STRING")
    EMAIL_SENDER = env("EMAIL_SENDER")  # e.g., DoNotReply@xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.azurecomm.net

    # Misc
    APP_BASE_URL = env("APP_BASE_URL")  # used to build links in emails
    ENV = env("APP_ENV", "dev")


def get_storage_connection_string() -> str:
    """
    Returns a connection string usable by azure-storage-blob.
    Prefers explicit BLOB_CONNECTION_STRING, falls back to AzureWebJobsStorage.
    """
    cs = Settings.BLOB_CONNECTION_STRING or Settings.AZURE_WEBJOBS_STORAGE
    if not cs:
        raise RuntimeError("No storage connection string configured (BLOB_CONNECTION_STRING or AzureWebJobsStorage).")
    return cs
