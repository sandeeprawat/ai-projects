/* Minimal Google Identity Services helper */
declare global {
  interface Window {
    google?: any;
    __GOOGLE_CLIENT_ID__?: string;
  }
}

type JwtClaims = {
  sub?: string;
  email?: string;
  name?: string;
  picture?: string;
  [k: string]: any;
};

const TOKEN_KEY = "google_id_token";

export function getGoogleClientId(): string | undefined {
  return window.__GOOGLE_CLIENT_ID__;
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
  window.dispatchEvent(new CustomEvent("auth:changed", { detail: { token } }));
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  window.dispatchEvent(new CustomEvent("auth:changed", { detail: { token: null } }));
}

export function decodeJwt(t: string | null | undefined): JwtClaims | null {
  if (!t) return null;
  try {
    const parts = t.split(".");
    if (parts.length !== 3) return null;
    let payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    while (payload.length % 4) payload += "="; // pad for base64
    const json = JSON.parse(atob(payload));
    return json as JwtClaims;
  } catch {
    return null;
  }
}

export function getUser(): { id?: string; email?: string; name?: string; picture?: string } | null {
  const claims = decodeJwt(getToken());
  if (!claims?.sub) return null;
  return {
    id: claims.sub,
    email: claims.email,
    name: claims.name || claims.email || claims.sub,
    picture: claims.picture
  };
}

export function initGoogle(onSignedIn?: () => void, renderInto?: HTMLElement | null) {
  const clientId = getGoogleClientId();
  if (!clientId) return;

  const cb = (resp: any) => {
    const cred = resp?.credential;
    if (typeof cred === "string" && cred.length > 0) {
      setToken(cred);
      try { onSignedIn?.(); } catch {}
      // Ensure UI refresh after sign-in
      if (!location.hash || location.hash === "#" || location.hash === "") {
        location.hash = "/schedules";
      }
      setTimeout(() => location.reload(), 50);
    }
  };

  const renderBtn = () => {
    if (!window.google) return;
    try {
      window.google.accounts.id.initialize({ client_id: clientId, callback: cb });
      if (renderInto) {
        window.google.accounts.id.renderButton(renderInto, {
          theme: "outline",
          size: "large"
        });
      } else {
        // One Tap fallback (optional)
        window.google.accounts.id.prompt();
      }
    } catch {
      // ignore
    }
  };

  if (window.google) {
    renderBtn();
  } else {
    // wait for script load
    let tries = 0;
    const timer = setInterval(() => {
      tries++;
      if (window.google) {
        clearInterval(timer);
        renderBtn();
      } else if (tries > 100) {
        clearInterval(timer);
      }
    }, 100);
  }
}
