import { getToken } from "./auth";

// API URL is configured via VITE_API_URL environment variable
// - Production: Set in .env.production (e.g., https://your-function-app.azurewebsites.net)
// - Local dev: Empty string, Vite proxy handles /api requests
function getApiBase(): string {
  // Use env variable (set at build time via .env.production or VITE_API_URL)
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  // Local dev - use relative /api (Vite proxy handles it)
  return "";
}

const API_BASE = getApiBase();

function buildUrl(path: string): string {
  if (path.startsWith("http")) return path;
  const apiPath = path.startsWith("/") ? path : `/${path}`;
  return API_BASE ? `${API_BASE}/api${apiPath}` : `/api${apiPath}`;
}

export async function getJson<T = any>(path: string): Promise<T> {
  const url = buildUrl(path);
  const t = getToken();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (t) headers["Authorization"] = `Bearer ${t}`;

  const res = await fetch(url, {
    method: "GET",
    headers
  });
  if (!res.ok) throw new Error(`GET ${url} failed: ${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export async function postJson<T = any>(path: string, body: any): Promise<T> {
  const url = buildUrl(path);
  const t = getToken();
  const headers: Record<string, string> = { Accept: "application/json", "Content-Type": "application/json" };
  if (t) headers["Authorization"] = `Bearer ${t}`;

  const res = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(body ?? {})
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`POST ${url} failed: ${res.status} ${res.statusText} ${text}`);
  }
  return (await res.json()) as T;
}

export async function putJson<T = any>(path: string, body: any): Promise<T> {
  const url = buildUrl(path);
  const t = getToken();
  const headers: Record<string, string> = { Accept: "application/json", "Content-Type": "application/json" };
  if (t) headers["Authorization"] = `Bearer ${t}`;

  const res = await fetch(url, {
    method: "PUT",
    headers,
    body: JSON.stringify(body ?? {})
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`PUT ${url} failed: ${res.status} ${res.statusText} ${text}`);
  }
  return (await res.json()) as T;
}

export async function delJson<T = any>(path: string): Promise<T> {
  const url = buildUrl(path);
  const t = getToken();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (t) headers["Authorization"] = `Bearer ${t}`;

  const res = await fetch(url, {
    method: "DELETE",
    headers
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`DELETE ${url} failed: ${res.status} ${res.statusText} ${text}`);
  }
  const txt = await res.text();
  return (txt ? JSON.parse(txt) : ({} as any)) as T;
}

/* Domain helpers (types are lightweight to avoid extra imports) */
export type Recurrence = {
  cadence: "hourly" | "daily" | "weekly";
  interval: number;
  hour?: number | null;
  minute?: number | null;
  weekday?: number | null; // 0=Mon..6=Sun
};

export type EmailSettings = {
  to: string[];
  attachPdf: boolean;
};

export type Schedule = {
  id?: string;
  userId?: string;
  prompt?: string;
  symbols: string[];
  recurrence: Recurrence;
  email: EmailSettings;
  deepResearch?: boolean;
  active: boolean;
  nextRunAt?: string | null;
  createdAt?: string | null;
};

export type Report = {
  id: string;
  runId: string;
  scheduleId: string;
  userId: string;
  title: string;
  prompt?: string;
  symbols: string[];
  summary?: string | null;
  blobPaths: { md?: string; html?: string; pdf?: string };
  citations: { title?: string; url?: string }[];
  createdAt?: string;
  signedUrls?: { md?: string | null; html?: string | null; pdf?: string | null };
};

/* API wrappers */
export async function listSchedules(limit = 100): Promise<Schedule[]> {
  return getJson<Schedule[]>(`/schedules?limit=${encodeURIComponent(String(limit))}`);
}

export async function createSchedule(input: {
  prompt: string;
  symbols?: string[];
  recurrence: Recurrence;
  email: EmailSettings;
  deepResearch?: boolean;
  active?: boolean;
}): Promise<Schedule> {
  return postJson<Schedule>("/schedules", {
    prompt: input.prompt,
    symbols: input.symbols ?? [],
    recurrence: input.recurrence,
    email: input.email,
    deepResearch: input.deepResearch ?? false,
    active: input.active ?? true
  });
}

export async function updateSchedule(
  scheduleId: string,
  input: { prompt: string; symbols?: string[]; recurrence: Recurrence; email: EmailSettings; deepResearch?: boolean; active?: boolean }
): Promise<Schedule> {
  return putJson<Schedule>(`/schedules/${encodeURIComponent(scheduleId)}`, {
    prompt: input.prompt,
    symbols: input.symbols ?? [],
    recurrence: input.recurrence,
    email: input.email,
    deepResearch: input.deepResearch ?? false,
    active: input.active ?? true
  });
}

export async function runScheduleNow(scheduleId: string): Promise<{ instanceId: string; runId: string; scheduleId: string }> {
  return postJson(`/schedules/${encodeURIComponent(scheduleId)}/run`, {});
}

export async function listReports(opts?: { scheduleId?: string; limit?: number }): Promise<Report[]> {
  const p = new URLSearchParams();
  if (opts?.scheduleId) p.set("scheduleId", opts.scheduleId);
  if (opts?.limit) p.set("limit", String(opts.limit));
  const q = p.toString();
  return getJson<Report[]>(`/reports${q ? `?${q}` : ""}`);
}

export async function getReport(reportId: string): Promise<Report> {
  return getJson<Report>(`/reports/${encodeURIComponent(reportId)}`);
}

export async function deleteReport(reportId: string): Promise<{ deleted: boolean; reportId: string }> {
  return delJson<{ deleted: boolean; reportId: string }>(`/reports/${encodeURIComponent(reportId)}`);
}

export async function deleteSchedule(scheduleId: string): Promise<{ deleted: boolean; scheduleId: string }> {
  return delJson<{ deleted: boolean; scheduleId: string }>(`/schedules/${encodeURIComponent(scheduleId)}`);
}

export async function runOnce(input: {
  prompt: string;
  symbols?: string[];
  emailTo?: string[];
  attachPdf?: boolean;
  deepResearch?: boolean;
}): Promise<{ instanceId: string; runId: string; message: string }> {
  return postJson("/run-once", {
    prompt: input.prompt,
    symbols: input.symbols ?? [],
    emailTo: input.emailTo ?? [],
    attachPdf: input.attachPdf ?? false,
    deepResearch: input.deepResearch ?? false
  });
}

/* ── Tracked Stocks (Performance Dashboard) ─────────────────────────────── */

export type TrackedStock = {
  id: string;
  userId: string;
  symbol: string;
  reportTitle?: string | null;
  reportId?: string | null;
  recommendationDate: string;
  recommendationPrice: number;
  createdAt?: string | null;
};

export async function listTrackedStocks(limit = 100): Promise<TrackedStock[]> {
  return getJson<TrackedStock[]>(`/tracked-stocks?limit=${encodeURIComponent(String(limit))}`);
}

export async function createTrackedStock(input: {
  symbol: string;
  reportTitle?: string;
  reportId?: string;
  recommendationDate: string;
  recommendationPrice: number;
}): Promise<TrackedStock> {
  return postJson<TrackedStock>("/tracked-stocks", input);
}

export async function deleteTrackedStock(stockId: string): Promise<{ deleted: boolean; stockId: string }> {
  return delJson<{ deleted: boolean; stockId: string }>(`/tracked-stocks/${encodeURIComponent(stockId)}`);
}

export async function fetchStockPrices(symbols: string[]): Promise<Record<string, number | null>> {
  if (!symbols.length) return {};
  const res = await getJson<{ prices: Record<string, number | null> }>(
    `/tracked-stocks/prices?symbols=${encodeURIComponent(symbols.join(","))}`
  );
  return res.prices;
}
