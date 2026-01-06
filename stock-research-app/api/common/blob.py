from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from azure.storage.blob import (
    BlobServiceClient,
    ContentSettings,
    generate_blob_sas,
    BlobSasPermissions,
    UserDelegationKey,
)

from .config import get_storage_connection_string, Settings

# Cache for user delegation key
_user_delegation_key: Optional[UserDelegationKey] = None
_user_delegation_key_expiry: Optional[datetime] = None


def _get_credential():
    """Get credential for Managed Identity if configured."""
    if Settings.AZURE_STORAGE_ACCOUNT_NAME and Settings.AZURE_CLIENT_ID:
        from azure.identity import ManagedIdentityCredential
        return ManagedIdentityCredential(client_id=Settings.AZURE_CLIENT_ID)
    elif Settings.AZURE_STORAGE_ACCOUNT_NAME:
        from azure.identity import DefaultAzureCredential
        return DefaultAzureCredential()
    return None


def _svc() -> BlobServiceClient:
    # Check if we should use Managed Identity
    if Settings.AZURE_STORAGE_ACCOUNT_NAME:
        credential = _get_credential()
        if credential:
            account_url = f"https://{Settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
            return BlobServiceClient(account_url, credential=credential)
    
    # Fall back to connection string
    conn = get_storage_connection_string()
    if conn.strip().lower() == "usedevelopmentstorage=true":
        # Expand Azurite shorthand into a full connection string azure-storage-blob can parse
        conn = (
            "DefaultEndpointsProtocol=http;"
            "AccountName=devstoreaccount1;"
            "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
            "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
            "QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;"
            "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
        )
    return BlobServiceClient.from_connection_string(conn)

def _ensure_container(svc: BlobServiceClient, container: str) -> None:
    try:
        svc.create_container(container)
    except Exception:
        # Likely exists
        pass

def _content_settings(content_type: Optional[str]) -> Optional[ContentSettings]:
    if not content_type:
        return None
    return ContentSettings(content_type=content_type)

def upload_text(container: str, blob_path: str, text: str, content_type: Optional[str] = None) -> str:
    svc = _svc()
    _ensure_container(svc, container)
    bc = svc.get_blob_client(container=container, blob=blob_path)
    bc.upload_blob(text.encode("utf-8"), overwrite=True, content_settings=_content_settings(content_type))
    return bc.url

def upload_bytes(container: str, blob_path: str, data: bytes, content_type: Optional[str] = None) -> str:
    svc = _svc()
    _ensure_container(svc, container)
    bc = svc.get_blob_client(container=container, blob=blob_path)
    bc.upload_blob(data, overwrite=True, content_settings=_content_settings(content_type))
    return bc.url

def _try_parse_account_from_conn_str(conn_str: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Returns (account_name, account_key, blob_endpoint) if present in the connection string.
    Works for both Azurite and Azure Storage connection strings.
    """
    if not conn_str:
        return None, None, None
    parts = {}
    for seg in conn_str.split(";"):
        if "=" in seg:
            k, v = seg.split("=", 1)
            parts[k.strip()] = v.strip()
    account_name = parts.get("AccountName")
    account_key = parts.get("AccountKey")
    blob_endpoint = parts.get("BlobEndpoint")
    return account_name, account_key, blob_endpoint

def make_read_sas_url(container: str, blob_path: str, expiry_hours: int = 48) -> Optional[str]:
    """
    Builds a read-only SAS URL for the given blob. 
    Uses User Delegation SAS with Managed Identity when available, otherwise falls back to account key.
    Returns None if credentials are unavailable.
    """
    global _user_delegation_key, _user_delegation_key_expiry
    
    expiry_time = datetime.now(timezone.utc) + timedelta(hours=max(1, int(expiry_hours)))
    
    # Try Managed Identity with User Delegation SAS first
    if Settings.AZURE_STORAGE_ACCOUNT_NAME:
        try:
            svc = _svc()
            account_name = Settings.AZURE_STORAGE_ACCOUNT_NAME
            blob_endpoint = f"https://{account_name}.blob.core.windows.net"
            
            # Get or refresh user delegation key (valid for up to 7 days, we refresh every 6 hours)
            now = datetime.now(timezone.utc)
            if _user_delegation_key is None or _user_delegation_key_expiry is None or now >= _user_delegation_key_expiry:
                key_start = now - timedelta(minutes=5)  # Start slightly in the past
                key_expiry = now + timedelta(hours=6)   # 6-hour validity
                _user_delegation_key = svc.get_user_delegation_key(key_start, key_expiry)
                _user_delegation_key_expiry = key_expiry
            
            from azure.storage.blob import generate_blob_sas
            sas = generate_blob_sas(
                account_name=account_name,
                container_name=container,
                blob_name=blob_path,
                user_delegation_key=_user_delegation_key,
                permission=BlobSasPermissions(read=True),
                expiry=expiry_time,
            )
            return f"{blob_endpoint}/{container}/{blob_path}?{sas}"
        except Exception:
            # Fall through to connection string method
            pass
    
    conn = get_storage_connection_string()

    # Handle Azurite shorthand
    if conn.strip().lower() == "usedevelopmentstorage=true":
        # Known Azurite defaults
        account_name = "devstoreaccount1"
        # Public Azurite default key from docs
        account_key = (
            "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=="
        )
        blob_endpoint = f"http://127.0.0.1:10000/{account_name}"
    else:
        account_name, account_key, blob_endpoint = _try_parse_account_from_conn_str(conn)
        if not (account_name and account_key):
            # Cannot create SAS without key
            return None
        if not blob_endpoint:
            # Derive default endpoint
            blob_endpoint = f"https://{account_name}.blob.core.windows.net"

    try:
        sas = generate_blob_sas(
            account_name=account_name,
            container_name=container,
            blob_name=blob_path,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expiry_time,
        )
        return f"{blob_endpoint}/{container}/{blob_path}?{sas}"
    except Exception:
        return None

def delete_blob(container: str, blob_path: str) -> bool:
    """
    Deletes a blob if it exists. Returns True if deletion succeeded (or blob didn't exist),
    False only on unexpected errors.
    """
    try:
        svc = _svc()
        bc = svc.get_blob_client(container=container, blob=blob_path)
        bc.delete_blob(delete_snapshots="include")
        return True
    except Exception:
        # Consider non-existent blob as success for idempotency
        return False
