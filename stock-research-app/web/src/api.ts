import { getToken } from "./auth";

export async function getJson<T = any>(path: string): Promise<T> {
  const url = path.startsWith("http") ? path : `/api${path.startsWith("/") ? path : `/${path}`}`;
  const t = getToken();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (t) headers["Authorization"] = `Bearer ${t}`;

  const res = await fetch(url, {
    method: "GET",
    headers,
    credentials: "include"
  });
  if (!res.ok) throw new Error(`GET ${url} failed: ${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export async function postJson<T = any>(path: string, body: any): Promise<T> {
  const url = path.startsWith("http") ? path : `/api${path.startsWith("/") ? path : `/${path}`}`;
  const t = getToken();
  const headers: Record<string, string> = { Accept: "application/json", "Content-Type": "application/json" };
  if (t) headers["Authorization"] = `Bearer ${t}`;

  const res = await fetch(url, {
    method: "POST",
    headers,
    credentials: "include",
    body: JSON.stringify(body ?? {})
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`POST ${url} failed: ${res.status} ${res.statusText} ${text}`);
  }
  return (await res.json()) as T;
}

export async function delJson<T = any>(path: string): Promise<T> {
  const url = path.startsWith("http") ? path : `/api${path.startsWith("/") ? path : `/${path}`}`;
  const t = getToken();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (t) headers["Authorization"] = `Bearer ${t}`;

  const res = await fetch(url, {
    method: "DELETE",
    headers,
    credentials: "include"
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
  active?: boolean;
}): Promise<Schedule> {
  return postJson<Schedule>("/schedules", {
    prompt: input.prompt,
    symbols: input.symbols ?? [],
    recurrence: input.recurrence,
    email: input.email,
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
