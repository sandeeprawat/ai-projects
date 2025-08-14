export async function getJson<T = any>(path: string): Promise<T> {
  const url = path.startsWith("http") ? path : `/api${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    method: "GET",
    headers: {
      Accept: "application/json"
    },
    credentials: "include"
  });
  if (!res.ok) {
    throw new Error(`GET ${url} failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export async function postJson<T = any>(path: string, body: any): Promise<T> {
  const url = path.startsWith("http") ? path : `/api${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json"
    },
    credentials: "include",
    body: JSON.stringify(body ?? {})
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`POST ${url} failed: ${res.status} ${res.statusText} ${text}`);
  }
  return (await res.json()) as T;
}
