from __future__ import annotations

import os
from typing import Dict, Optional

# Google ID token verification
# Uses google-auth to verify JWT from Google Identity Services.
try:
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
except Exception:  # pragma: no cover
    id_token = None  # type: ignore
    google_requests = None  # type: ignore

def verify_google_id_token(token: str) -> Optional[Dict[str, str]]:
    """
    Verifies a Google ID token (JWT) and returns a user dict:
      {"userId": sub, "name": name, "email": email, "provider": "google"}
    Returns None if verification fails or not configured.
    """
    if not token or not id_token or not google_requests:
        return None

    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    if not client_id:
        return None

    try:
        request = google_requests.Request()
        info = id_token.verify_oauth2_token(token, request, audience=client_id)
        # Expected fields: sub (user id), email, name, picture, iss, aud, etc.
        sub = info.get("sub")
        email = info.get("email")
        name = info.get("name") or email or sub
        if not sub:
            return None
        return {"userId": sub, "name": name, "email": email or "", "provider": "google"}
    except Exception:
        return None
