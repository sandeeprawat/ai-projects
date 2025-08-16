import {
  listSchedules,
  createSchedule,
  updateSchedule,
  deleteSchedule,
  runScheduleNow,
  listReports,
  getReport,
  type Schedule,
  type Recurrence,
  type EmailSettings,
  type Report
} from "../api";

export function renderSchedules(root: HTMLElement) {
  root.innerHTML = "";

  // State
  let schedules: Schedule[] = [];
  let editingId: string | null = null;
  const reportsCache = new Map<string, Report[]>(); // scheduleId -> reports

  // Helpers
  function escapeHtml(s: unknown) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
  function fmtDate(s?: string | null) {
    if (!s) return "";
    try {
      const d = new Date(s);
      return d.toLocaleString();
    } catch {
      return s || "";
    }
  }
  function parseEmails(s: string): string[] {
    return (s || "")
      .split(/[,\s;]/g)
      .map((x) => x.trim())
      .filter((x) => x.length > 0);
  }

  // Layout
  const page = document.createElement("div");
  page.className = "page schedules-page";

  const header = document.createElement("div");
  header.className = "page-header";
  header.innerHTML = `
    <h2>Schedules</h2>
    <div class="actions">
      <button id="refreshBtn">Refresh</button>
    </div>
  `;
  page.appendChild(header);

  const status = document.createElement("div");
  status.className = "status";
  page.appendChild(status);

  const grid = document.createElement("div");
  grid.className = "grid";

  // Form card
  const formCard = document.createElement("div");
  formCard.className = "card row";
  formCard.innerHTML = `
    <h3 style="margin-top:0;" id="formTitle">Create Schedule</h3>
    <div class="grid">
      <div class="col-12">
        <label for="prompt">Research Prompt</label>
        <textarea id="prompt" placeholder="e.g., Provide a weekly research brief covering recent developments, earnings, and risks."></textarea>
      </div>
      <div class="col-12">
        <label for="symbols">Symbols (comma separated)</label>
        <input id="symbols" type="text" placeholder="AAPL, MSFT, GOOGL" />
      </div>

      <div class="col-4">
        <label for="cadence">Frequency</label>
        <select id="cadence">
          <option value="hourly">Hourly</option>
          <option value="daily">Daily</option>
          <option value="weekly" selected>Weekly</option>
        </select>
      </div>

      <!-- Single row for all time variables as requested -->
      <div class="col-12">
        <div class="grid">
          <div class="col-3">
            <label for="interval">Interval</label>
            <input id="interval" type="number" min="1" value="1" />
          </div>
          <div class="col-3">
            <label for="hour">Hour (0-23)</label>
            <input id="hour" type="number" min="0" max="23" placeholder="e.g., 9" />
          </div>
          <div class="col-3">
            <label for="minute">Minute (0-59)</label>
            <input id="minute" type="number" min="0" max="59" placeholder="e.g., 0" />
          </div>
          <div class="col-3">
            <label for="weekday">Weekday (Mon=0..Sun=6)</label>
            <select id="weekday">
              <option value="">—</option>
              <option value="0">Mon</option>
              <option value="1">Tue</option>
              <option value="2">Wed</option>
              <option value="3">Thu</option>
              <option value="4">Fri</option>
              <option value="5">Sat</option>
              <option value="6">Sun</option>
            </select>
          </div>
        </div>
      </div>

      <div class="col-8">
        <label for="emailTo">Email recipients (comma separated)</label>
        <input id="emailTo" type="text" placeholder="me@example.com, team@example.com" />
      </div>
      <div class="col-4" style="display:flex;align-items:flex-end;gap:12px;">
        <label style="display:flex;align-items:center;gap:8px;margin:0;">
          <input id="attachPdf" type="checkbox" /> Attach PDF
        </label>
        <label style="display:flex;align-items:center;gap:8px;margin:0;">
          <input id="active" type="checkbox" checked /> Active
        </label>
      </div>

      <div class="col-12" style="display:flex; gap:8px; margin-top:8px;">
        <button id="createBtn" class="primary">Create</button>
        <button id="updateBtn" class="primary" style="display:none;">Save</button>
        <button id="cancelEditBtn" class="secondary" style="display:none;">Cancel</button>
        <button id="resetBtn" class="secondary">Reset</button>
      </div>
    </div>
  `;
  grid.appendChild(formCard);

  // Table card
  const tableCard = document.createElement("div");
  tableCard.className = "card row";
  tableCard.innerHTML = `
    <div class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>Prompt</th>
            <th>Symbols</th>
            <th>Cadence</th>
            <th>Next Run</th>
            <th style="width:380px;">Actions</th>
          </tr>
        </thead>
        <tbody id="schedulesTbody">
          <tr><td colspan="5">Loading…</td></tr>
        </tbody>
      </table>
    </div>
  `;
  grid.appendChild(tableCard);

  page.appendChild(grid);
  root.appendChild(page);

  // Query elements
  const refreshBtn = header.querySelector<HTMLButtonElement>("#refreshBtn")!;
  const tbody = tableCard.querySelector<HTMLTableSectionElement>("#schedulesTbody")!;
  const formTitle = formCard.querySelector<HTMLElement>("#formTitle")!;
  const createBtn = formCard.querySelector<HTMLButtonElement>("#createBtn")!;
  const updateBtn = formCard.querySelector<HTMLButtonElement>("#updateBtn")!;
  const cancelEditBtn = formCard.querySelector<HTMLButtonElement>("#cancelEditBtn")!;
  const resetBtn = formCard.querySelector<HTMLButtonElement>("#resetBtn")!;

  const promptEl = formCard.querySelector<HTMLTextAreaElement>("#prompt")!;
  const symbolsEl = formCard.querySelector<HTMLInputElement>("#symbols")!;
  const cadenceEl = formCard.querySelector<HTMLSelectElement>("#cadence")!;
  const intervalEl = formCard.querySelector<HTMLInputElement>("#interval")!;
  const hourEl = formCard.querySelector<HTMLInputElement>("#hour")!;
  const minuteEl = formCard.querySelector<HTMLInputElement>("#minute")!;
  const weekdayEl = formCard.querySelector<HTMLSelectElement>("#weekday")!;
  const emailToEl = formCard.querySelector<HTMLInputElement>("#emailTo")!;
  const attachPdfEl = formCard.querySelector<HTMLInputElement>("#attachPdf")!;
  const activeEl = formCard.querySelector<HTMLInputElement>("#active")!;

  function setStatus(text: string, kind: "info" | "success" | "error" = "info") {
    status.textContent = text || "";
    status.className = `status ${kind}`;
  }

  function resetForm() {
    // Weekly default as requested
    formTitle.textContent = "Create Schedule";
    editingId = null;
    promptEl.value = "";
    symbolsEl.value = "";
    cadenceEl.value = "weekly";
    intervalEl.value = "1";
    hourEl.value = "";
    minuteEl.value = "";
    weekdayEl.value = "";
    emailToEl.value = "";
    attachPdfEl.checked = false;
    activeEl.checked = true;
    createBtn.style.display = "";
    updateBtn.style.display = "none";
    cancelEditBtn.style.display = "none";
    setStatus("");
  }

  function readForm(): {
    prompt: string;
    symbols: string[];
    recurrence: Recurrence;
    email: EmailSettings;
    active: boolean;
  } {
    const cadence = (cadenceEl.value || "weekly") as Recurrence["cadence"];
    const interval = Math.max(1, Number(intervalEl.value || 1));
    const hour = hourEl.value === "" ? null : clampNum(Number(hourEl.value), 0, 23);
    const minute = minuteEl.value === "" ? null : clampNum(Number(minuteEl.value), 0, 59);
    const weekday = weekdayEl.value === "" ? null : clampNum(Number(weekdayEl.value), 0, 6);

    const rec: Recurrence = { cadence, interval, hour, minute, weekday };
    const email: EmailSettings = { to: parseEmails(emailToEl.value), attachPdf: !!attachPdfEl.checked };
    const symbols = (symbolsEl.value || "")
      .split(/[,\s]+/g)
      .map((x) => x.trim().toUpperCase())
      .filter((x) => x);

    return {
      prompt: promptEl.value.trim(),
      symbols,
      recurrence: rec,
      email,
      active: !!activeEl.checked
    };
  }

  function clampNum(n: number, min: number, max: number): number {
    if (Number.isNaN(n)) return min;
    return Math.min(max, Math.max(min, Math.floor(n)));
  }

  function populateForm(s: Schedule) {
    formTitle.textContent = "Edit Schedule";
    editingId = s.id || null;

    promptEl.value = s.prompt || "";
    symbolsEl.value = (s.symbols || []).join(", ");
    cadenceEl.value = s.recurrence?.cadence || "weekly";
    intervalEl.value = String(s.recurrence?.interval ?? 1);
    hourEl.value = s.recurrence?.hour !== null && s.recurrence?.hour !== undefined ? String(s.recurrence?.hour) : "";
    minuteEl.value = s.recurrence?.minute !== null && s.recurrence?.minute !== undefined ? String(s.recurrence?.minute) : "";
    weekdayEl.value = s.recurrence?.weekday !== null && s.recurrence?.weekday !== undefined ? String(s.recurrence?.weekday) : "";
    emailToEl.value = (s.email?.to || []).join(", ");
    attachPdfEl.checked = !!s.email?.attachPdf;
    activeEl.checked = !!s.active;

    createBtn.style.display = "none";
    updateBtn.style.display = "";
    cancelEditBtn.style.display = "";
  }

  function renderRows() {
    if (!schedules.length) {
      tbody.innerHTML = `<tr><td colspan="5">No schedules found.</td></tr>`;
      return;
    }
    const rows = schedules
      .map((s) => {
        const sym = (s.symbols || []).join(", ");
        const cad = `${s.recurrence?.cadence || ""} x${s.recurrence?.interval ?? 1}`.trim();
        const nxt = fmtDate(s.nextRunAt);
        const promptShort = (s.prompt || "").slice(0, 80);
        return `
          <tr data-id="${escapeHtml(s.id || "")}">
            <td>
              <div title="${escapeHtml(s.prompt || "")}">${escapeHtml(promptShort)}${(s.prompt || "").length > 80 ? "…" : ""}</div>
            </td>
            <td>${escapeHtml(sym)}</td>
            <td><span class="badge">${escapeHtml(cad)}</span></td>
            <td>${escapeHtml(nxt)}</td>
            <td>
              <button class="runBtn">Run now</button>
              <button class="editBtn">Edit</button>
              <button class="viewReportsBtn">View Reports</button>
              <button class="deleteBtn danger">Delete</button>
            </td>
          </tr>
          <tr class="reportsRow" data-parent="${escapeHtml(s.id || "")}" style="display:none;">
            <td colspan="5">
              <div class="inline-panel">
                <h4>Reports</h4>
                <div class="inline-list" id="repList-${escapeHtml(s.id || "")}">Loading…</div>
              </div>
            </td>
          </tr>
        `;
      })
      .join("");
    tbody.innerHTML = rows;
    wireRowEvents();
  }

  function wireRowEvents() {
    tbody.querySelectorAll<HTMLButtonElement>(".runBtn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const tr = btn.closest("tr") as HTMLTableRowElement | null;
        const id = tr?.getAttribute("data-id") || "";
        if (!id) return;
        btn.disabled = true;
        setStatus("Starting run…", "info");
        try {
          await runScheduleNow(id);
          setStatus("Run started.", "success");
        } catch (e: any) {
          setStatus(`Run failed: ${e?.message ?? String(e)}`, "error");
        } finally {
          btn.disabled = false;
        }
      });
    });

    tbody.querySelectorAll<HTMLButtonElement>(".editBtn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tr = btn.closest("tr") as HTMLTableRowElement | null;
        const id = tr?.getAttribute("data-id") || "";
        if (!id) return;
        const s = schedules.find((x) => x.id === id);
        if (!s) return;
        populateForm(s);
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    });

    tbody.querySelectorAll<HTMLButtonElement>(".deleteBtn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const tr = btn.closest("tr") as HTMLTableRowElement | null;
        const id = tr?.getAttribute("data-id") || "";
        if (!id) return;
        if (!confirm("Delete this schedule and its future runs?")) return;
        btn.disabled = true;
        setStatus("Deleting…", "info");
        try {
          await deleteSchedule(id);
          schedules = schedules.filter((s) => s.id !== id);
          // hide associated reports row
          const rr = tbody.querySelector<HTMLTableRowElement>(`.reportsRow[data-parent="${CSS.escape(id)}"]`);
          rr?.remove();
          renderRows();
          setStatus("Schedule deleted.", "success");
        } catch (e: any) {
          btn.disabled = false;
          setStatus(`Delete failed: ${e?.message ?? String(e)}`, "error");
        }
      });
    });

    tbody.querySelectorAll<HTMLButtonElement>(".viewReportsBtn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const tr = btn.closest("tr") as HTMLTableRowElement | null;
        const id = tr?.getAttribute("data-id") || "";
        if (!id) return;
        const rr = tbody.querySelector<HTMLTableRowElement>(`.reportsRow[data-parent="${CSS.escape(id)}"]`);
        if (!rr) return;
        const panel = rr.querySelector<HTMLElement>(`#repList-${CSS.escape(id)}`)!;
        const visible = rr.style.display !== "none";
        if (visible) {
          rr.style.display = "none";
          return;
        }
        rr.style.display = "";
        // Load if not cached
        try {
          panel.textContent = "Loading…";
          if (!reportsCache.has(id)) {
            const reps = await listReports({ scheduleId: id, limit: 50 });
            reportsCache.set(id, reps);
          }
          renderReportList(id, panel);
        } catch (e: any) {
          panel.textContent = `Failed to load: ${e?.message ?? String(e)}`;
        }
      });
    });
  }

  function renderReportList(scheduleId: string, host: HTMLElement) {
    const reps = reportsCache.get(scheduleId) || [];
    if (!reps.length) {
      host.textContent = "No reports yet.";
      return;
    }
    const items = reps
      .map((r) => {
        const created = fmtDate(r.createdAt);
        const title = r.title || r.id;
        return `
          <div class="inline-item" data-rid="${escapeHtml(r.id)}">
            <div>
              <div style="font-weight:600;">${escapeHtml(title)}</div>
              <div style="font-size:12px;color:#9ca3af;">${escapeHtml(created)}</div>
            </div>
            <div style="display:flex;gap:6px;">
              <button class="viewBtn">View</button>
              <button class="dlBtn" data-kind="pdf" title="Download PDF">PDF</button>
              <button class="dlBtn secondary" data-kind="html" title="Download HTML">HTML</button>
              <button class="dlBtn secondary" data-kind="md" title="Download Markdown">MD</button>
            </div>
          </div>
        `;
      })
      .join("");
    host.innerHTML = items;

    // Wire view/download for inline list
    host.querySelectorAll<HTMLButtonElement>(".viewBtn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const item = btn.closest(".inline-item") as HTMLElement | null;
        const rid = item?.getAttribute("data-rid") || "";
        if (!rid) return;
        setStatus("Fetching report link…", "info");
        try {
          const urls = await ensureSignedUrls(scheduleId, rid);
          const url = urls?.html || urls?.pdf || urls?.md;
          if (url) {
            window.open(url, "_blank");
            setStatus("");
          } else {
            setStatus("No viewable assets for this report.", "error");
          }
        } catch (e: any) {
          setStatus(`Open failed: ${e?.message ?? String(e)}`, "error");
        }
      });
    });
    host.querySelectorAll<HTMLButtonElement>(".dlBtn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const item = btn.closest(".inline-item") as HTMLElement | null;
        const rid = item?.getAttribute("data-rid") || "";
        const kind = (btn.getAttribute("data-kind") as "pdf" | "html" | "md" | null) || null;
        if (!rid || !kind) return;
        setStatus(`Preparing ${kind.toUpperCase()} download…`, "info");
        try {
          const urls = await ensureSignedUrls(scheduleId, rid);
          const url = (urls && (urls as any)[kind]) as string | undefined;
          if (url) {
            const a = document.createElement("a");
            a.href = url;
            a.download = "";
            a.rel = "noopener";
            document.body.appendChild(a);
            a.click();
            a.remove();
            setStatus("Download started.", "success");
          } else {
            setStatus(`No ${kind.toUpperCase()} available for this report.`, "error");
          }
        } catch (e: any) {
          setStatus(`Download failed: ${e?.message ?? String(e)}`, "error");
        }
      });
    });
  }

  async function ensureSignedUrls(scheduleId: string, reportId: string): Promise<Report["signedUrls"] | null> {
    const list = reportsCache.get(scheduleId) || [];
    const cur = list.find((r) => r.id === reportId);
    if (cur?.signedUrls && (cur.signedUrls.html || cur.signedUrls.pdf || cur.signedUrls.md)) {
      return cur.signedUrls;
    }
    try {
      const full = await getReport(reportId);
      const idx = list.findIndex((r) => r.id === reportId);
      if (idx >= 0) {
        list[idx] = { ...list[idx], ...full };
        reportsCache.set(scheduleId, list);
      }
      return full.signedUrls || null;
    } catch {
      return null;
    }
  }

  // Events
  refreshBtn.addEventListener("click", () => load());

  createBtn.addEventListener("click", async () => {
    const input = readForm();
    if (!input.prompt) {
      setStatus("Prompt is required.", "error");
      return;
    }
    createBtn.disabled = true;
    setStatus("Creating schedule…", "info");
    try {
      await createSchedule(input);
      setStatus("Schedule created.", "success");
      resetForm();
      await load();
    } catch (e: any) {
      setStatus(`Create failed: ${e?.message ?? String(e)}`, "error");
    } finally {
      createBtn.disabled = false;
    }
  });

  updateBtn.addEventListener("click", async () => {
    if (!editingId) return;
    const input = readForm();
    if (!input.prompt) {
      setStatus("Prompt is required.", "error");
      return;
    }
    updateBtn.disabled = true;
    setStatus("Saving changes…", "info");
    try {
      await updateSchedule(editingId, input);
      setStatus("Schedule updated.", "success");
      resetForm();
      await load();
    } catch (e: any) {
      setStatus(`Update failed: ${e?.message ?? String(e)}`, "error");
    } finally {
      updateBtn.disabled = false;
    }
  });

  cancelEditBtn.addEventListener("click", () => {
    resetForm();
  });

  resetBtn.addEventListener("click", () => {
    resetForm();
  });

  // Initial
  resetForm();
  load();

  async function load() {
    try {
      setStatus("Loading…", "info");
      schedules = await listSchedules(200);
      renderRows();
      setStatus("");
    } catch (e: any) {
      tbody.innerHTML = `<tr><td colspan="5">Failed to load: ${escapeHtml(e?.message ?? String(e))}</td></tr>`;
      setStatus("Failed to load schedules.", "error");
    }
  }
}
