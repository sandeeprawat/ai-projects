import { listReports, deleteReport, getReport, type Report } from "../api";
import { openReportPreview } from "../markdown";
import { iconEye, iconTrash, iconFilePdf, iconFileHtml, iconFileMd, iconMarkdown, iconRefresh } from "../icons";

export function renderReports(root: HTMLElement) {
  root.innerHTML = "";
  const container = document.createElement("div");
  container.className = "page reports-page";

  const header = document.createElement("div");
  header.className = "page-header";
  header.innerHTML = `
    <h2>Reports</h2>
    <div class="actions">
      <button id="bulkDeleteBtn" class="danger" disabled>${iconTrash()} Delete Selected</button>
      <button id="refreshBtn">${iconRefresh()} Refresh</button>
    </div>
  `;
  container.appendChild(header);

  const status = document.createElement("div");
  status.className = "status";
  container.appendChild(status);

  const tableWrap = document.createElement("div");
  tableWrap.className = "table-wrap";
  tableWrap.innerHTML = `
    <table class="table">
      <thead>
        <tr>
          <th style="width:36px;"><input type="checkbox" id="selectAll"/></th>
          <th>Title</th>
          <th>Symbols</th>
          <th>Created</th>
          <th style="width:320px;">Actions</th>
        </tr>
      </thead>
      <tbody id="reportsTbody">
        <tr><td colspan="5">Loading…</td></tr>
      </tbody>
    </table>
  `;
  container.appendChild(tableWrap);

  root.appendChild(container);

  const bulkBtn = header.querySelector<HTMLButtonElement>("#bulkDeleteBtn")!;
  const refreshBtn = header.querySelector<HTMLButtonElement>("#refreshBtn")!;
  const selectAll = tableWrap.querySelector<HTMLInputElement>("#selectAll")!;
  const tbody = tableWrap.querySelector<HTMLTableSectionElement>("#reportsTbody")!;

  // Delegated handlers for view/download actions
  tbody.addEventListener("click", async (ev) => {
    const target = ev.target as HTMLElement;
    const btn = target.closest("button");
    if (!btn) return;

    const tr = btn.closest("tr") as HTMLTableRowElement | null;
    const id = tr?.getAttribute("data-id") || "";
    if (!id) return;

    if (btn.classList.contains("previewBtn")) {
      setStatus("Opening preview…", "info");
      try {
        const urls = await ensureSignedUrls(id);
        if (urls) {
          const title = (tr?.querySelector("td:nth-child(2)") as HTMLElement | null)?.textContent?.trim() || "Report";
          const ok = await openReportPreview(urls, title);
          if (ok) setStatus("");
          else setStatus("No previewable content for this report.", "error");
        } else {
          setStatus("Unable to fetch report details.", "error");
        }
      } catch (err: any) {
        setStatus(`Preview failed: ${err?.message ?? String(err)}`, "error");
      }
      return;
    }

    if (btn.classList.contains("viewBtn")) {
      setStatus("Fetching report link…", "info");
      try {
        const urls = await ensureSignedUrls(id);
        const url = urls?.html || urls?.pdf || urls?.md;
        if (url) {
          window.open(url, "_blank");
          setStatus("");
        } else {
          setStatus("No viewable assets for this report.", "error");
        }
      } catch (err: any) {
        setStatus(`Open failed: ${err?.message ?? String(err)}`, "error");
      }
      return;
    }

    if (btn.classList.contains("dlBtn")) {
      const kind = btn.getAttribute("data-kind") as "pdf" | "html" | "md" | null;
      setStatus(`Preparing ${kind?.toUpperCase() || ""} download…`, "info");
      try {
        const urls = await ensureSignedUrls(id);
        const url = (urls && kind ? (urls as any)[kind] : null) as string | null;
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
          setStatus(`No ${kind?.toUpperCase()} available for this report.`, "error");
        }
      } catch (err: any) {
        setStatus(`Download failed: ${err?.message ?? String(err)}`, "error");
      }
      return;
    }
  });

  let reports: Report[] = [];
  let selected = new Set<string>();

  function setStatus(text: string, kind: "info" | "success" | "error" = "info") {
    status.textContent = text || "";
    status.className = `status ${kind}`;
  }

  function fmtDate(s?: string | null) {
    if (!s) return "";
    try {
      const d = new Date(s);
      return d.toLocaleString();
    } catch {
      return s;
    }
  }

  function escapeHtml(s: unknown) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  async function ensureSignedUrls(id: string): Promise<Report["signedUrls"] | null> {
    const cur = reports.find((r) => r.id === id);
    if (cur?.signedUrls && (cur.signedUrls.html || cur.signedUrls.pdf || cur.signedUrls.md)) {
      return cur.signedUrls;
    }
    try {
      const full = await getReport(id);
      const idx = reports.findIndex((r) => r.id === id);
      if (idx >= 0) {
        reports[idx] = { ...reports[idx], ...full };
      } else {
        reports.push(full);
      }
      return full.signedUrls || null;
    } catch {
      return null;
    }
  }

  function updateSelectAllState() {
    const total = reports.length;
    const sel = selected.size;
    selectAll.indeterminate = sel > 0 && sel < total;
    selectAll.checked = sel > 0 && sel === total;
  }

  function wireRowEvents() {
    tbody.querySelectorAll<HTMLInputElement>(".rowChk").forEach((el) => {
      el.addEventListener("change", () => {
        const tr = el.closest("tr");
        const id = tr?.getAttribute("data-id");
        if (!id) return;
        if (el.checked) selected.add(id);
        else selected.delete(id);
        bulkBtn.disabled = selected.size === 0;
        updateSelectAllState();
      });
    });

    // Single delete — no confirmation dialog (inline status only)
    tbody.querySelectorAll<HTMLButtonElement>(".deleteBtn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const tr = btn.closest("tr");
        const id = tr?.getAttribute("data-id");
        if (!id) return;
        setStatus("Deleting report…", "info");
        btn.disabled = true;
        try {
          await deleteReport(id);
          reports = reports.filter((r) => r.id !== id);
          selected.delete(id);
          renderRows();
          setStatus("Report deleted.", "success");
        } catch (err: any) {
          btn.disabled = false;
          setStatus(`Delete failed: ${err?.message ?? String(err)}`, "error");
        }
      });
    });
  }

  function renderRows() {
    if (!reports.length) {
      tbody.innerHTML = `<tr><td colspan="5">No reports found.</td></tr>`;
      bulkBtn.disabled = true;
      selectAll.checked = false;
      selectAll.indeterminate = false;
      return;
    }
    const rows = reports
      .map((r) => {
        const sym = (r.symbols || []).join(", ");
        const created = fmtDate(r.createdAt);
        const checked = selected.has(r.id) ? "checked" : "";
        return `
          <tr data-id="${r.id}">
            <td><input type="checkbox" class="rowChk" ${checked} /></td>
            <td>${escapeHtml(r.title || r.id)}</td>
            <td>${escapeHtml(sym)}</td>
            <td>${escapeHtml(created)}</td>
            <td>
              <button class="previewBtn">${iconMarkdown()} Preview</button>
              <button class="viewBtn">${iconEye()} View</button>
              <button class="dlBtn" data-kind="pdf" title="Download PDF">${iconFilePdf()} PDF</button>
              <button class="dlBtn secondary" data-kind="html" title="Download HTML">${iconFileHtml()} HTML</button>
              <button class="dlBtn secondary" data-kind="md" title="Download Markdown">${iconFileMd()} MD</button>
              <button class="deleteBtn danger">${iconTrash()} Delete</button>
            </td>
          </tr>
        `;
      })
      .join("");
    tbody.innerHTML = rows;
    wireRowEvents();
    bulkBtn.disabled = selected.size === 0;
    updateSelectAllState();
  }

  selectAll.addEventListener("change", () => {
    selected = new Set<string>();
    if (selectAll.checked) {
      for (const r of reports) selected.add(r.id);
    }
    renderRows();
  });

  refreshBtn.addEventListener("click", () => load());

  bulkBtn.addEventListener("click", async () => {
    if (selected.size === 0) return;
    const ids = Array.from(selected);
    bulkBtn.disabled = true;
    setStatus(`Deleting ${ids.length} report(s)…`, "info");
    try {
      const results = await Promise.allSettled(ids.map((id) => deleteReport(id)));
      const failed = results
        .map((res, idx) => ({ res, id: ids[idx] }))
        .filter((x) => x.res.status === "rejected") as { res: PromiseRejectedResult; id: string }[];
      // Remove all successfully deleted
      const successIds = new Set(
        results
          .map((res, idx) => ({ res, id: ids[idx] }))
          .filter((x) => x.res.status === "fulfilled")
          .map((x) => x.id)
      );
      reports = reports.filter((r) => !successIds.has(r.id));
      for (const id of successIds) selected.delete(id);
      renderRows();

      if (failed.length) {
        setStatus(`Deleted ${ids.length - failed.length} of ${ids.length}. Some deletions failed.`, "error");
      } else {
        setStatus("Bulk delete complete.", "success");
      }
    } catch (err: any) {
      setStatus(`Bulk delete encountered errors: ${err?.message ?? String(err)}`, "error");
    } finally {
      bulkBtn.disabled = selected.size === 0;
    }
  });

  async function load() {
    try {
      setStatus("Loading…", "info");
      selected.clear();
      reports = await listReports({ limit: 200 });
      renderRows();
      setStatus("");
    } catch (err: any) {
      tbody.innerHTML = `<tr><td colspan="5">Failed to load: ${escapeHtml(err?.message ?? String(err))}</td></tr>`;
      setStatus("Failed to load reports.", "error");
    }
  }

  load();
}
