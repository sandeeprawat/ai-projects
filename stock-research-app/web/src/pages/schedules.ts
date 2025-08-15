import {
  listSchedules,
  createSchedule,
  runScheduleNow,
  deleteSchedule,
  type Schedule,
  type Recurrence,
  type EmailSettings
} from "../api";

export function renderSchedules(root: HTMLElement) {
  root.innerHTML = "";
  const container = document.createElement("div");
  container.className = "page schedules-page";

  const header = document.createElement("div");
  header.className = "page-header";
  header.innerHTML = `
    <h2>Schedules</h2>
    <div class="actions">
      <button id="refreshBtn">Refresh</button>
    </div>
  `;
  container.appendChild(header);

  const status = document.createElement("div");
  status.className = "status";
  container.appendChild(status);

  const formWrap = document.createElement("div");
  formWrap.className = "form-wrap";
  formWrap.innerHTML = `
    <section class="card">
      <h3>Create Schedule</h3>
      <div class="grid">
        <label>
          <div>Prompt</div>
          <textarea id="prompt" rows="3" placeholder="What to research..."></textarea>
        </label>
        <label>
          <div>Symbols (comma separated)</div>
          <input id="symbols" type="text" placeholder="AAPL, MSFT" />
        </label>

        <label>
          <div>Cadence</div>
          <select id="cadence">
            <option value="hourly">Hourly</option>
            <option value="daily" selected>Daily</option>
            <option value="weekly">Weekly</option>
          </select>
        </label>
        <label>
          <div>Interval</div>
          <input id="interval" type="number" min="1" value="1" />
        </label>

        <div id="timeFields" class="time-fields">
          <label>
            <div>Hour (0-23)</div>
            <input id="hour" type="number" min="0" max="23" value="9" />
          </label>
          <label>
            <div>Minute (0-59)</div>
            <input id="minute" type="number" min="0" max="59" value="0" />
          </label>
        </div>

        <div id="weekdayField" class="weekday-field" style="display:none;">
          <label>
            <div>Weekday</div>
            <select id="weekday">
              <option value="0">Mon</option>
              <option value="1">Tue</option>
              <option value="2">Wed</option>
              <option value="3">Thu</option>
              <option value="4">Fri</option>
              <option value="5">Sat</option>
              <option value="6">Sun</option>
            </select>
          </label>
        </div>

        <label>
          <div>Email To (comma separated)</div>
          <input id="emailTo" type="text" placeholder="user@example.com, team@example.com" />
        </label>
        <label class="checkbox">
          <input id="attachPdf" type="checkbox" />
          <span>Attach PDF</span>
        </label>
        <label class="checkbox">
          <input id="active" type="checkbox" checked />
          <span>Active</span>
        </label>
      </div>

      <div class="actions">
        <button id="createBtn">Create</button>
        <button id="createRunNowBtn">Create + Run Now</button>
        <button id="resetBtn" class="secondary">Reset</button>
      </div>
    </section>
  `;
  container.appendChild(formWrap);

  const tableWrap = document.createElement("div");
  tableWrap.className = "table-wrap";
  tableWrap.innerHTML = `
    <section class="card">
      <div class="table-header">
        <h3>Existing Schedules</h3>
      </div>
      <table class="table">
        <thead>
          <tr>
            <th>Prompt</th>
            <th>Symbols</th>
            <th>Cadence</th>
            <th>Next Run</th>
            <th>Active</th>
            <th style="width:200px;">Actions</th>
          </tr>
        </thead>
        <tbody id="schedulesTbody">
          <tr><td colspan="6">Loading…</td></tr>
        </tbody>
      </table>
    </section>
  `;
  container.appendChild(tableWrap);

  root.appendChild(container);

  // Elements
  const refreshBtn = header.querySelector<HTMLButtonElement>("#refreshBtn")!;
  const tbody = tableWrap.querySelector<HTMLTableSectionElement>("#schedulesTbody")!;
  const promptEl = formWrap.querySelector<HTMLTextAreaElement>("#prompt")!;
  const symbolsEl = formWrap.querySelector<HTMLInputElement>("#symbols")!;
  const cadenceEl = formWrap.querySelector<HTMLSelectElement>("#cadence")!;
  const intervalEl = formWrap.querySelector<HTMLInputElement>("#interval")!;
  const hourEl = formWrap.querySelector<HTMLInputElement>("#hour")!;
  const minuteEl = formWrap.querySelector<HTMLInputElement>("#minute")!;
  const weekdayEl = formWrap.querySelector<HTMLSelectElement>("#weekday")!;
  const timeFields = formWrap.querySelector<HTMLDivElement>("#timeFields")!;
  const weekdayField = formWrap.querySelector<HTMLDivElement>("#weekdayField")!;
  const emailToEl = formWrap.querySelector<HTMLInputElement>("#emailTo")!;
  const attachPdfEl = formWrap.querySelector<HTMLInputElement>("#attachPdf")!;
  const activeEl = formWrap.querySelector<HTMLInputElement>("#active")!;
  const createBtn = formWrap.querySelector<HTMLButtonElement>("#createBtn")!;
  const createRunNowBtn = formWrap.querySelector<HTMLButtonElement>("#createRunNowBtn")!;
  const resetBtn = formWrap.querySelector<HTMLButtonElement>("#resetBtn")!;

  let schedules: Schedule[] = [];

  function setStatus(text: string, kind: "info" | "success" | "error" = "info") {
    status.textContent = text || "";
    status.className = `status ${kind}`;
  }

  function escapeHtml(s: unknown) {
    const str = String(s ?? "");
    return str
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

  function parseList(v: string): string[] {
    return (v || "")
      .split(",")
      .map((x) => x.trim())
      .filter((x) => x.length > 0);
  }

  function updateCadenceVisibility() {
    const cad = cadenceEl.value as Recurrence["cadence"];
    if (cad === "hourly") {
      timeFields.style.display = "";
      weekdayField.style.display = "none";
    } else if (cad === "daily") {
      timeFields.style.display = "";
      weekdayField.style.display = "none";
    } else {
      timeFields.style.display = "";
      weekdayField.style.display = "";
    }
  }

  cadenceEl.addEventListener("change", updateCadenceVisibility);
  updateCadenceVisibility();

  function readForm(): {
    prompt: string;
    symbols: string[];
    recurrence: Recurrence;
    email: EmailSettings;
    active: boolean;
  } {
    const prompt = (promptEl.value || "").trim();
    const symbols = parseList(symbolsEl.value);
    const cadence = (cadenceEl.value || "daily") as Recurrence["cadence"];
    const interval = Math.max(1, Number(intervalEl.value || 1) || 1);
    let hour: number | null | undefined = Number(hourEl.value);
    let minute: number | null | undefined = Number(minuteEl.value);
    let weekday: number | null | undefined = Number(weekdayEl.value);

    if (cadence === "hourly") {
      // Only minute is relevant; keep hour for consistency but backend can ignore if not needed
      hour = Number.isFinite(hour) ? hour : 0;
      minute = Number.isFinite(minute) ? minute : 0;
      weekday = null;
    } else if (cadence === "daily") {
      hour = Number.isFinite(hour) ? hour : 9;
      minute = Number.isFinite(minute) ? minute : 0;
      weekday = null;
    } else {
      hour = Number.isFinite(hour) ? hour : 9;
      minute = Number.isFinite(minute) ? minute : 0;
      weekday = Number.isFinite(weekday as number) ? (weekday as number) : 0;
    }

    const email: EmailSettings = {
      to: parseList(emailToEl.value),
      attachPdf: !!attachPdfEl.checked
    };

    return {
      prompt,
      symbols,
      recurrence: { cadence, interval, hour, minute, weekday },
      email,
      active: !!activeEl.checked
    };
  }

  function validateForm(): string | null {
    const data = readForm();
    if (!data.prompt) return "Prompt is required.";
    if (!data.recurrence?.cadence) return "Cadence is required.";
    if (!data.recurrence?.interval || data.recurrence.interval < 1) return "Interval must be >= 1.";
    if (data.recurrence.cadence !== "hourly") {
      if (data.recurrence.hour == null || data.recurrence.minute == null) return "Hour and minute are required.";
    }
    return null;
  }

  function fmtCadence(r: Recurrence | undefined): string {
    if (!r) return "";
    const base = `${r.cadence} x${r.interval}`;
    if (r.cadence === "hourly") {
      return base + (typeof r.minute === "number" ? ` at :${String(r.minute).padStart(2, "0")}` : "");
    }
    if (r.cadence === "daily") {
      return base + (typeof r.hour === "number" && typeof r.minute === "number" ? ` at ${String(r.hour).padStart(2, "0")}:${String(r.minute).padStart(2, "0")}` : "");
    }
    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const day = typeof r.weekday === "number" ? days[r.weekday] : "";
    const time = typeof r.hour === "number" && typeof r.minute === "number" ? ` ${String(r.hour).padStart(2, "0")}:${String(r.minute).padStart(2, "0")}` : "";
    return `${base} ${day}${time}`;
    }

  function renderRows() {
    if (!schedules.length) {
      tbody.innerHTML = `<tr><td colspan="6">No schedules found.</td></tr>`;
      return;
    }
    const rows = schedules
      .map((s) => {
        const sym = (s.symbols || []).join(", ");
        const cadence = fmtCadence(s.recurrence);
        const next = fmtDate(s.nextRunAt);
        const prompt = (s.prompt || s.id || "").slice(0, 120);
        return `
          <tr data-id="${s.id}">
            <td title="${escapeHtml(s.prompt || s.id || "")}">${escapeHtml(prompt)}</td>
            <td>${escapeHtml(sym)}</td>
            <td>${escapeHtml(cadence)}</td>
            <td>${escapeHtml(next)}</td>
            <td>${s.active ? "Yes" : "No"}</td>
            <td>
              <button class="runBtn">Run now</button>
              <button class="deleteBtn danger">Delete</button>
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
        const tr = btn.closest("tr");
        const id = tr?.getAttribute("data-id");
        if (!id) return;
        btn.disabled = true;
        setStatus("Starting run…", "info");
        try {
          const res = await runScheduleNow(id);
          setStatus(`Run started. Instance: ${res.instanceId}`, "success");
        } catch (err: any) {
          setStatus(`Run failed: ${err?.message ?? String(err)}`, "error");
        } finally {
          btn.disabled = false;
        }
      });
    });

    tbody.querySelectorAll<HTMLButtonElement>(".deleteBtn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const tr = btn.closest("tr");
        const id = tr?.getAttribute("data-id");
        if (!id) return;
        btn.disabled = true;
        setStatus("Deleting schedule…", "info");
        try {
          await deleteSchedule(id);
          schedules = schedules.filter((x) => x.id !== id);
          renderRows();
          setStatus("Schedule deleted.", "success");
        } catch (err: any) {
          setStatus(`Delete failed: ${err?.message ?? String(err)}`, "error");
          btn.disabled = false;
        }
      });
    });
  }

  refreshBtn.addEventListener("click", () => load());

  createBtn.addEventListener("click", async () => {
    const err = validateForm();
    if (err) {
      setStatus(err, "error");
      return;
    }
    const data = readForm();
    setStatus("Creating schedule…", "info");
    createBtn.disabled = true;
    createRunNowBtn.disabled = true;
    try {
      const s = await createSchedule(data);
      setStatus("Schedule created.", "success");
      await load();
      // Keep the form values, just created; do not auto-reset
    } catch (e: any) {
      setStatus(`Create failed: ${e?.message ?? String(e)}`, "error");
    } finally {
      createBtn.disabled = false;
      createRunNowBtn.disabled = false;
    }
  });

  createRunNowBtn.addEventListener("click", async () => {
    const err = validateForm();
    if (err) {
      setStatus(err, "error");
      return;
    }
    const data = readForm();
    setStatus("Creating schedule and starting run…", "info");
    createBtn.disabled = true;
    createRunNowBtn.disabled = true;
    try {
      const s = await createSchedule(data);
      if (!s?.id) throw new Error("Schedule created but id missing.");
      const res = await runScheduleNow(s.id);
      setStatus(`Schedule created and run started. Instance: ${res.instanceId}`, "success");
      await load();
    } catch (e: any) {
      setStatus(`Create+Run failed: ${e?.message ?? String(e)}`, "error");
    } finally {
      createBtn.disabled = false;
      createRunNowBtn.disabled = false;
    }
  });

  resetBtn.addEventListener("click", () => {
    promptEl.value = "";
    symbolsEl.value = "";
    cadenceEl.value = "daily";
    intervalEl.value = "1";
    hourEl.value = "9";
    minuteEl.value = "0";
    weekdayEl.value = "0";
    emailToEl.value = "";
    attachPdfEl.checked = false;
    activeEl.checked = true;
    updateCadenceVisibility();
    setStatus("");
  });

  async function load() {
    try {
      setStatus("Loading…", "info");
      schedules = await listSchedules(200);
      renderRows();
      setStatus("");
    } catch (err: any) {
      tbody.innerHTML = `<tr><td colspan="6">Failed to load: ${escapeHtml(err?.message ?? String(err))}</td></tr>`;
      setStatus("Failed to load schedules.", "error");
    }
  }

  load();
}
