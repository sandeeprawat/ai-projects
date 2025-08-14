import React, { useEffect, useState } from "react";
import { getJson, postJson } from "./api";

type Report = {
  id: string;
  title: string;
  createdAt?: string;
  scheduleId?: string;
};

type ReportDetails = Report & {
  signedUrls?: { md?: string | null; html?: string | null; pdf?: string | null };
};

const App: React.FC = () => {
  // Schedule form state
  const [symbols, setSymbols] = useState("AAPL, MSFT");
  const [recurrenceType, setRecurrenceType] = useState<"daily" | "weekly" | "hours">("daily");
  const [hour, setHour] = useState<number>(14);
  const [dow, setDow] = useState<number>(1);
  const [interval, setInterval] = useState<number>(24);
  const [emailTo, setEmailTo] = useState("");
  const [attachPdf, setAttachPdf] = useState(true);

  const [lastScheduleId, setLastScheduleId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("");

  // Reports
  const [reports, setReports] = useState<Report[]>([]);
  const [selected, setSelected] = useState<ReportDetails | null>(null);
  const [loadingReports, setLoadingReports] = useState(false);

  const createSchedule = async () => {
    setStatus("Creating schedule...");
    try {
      const body: any = {
        symbols: symbols.split(",").map((s) => s.trim()).filter(Boolean),
        recurrence:
          recurrenceType === "daily"
            ? { type: "daily", hour }
            : recurrenceType === "weekly"
            ? { type: "weekly", dow, hour }
            : { type: "hours", interval },
        email: {
          to: emailTo.split(",").map((e) => e.trim()).filter(Boolean),
          attachPdf,
        },
        active: true,
      };
      const resp = await postJson("/api/schedules", body);
      setLastScheduleId(resp.id);
      setStatus(`Schedule created: ${resp.id}`);
    } catch (e: any) {
      setStatus(`Error creating schedule: ${e?.message || String(e)}`);
    }
  };

  const runNow = async () => {
    if (!lastScheduleId) return;
    setStatus("Starting run...");
    try {
      const resp = await postJson(`/api/schedules/${lastScheduleId}/run`, {});
      setStatus(`Run started. instanceId=${resp.instanceId}, runId=${resp.runId}`);
    } catch (e: any) {
      setStatus(`Error starting run: ${e?.message || String(e)}`);
    }
  };

  const refreshReports = async () => {
    setLoadingReports(true);
    setSelected(null);
    try {
      const items = await getJson("/api/reports?limit=20");
      setReports(items || []);
    } catch (e) {
      // ignore
    } finally {
      setLoadingReports(false);
    }
  };

  const openReport = async (id: string) => {
    try {
      const doc = await getJson(`/api/reports/${id}`);
      setSelected(doc);
    } catch (e) {
      setSelected(null);
    }
  };

  useEffect(() => {
    refreshReports();
  }, []);

  return (
    <div style={{ fontFamily: "Inter, system-ui, Arial", maxWidth: 960, margin: "0 auto", padding: 24 }}>
      <h1>Stock Research</h1>

      <section style={{ border: "1px solid #ddd", padding: 16, borderRadius: 8, marginBottom: 24 }}>
        <h2>Create Schedule</h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <label>
            <div>Symbols (comma separated)</div>
            <input value={symbols} onChange={(e) => setSymbols(e.target.value)} placeholder="AAPL, MSFT" style={{ width: "100%" }} />
          </label>

          <label>
            <div>Recurrence Type</div>
            <select value={recurrenceType} onChange={(e) => setRecurrenceType(e.target.value as any)} style={{ width: "100%" }}>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="hours">Every N hours</option>
            </select>
          </label>

          {recurrenceType !== "hours" && (
            <label>
              <div>Hour (UTC 0-23)</div>
              <input type="number" min={0} max={23} value={hour} onChange={(e) => setHour(Number(e.target.value))} style={{ width: "100%" }} />
            </label>
          )}

          {recurrenceType === "weekly" && (
            <label>
              <div>Day of week (Mon=0..Sun=6)</div>
              <input type="number" min={0} max={6} value={dow} onChange={(e) => setDow(Number(e.target.value))} style={{ width: "100%" }} />
            </label>
          )}

          {recurrenceType === "hours" && (
            <label>
              <div>Interval (hours)</div>
              <input type="number" min={1} value={interval} onChange={(e) => setInterval(Number(e.target.value))} style={{ width: "100%" }} />
            </label>
          )}

          <label>
            <div>Email recipients (comma separated)</div>
            <input value={emailTo} onChange={(e) => setEmailTo(e.target.value)} placeholder="you@example.com" style={{ width: "100%" }} />
          </label>

          <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={attachPdf} onChange={(e) => setAttachPdf(e.target.checked)} />
            Attach PDF
          </label>
        </div>

        <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
          <button onClick={createSchedule}>Create</button>
          <button onClick={runNow} disabled={!lastScheduleId}>Run Now</button>
          <span style={{ color: "#666" }}>{status}</span>
        </div>
      </section>

      <section style={{ border: "1px solid #ddd", padding: 16, borderRadius: 8 }}>
        <h2>Reports</h2>
        <div style={{ marginBottom: 8 }}>
          <button onClick={refreshReports} disabled={loadingReports}>{loadingReports ? "Loading..." : "Refresh"}</button>
        </div>
        {reports.length === 0 ? (
          <div>No reports yet.</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: 6 }}>Title</th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: 6 }}>Created</th>
                <th style={{ borderBottom: "1px solid #ccc", padding: 6 }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.id}>
                  <td style={{ borderBottom: "1px solid #eee", padding: 6 }}>{r.title}</td>
                  <td style={{ borderBottom: "1px solid #eee", padding: 6 }}>{r.createdAt || ""}</td>
                  <td style={{ borderBottom: "1px solid #eee", padding: 6 }}>
                    <button onClick={() => openReport(r.id)}>Open</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {selected && (
          <div style={{ marginTop: 12, padding: 12, background: "#fafafa", border: "1px solid #eee", borderRadius: 6 }}>
            <h3 style={{ marginTop: 0 }}>{selected.title}</h3>
            <div style={{ display: "flex", gap: 12 }}>
              {selected.signedUrls?.html && (
                <a href={selected.signedUrls.html} target="_blank" rel="noreferrer">Open HTML</a>
              )}
              {selected.signedUrls?.md && (
                <a href={selected.signedUrls.md} target="_blank" rel="noreferrer">Download MD</a>
              )}
              {selected.signedUrls?.pdf && (
                <a href={selected.signedUrls.pdf} target="_blank" rel="noreferrer">Download PDF</a>
              )}
            </div>
          </div>
        )}
      </section>
    </div>
  );
};

export default App;
