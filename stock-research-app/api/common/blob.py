from __future__ import annotations

import datetime
from typing import Optional, Tuple
from azure.storage.blob import (
    BlobServiceClient,
    ContentSettings,
    generate_blob_sas,
    BlobSasPermissions,
)
from .config import Settings, get_storage_connection_string

_bs_client: Optional[BlobServiceClient] = None

def _get_service_client() -> BlobServiceClient:
    global _bs_client
    if _bs_client is None:
        cs = get_storage_connection_string()
        _bs_client = BlobServiceClient.from_connection_string(cs)
    return _bs_client

def ensure_container(container_name: str) -> None:
    svc = _get_service_client()
    try:
        svc.create_container(container_name)
    except Exception:
        # Likely already exists
        pass

def upload_text(container: str, blob_path: str, text: str, content_type: str = "text/plain; charset=utf-8") -> str:
    ensure_container(container)
    blob = _get_service_client().get_blob_client(container=container, blob=blob_path)
    blob.upload_blob(text.encode("utf-8"), overwrite=True, content_settings=ContentSettings(content_type=content_type))
    return get_blob_url(container, blob_path)

def upload_bytes(container: str, blob_path: str, data: bytes, content_type: str) -> str:
    ensure_container(container)
    blob = _get_service_client().get_blob_client(container=container, blob=blob_path)
    blob.upload_blob(data, overwrite=True, content_settings=ContentSettings(content_type=content_type))
    return get_blob_url(container, blob_path)

def get_blob_url(container: str, blob_path: str) -> str:
    blob = _get_service_client().get_blob_client(container=container, blob=blob_path)
    return blob.url

def _parse_account_info_from_conn_string(cs: str) -> Tuple[Optional[str], Optional[str]]:
    # Example: DefaultEndpointsProtocol=https;AccountName=foo;AccountKey=BASE64==;EndpointSuffix=core.windows.net
    parts = dict(
        kv.split("=", 1) for kv in cs.split(";") if "=" in kv
    )
    return parts.get("AccountName"), parts.get("AccountKey")

def make_read_sas_url(container: str, blob_path: str, minutes: int = 60) -> str:
    """
    Generates a time-limited read-only SAS URL for the given blob.
    """
    svc = _get_service_client()
    account_name, account_key = _parse_account_info_from_conn_string(svc.credential.account_key if hasattr(svc, "credential") and hasattr(svc.credential, "account_key") else get_storage_connection_string())
    # Fallback parse if svc.credential doesn't expose key
    if not account_name or not account_key:
        account_name, account_key = _parse_account_info_from_conn_string(get_storage_connection_string())

    if not account_name or not account_key:
        raise RuntimeError("Unable to derive storage account name/key for SAS generation.")

    expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
    sas = generate_blob_sas(
        account_name=account_name,
        container_name=container,
        blob_name=blob_path,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=expiry,
    )
    return f"{get_blob_url(container, blob_path)}?{sas}"
