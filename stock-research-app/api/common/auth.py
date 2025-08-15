import base64
import json
from typing import Optional, Dict
from .google_auth import verify_google_id_token

# Static Web Apps sends X-MS-CLIENT-PRINCIPAL with user info when using built-in auth.
# For local dev, we fall back to a fixed dev user.

def get_user_context(headers: Dict[str, str]) -> Dict[str, Optional[str]]:
    """
    Returns a dict with keys: userId, name, provider.
    """
    # First, try Authorization: Bearer (Google ID token for local/dev or custom frontends)
    authz = None
    for k, v in headers.items():
        if k.lower() == "authorization":
            authz = v
            break
    if authz and isinstance(authz, str) and authz.lower().startswith("bearer "):
        token = authz.split(" ", 1)[1].strip()
        user = verify_google_id_token(token)
        if user:
            return user

    principal_b64 = None
    # Headers can be case-insensitive; normalize access
    for k, v in headers.items():
        if k.lower() == "x-ms-client-principal":
            principal_b64 = v
            break

    if principal_b64:
        try:
            decoded = base64.b64decode(principal_b64)
            principal = json.loads(decoded.decode("utf-8"))
            user_id = principal.get("userId") or principal.get("userDetails")
            name = principal.get("userDetails") or principal.get("name")
            provider = principal.get("identityProvider")
            if user_id:
                return {"userId": user_id, "name": name, "provider": provider}
        except Exception:
            pass

    # Fallback for local development
    return {"userId": "dev-user", "name": "Developer", "provider": "local"}
