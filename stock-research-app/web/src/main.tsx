import React from "react";
import { createRoot } from "react-dom/client";

/* Minimal hash router to avoid extra deps */
type Route = { path: RegExp; render: (params: Record<string, string>) => JSX.Element };

function useHashLocation() {
  const [hash, setHash] = React.useState(window.location.hash || "#/schedules");
  React.useEffect(() => {
    const onHashChange = () => setHash(window.location.hash || "#/schedules");
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  return hash.startsWith("#") ? hash.slice(1) : hash;
}

function Link(props: { to: string; children: React.ReactNode }) {
  return (
    <a href={`#${props.to}`} style={{ textDecoration: "none", color: "#2563eb" }}>
      {props.children}
    </a>
  );
}

/* API wrappers */
import {
  listSchedules,
  createSchedule,
  runScheduleNow,
  listReports,
  getReport,
  type Schedule,
  type Recurrence,
  type EmailSettings,
  type Report
} from "./api";
import { initGoogle, getUser as getGoogleUser, clearToken } from "./auth";
import "./styles.css";

/* Pages */
function SchedulesPage() {
  const [items, setItems] = React.useState<Schedule[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // form state
  const [prompt, setPrompt] = React.useState("Research the latest developments and outlook for AAPL and MSFT.");
  const [symbols, setSymbols] = React.useState("");
  const [cadence, setCadence] = React.useState<"hourly" | "daily" | "weekly">("daily");
  const [interval, setInterval] = React.useState(1);
  const [hour, setHour] = React.useState(9);
  const [minute, setMinute] = React.useState(0);
  const [weekday, setWeekday] = React.useState(0);
  const [emailTo, setEmailTo] = React.useState("");
  const [attachPdf, setAttachPdf] = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await listSchedules(100);
      setItems(rows);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => { void load(); }, [load]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!prompt.trim()) {
      setError("Prompt is required");
      return;
    }
    try {
      const rec: Recurrence = { cadence, interval, hour, minute, weekday };
      const email: EmailSettings = {
        to: emailTo.split(",").map(s => s.trim()).filter(Boolean),
        attachPdf
      };
      await createSchedule({
        prompt: prompt.trim(),
        symbols: symbols.split(",").map(s => s.trim().toUpperCase()).filter(Boolean),
        recurrence: rec,
        email,
        active: true
      });
      setPrompt("");
      setSymbols("");
      await load();
      alert("Schedule created");
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  async function onRunNow(id: string) {
    try {
      await runScheduleNow(id);
      alert("Run started");
    } catch (e: any) {
      alert(e?.message || String(e));
    }
  }

  return (
    <div className="page">
      <h2>Schedules</h2>
      {error && <div style={{ color: "crimson", marginBottom: 12 }}>{error}</div>}

      <form onSubmit={onCreate} className="card" style={{ display: "grid", gap: 8, maxWidth: 720, marginBottom: 24 }}>
        <label>
          Research prompt (required)
          <textarea value={prompt} onChange={e => setPrompt(e.target.value)} rows={5} style={{ width: "100%" }} />
        </label>
        <label>
          Symbols (optional, comma-separated)
          <input value={symbols} onChange={e => setSymbols(e.target.value)} style={{ width: "100%" }} />
        </label>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <label>Cadence
            <select value={cadence} onChange={e => setCadence(e.target.value as any)}>
              <option value="hourly">hourly</option>
              <option value="daily">daily</option>
              <option value="weekly">weekly</option>
            </select>
          </label>
          <label>Interval
            <input type="number" min={1} value={interval} onChange={e => setInterval(Number(e.target.value || 1))} style={{ width: 80 }} />
          </label>
          {cadence !== "hourly" && (
            <>
              <label>Hour
                <input type="number" min={0} max={23} value={hour} onChange={e => setHour(Number(e.target.value || 0))} style={{ width: 80 }} />
              </label>
              <label>Minute
                <input type="number" min={0} max={59} value={minute} onChange={e => setMinute(Number(e.target.value || 0))} style={{ width: 80 }} />
              </label>
            </>
          )}
          {cadence === "weekly" && (
            <label>Weekday
              <select value={weekday} onChange={e => setWeekday(Number(e.target.value || 0))}>
                <option value={0}>Mon</option>
                <option value={1}>Tue</option>
                <option value={2}>Wed</option>
                <option value={3}>Thu</option>
                <option value={4}>Fri</option>
                <option value={5}>Sat</option>
                <option value={6}>Sun</option>
              </select>
            </label>
          )}
        </div>

        <label>
          Email to (comma-separated)
          <input value={emailTo} onChange={e => setEmailTo(e.target.value)} style={{ width: "100%" }} />
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input type="checkbox" checked={attachPdf} onChange={e => setAttachPdf(e.target.checked)} />
          Attach PDF
        </label>

        <button type="submit" disabled={loading}>Create schedule</button>
      </form>

      <div>
        {loading ? <div>Loading...</div> : null}
        <table>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>Prompt / Symbols</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>Cadence</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>Next Run (UTC)</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map(s => (
              <tr key={s.id}>
                <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{s.prompt ? s.prompt.slice(0, 80) : s.symbols?.join(", ")}</td>
                <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{s.recurrence?.cadence} / {s.recurrence?.interval}</td>
                <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{s.nextRunAt || "-"}</td>
                <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                  {s.id && <button onClick={() => onRunNow(s.id!)}>Run Now</button>}{" "}
                  {s.id && <Link to={`/reports?scheduleId=${encodeURIComponent(s.id)}`}>View Reports</Link>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ReportsPage() {
  const [items, setItems] = React.useState<Report[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // read scheduleId from hash query
  const hash = useHashLocation();
  const url = new URL(hash.startsWith("/") ? hash : `/${hash}`, "http://local/");
  const scheduleId = url.searchParams.get("scheduleId") || undefined;

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await listReports({ scheduleId, limit: 100 });
      setItems(rows);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }, [scheduleId]);

  React.useEffect(() => { void load(); }, [load]);

  return (
    <div className="page">
      <h2>Reports {scheduleId ? `(Schedule ${scheduleId})` : ""}</h2>
      {error && <div style={{ color: "crimson", marginBottom: 12 }}>{error}</div>}
      {loading ? <div>Loading...</div> : null}
      <table>
        <thead>
          <tr>
            <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>Title</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>Symbols</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>Created</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>Open</th>
          </tr>
        </thead>
        <tbody>
          {items.map(r => (
            <tr key={r.id}>
              <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{r.title}</td>
              <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{r.symbols?.join(", ")}</td>
              <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{r.createdAt || "-"}</td>
              <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                <Link to={`/report/${encodeURIComponent(r.id)}`}>View</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ReportDetailPage(props: { reportId: string }) {
  const [report, setReport] = React.useState<Report | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const r = await getReport(props.reportId);
        setReport(r);
      } catch (e: any) {
        setError(e?.message || String(e));
      } finally {
        setLoading(false);
      }
    })();
  }, [props.reportId]);

  return (
    <div className="page">
      <h2>{report?.title || "Report"}</h2>
      {error && <div style={{ color: "crimson", marginBottom: 12 }}>{error}</div>}
      {loading ? <div>Loading...</div> : null}

      {report && (
        <div style={{ display: "grid", gap: 8 }}>
          <div>Symbols: {report.symbols?.join(", ") || "-" }</div>
          <div>Created: {report.createdAt || "-" }</div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {report.signedUrls?.html && (
              <a href={report.signedUrls.html} target="_blank" rel="noreferrer">Open HTML</a>
            )}
            {report.signedUrls?.md && (
              <a href={report.signedUrls.md} target="_blank" rel="noreferrer">Open Markdown</a>
            )}
            {report.signedUrls?.pdf && (
              <a href={report.signedUrls.pdf} target="_blank" rel="noreferrer">Download PDF</a>
            )}
          </div>
          {Array.isArray(report.citations) && report.citations.length > 0 && (
            <div>
              <h3>Citations</h3>
              <ul>
                {report.citations.map((c, i) => (
                  <li key={`${i}-${c.url}`}>{c.title || c.url} - <a href={c.url} target="_blank" rel="noreferrer">{c.url}</a></li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* App shell + router */
function App() {
  const [user, setUser] = React.useState(() => getGoogleUser());
  const loginRef = React.useRef<HTMLDivElement | null>(null);
  React.useEffect(() => { initGoogle(() => { setUser(getGoogleUser()); }, loginRef.current); }, []);
  const onLogout = () => { clearToken(); setUser(null); };
  React.useEffect(() => {
    const onAuthChanged = () => setUser(getGoogleUser());
    const onStorage = (e: StorageEvent) => { if (e.key === "google_id_token") onAuthChanged(); };
    window.addEventListener("auth:changed", onAuthChanged as any);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener("auth:changed", onAuthChanged as any);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  // Auth gate: block the UI for unauthenticated users
  if (!user) {
    return (
      <div className="auth-shell">
        <header className="app-header">
          <strong>Stock Research</strong>
          <div ref={loginRef}></div>
        </header>
        <div className="login-panel">
          <div className="login-card">
            <h1>Welcome</h1>
            <p className="muted">Sign in with Google to continue.</p>
            <div className="muted">Use the button in the header.</div>
          </div>
        </div>
      </div>
    );
  }

  const hash = useHashLocation();
  const path = hash || "/schedules";

  const routes: Route[] = [
    { path: /^\/schedules$/, render: () => <SchedulesPage /> },
    { path: /^\/reports(?:\?.*)?$/, render: () => <ReportsPage /> },
    { path: /^\/report\/(?<id>[^/]+)$/, render: ({ id }) => <ReportDetailPage reportId={decodeURIComponent(id)} /> }
  ];

  let matched: JSX.Element = <SchedulesPage />;
  for (const r of routes) {
    const m = path.match(r.path);
    if (m) {
      const params = (m.groups || {}) as Record<string, string>;
      matched = r.render(params);
      break;
    }
  }

  return (
    <div style={{ fontFamily: "system-ui, Segoe UI, Roboto, Arial, sans-serif" }}>
      <header className="app-header">
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <strong>Stock Research</strong>
          <nav style={{ display: "flex", gap: 12 }}>
            <Link to="/schedules">Schedules</Link>
            <Link to="/reports">Reports</Link>
          </nav>
        </div>
        <div>
          {user ? (
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <span style={{ opacity: 0.8 }}>Signed in as {user.name}</span>
              <button onClick={onLogout}>Logout</button>
            </div>
          ) : (
            <div ref={loginRef}></div>
          )}
        </div>
      </header>
      <main>{matched}</main>
    </div>
  );
}

const rootEl = document.getElementById("root")!;
createRoot(rootEl).render(<App />);
