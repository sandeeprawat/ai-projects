import {
  listTrackedStocks,
  createTrackedStock,
  deleteTrackedStock,
  fetchStockPrices,
  type TrackedStock,
} from "../api";
import { iconTrash, iconRefresh } from "../icons";

const INDIAN_EXCHANGES = new Set(["NSE", "BSE"]);

export function renderPerformance(root: HTMLElement) {
  root.innerHTML = "";
  const container = document.createElement("div");
  container.className = "page performance-page";

  const header = document.createElement("div");
  header.className = "page-header";
  header.innerHTML = `
    <h2>Performance Tracker</h2>
    <div class="actions">
      <button id="refreshBtn">${iconRefresh()} Refresh</button>
    </div>
  `;
  container.appendChild(header);

  // Add stock form
  const formCard = document.createElement("div");
  formCard.className = "card";
  formCard.innerHTML = `
    <h3 style="margin-top:0;">Track a Stock</h3>
    <form id="addStockForm" class="perf-form" autocomplete="off">
      <div class="form-row">
        <label>
          Symbol <span class="required">*</span>
          <input type="text" id="fSymbol" placeholder="e.g. RELIANCE" required style="text-transform:uppercase;" />
        </label>
        <label>
          Exchange
          <select id="fExchange">
            <option value="">Auto / US</option>
            <option value="NSE">NSE (India)</option>
            <option value="BSE">BSE (India)</option>
            <option value="NASDAQ">NASDAQ</option>
            <option value="NYSE">NYSE</option>
          </select>
        </label>
        <label>
          Report Title
          <input type="text" id="fReportTitle" placeholder="e.g. Weekly Stock Report" />
        </label>
        <label>
          Recommendation Date <span class="required">*</span>
          <input type="date" id="fRecDate" required />
        </label>
        <label>
          Recommendation Price <span class="required">*</span>
          <input type="number" id="fRecPrice" step="0.01" min="0.01" placeholder="0.00" required />
        </label>
        <div style="display:flex;align-items:flex-end;">
          <button type="submit">Add Stock</button>
        </div>
      </div>
    </form>
  `;
  container.appendChild(formCard);

  const status = document.createElement("div");
  status.className = "status";
  container.appendChild(status);

  const tableWrap = document.createElement("div");
  tableWrap.className = "table-wrap";
  tableWrap.innerHTML = `
    <table class="table">
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Report</th>
          <th>Rec. Date</th>
          <th style="text-align:right;">Rec. Price</th>
          <th style="text-align:right;">Current Price</th>
          <th style="text-align:right;">Change</th>
          <th style="text-align:right;">Change %</th>
          <th style="width:100px;">Actions</th>
        </tr>
      </thead>
      <tbody id="stocksTbody">
        <tr><td colspan="8">Loading…</td></tr>
      </tbody>
    </table>
  `;
  container.appendChild(tableWrap);

  root.appendChild(container);

  const refreshBtn = header.querySelector<HTMLButtonElement>("#refreshBtn")!;
  const form = formCard.querySelector<HTMLFormElement>("#addStockForm")!;
  const tbody = tableWrap.querySelector<HTMLTableSectionElement>("#stocksTbody")!;

  let stocks: TrackedStock[] = [];
  let prices: Record<string, number | null> = {};

  function setStatus(text: string, kind: "info" | "success" | "error" = "info") {
    status.textContent = text || "";
    status.className = `status ${kind}`;
  }

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
      if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
        const [y, m, d] = s.split("-");
        return `${m}/${d}/${y}`;
      }
      return new Date(s).toLocaleDateString();
    } catch {
      return s;
    }
  }

  function currencySymbol(exchange?: string | null): string {
    return INDIAN_EXCHANGES.has((exchange || "").toUpperCase()) ? "₹" : "$";
  }

  function fmtPrice(n: number | null | undefined, exchange?: string | null): string {
    if (n == null) return "—";
    return currencySymbol(exchange) + n.toFixed(2);
  }

  /** Count how many reports reference this symbol */
  function reportsForSymbol(symbol: string): TrackedStock[] {
    return stocks.filter((s) => s.symbol === symbol);
  }

  function renderRows() {
    if (!stocks.length) {
      tbody.innerHTML = `<tr><td colspan="8">No tracked stocks. Add one above.</td></tr>`;
      return;
    }
    const rows = stocks
      .map((s) => {
        const curPrice = prices[s.symbol] ?? null;
        let changeTd = "—";
        let changePctTd = "—";
        let changeClass = "";
        const cs = currencySymbol(s.exchange);

        if (curPrice != null && s.recommendationPrice > 0) {
          const change = curPrice - s.recommendationPrice;
          const pct = (change / s.recommendationPrice) * 100;
          changeClass = change >= 0 ? "positive" : "negative";
          const sign = change >= 0 ? "+" : "";
          changeTd = `${sign}${cs}${Math.abs(change).toFixed(2)}`;
          changePctTd = `${sign}${pct.toFixed(2)}%`;
        }

        const exchBadge = s.exchange ? `<span class="badge">${escapeHtml(s.exchange)}</span> ` : "";
        const sameSymbolCount = reportsForSymbol(s.symbol).length;
        const symbolLink = sameSymbolCount > 1
          ? `<a href="#" class="symbolLink" data-symbol="${escapeHtml(s.symbol)}">${escapeHtml(s.symbol)}</a>`
          : `<strong>${escapeHtml(s.symbol)}</strong>`;

        // Report link
        const reportCell = s.reportId
          ? `<a href="#/reports?highlight=${encodeURIComponent(s.reportId)}" class="report-link" title="View report">${escapeHtml(s.reportTitle || "View Report")}</a>`
          : escapeHtml(s.reportTitle || "—");

        return `
          <tr data-id="${s.id}">
            <td>${exchBadge}${symbolLink}</td>
            <td>${reportCell}</td>
            <td>${fmtDate(s.recommendationDate)}</td>
            <td style="text-align:right;">${fmtPrice(s.recommendationPrice, s.exchange)}</td>
            <td style="text-align:right;">${curPrice != null ? fmtPrice(curPrice, s.exchange) : '<span class="muted">loading…</span>'}</td>
            <td style="text-align:right;" class="${changeClass}">${changeTd}</td>
            <td style="text-align:right;" class="${changeClass}">${changePctTd}</td>
            <td>
              <button class="deleteBtn danger" title="Remove">${iconTrash()}</button>
            </td>
          </tr>
        `;
      })
      .join("");
    tbody.innerHTML = rows;
    wireRowEvents();
  }

  function wireRowEvents() {
    tbody.querySelectorAll<HTMLButtonElement>(".deleteBtn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const tr = btn.closest("tr");
        const id = tr?.getAttribute("data-id");
        if (!id) return;
        setStatus("Removing stock…", "info");
        btn.disabled = true;
        try {
          await deleteTrackedStock(id);
          stocks = stocks.filter((s) => s.id !== id);
          renderRows();
          setStatus("Stock removed.", "success");
        } catch (err: any) {
          btn.disabled = false;
          setStatus(`Delete failed: ${err?.message ?? String(err)}`, "error");
        }
      });
    });

    // Symbol click → show all reports for that symbol
    tbody.querySelectorAll<HTMLAnchorElement>(".symbolLink").forEach((link) => {
      link.addEventListener("click", (ev) => {
        ev.preventDefault();
        const sym = link.getAttribute("data-symbol") || "";
        const related = reportsForSymbol(sym);
        if (!related.length) return;
        const list = related
          .map((r) => {
            const title = escapeHtml(r.reportTitle || "Untitled");
            const date = fmtDate(r.recommendationDate);
            const price = fmtPrice(r.recommendationPrice, r.exchange);
            const link = r.reportId
              ? `<a href="#/reports?highlight=${encodeURIComponent(r.reportId)}" class="report-link">${title}</a>`
              : title;
            return `<li>${link} — ${date} at ${price}</li>`;
          })
          .join("");
        showSymbolPopup(sym, list);
      });
    });
  }

  function showSymbolPopup(symbol: string, listHtml: string) {
    // Remove any existing popup
    document.querySelector(".symbol-popup-backdrop")?.remove();
    const backdrop = document.createElement("div");
    backdrop.className = "modal-backdrop symbol-popup-backdrop";
    backdrop.innerHTML = `
      <div class="modal" style="width:min(600px,90vw);max-height:60vh;">
        <div class="modal-header">
          <span class="modal-title">Reports for ${escapeHtml(symbol)}</span>
          <button class="modal-close">&times;</button>
        </div>
        <div class="modal-body">
          <ul style="margin:0;padding-left:20px;">${listHtml}</ul>
        </div>
      </div>
    `;
    document.body.appendChild(backdrop);
    backdrop.querySelector(".modal-close")?.addEventListener("click", () => backdrop.remove());
    backdrop.addEventListener("click", (e) => { if (e.target === backdrop) backdrop.remove(); });
  }

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const symbolEl = form.querySelector<HTMLInputElement>("#fSymbol")!;
    const exchangeEl = form.querySelector<HTMLSelectElement>("#fExchange")!;
    const reportTitleEl = form.querySelector<HTMLInputElement>("#fReportTitle")!;
    const recDateEl = form.querySelector<HTMLInputElement>("#fRecDate")!;
    const recPriceEl = form.querySelector<HTMLInputElement>("#fRecPrice")!;

    const symbol = symbolEl.value.trim().toUpperCase();
    const exchange = exchangeEl.value.trim().toUpperCase() || undefined;
    const reportTitle = reportTitleEl.value.trim();
    const recDate = recDateEl.value;
    const recPrice = parseFloat(recPriceEl.value);

    if (!symbol || !recDate || isNaN(recPrice) || recPrice <= 0) {
      setStatus("Please fill all required fields.", "error");
      return;
    }

    setStatus("Adding stock…", "info");
    const submitBtn = form.querySelector<HTMLButtonElement>("button[type=submit]")!;
    submitBtn.disabled = true;

    try {
      const created = await createTrackedStock({
        symbol,
        exchange,
        reportTitle: reportTitle || undefined,
        recommendationDate: recDate,
        recommendationPrice: recPrice,
      });
      stocks.push(created);
      stocks.sort((a, b) => a.symbol.localeCompare(b.symbol));

      // Fetch price for new symbol
      loadPrices([created]);

      renderRows();
      form.reset();
      setStatus(`${created.symbol} added.`, "success");
    } catch (err: any) {
      setStatus(`Failed to add: ${err?.message ?? String(err)}`, "error");
    } finally {
      submitBtn.disabled = false;
    }
  });

  refreshBtn.addEventListener("click", () => load());

  async function loadPrices(subset?: TrackedStock[]) {
    const items = subset ?? stocks;
    if (!items.length) return;
    // Deduplicate symbols for price fetch
    const seen = new Set<string>();
    const syms: string[] = [];
    const exchs: string[] = [];
    for (const s of items) {
      if (!seen.has(s.symbol)) {
        seen.add(s.symbol);
        syms.push(s.symbol);
        exchs.push(s.exchange || "");
      }
    }
    try {
      const fetched = await fetchStockPrices(syms, exchs);
      prices = { ...prices, ...fetched };
      renderRows();
    } catch {
      // Silently fail price fetch — rows will show "loading…"
    }
  }

  async function load() {
    try {
      setStatus("Loading…", "info");
      stocks = await listTrackedStocks();
      prices = {};
      renderRows();
      setStatus("");
      loadPrices();
    } catch (err: any) {
      tbody.innerHTML = `<tr><td colspan="8">Failed to load: ${escapeHtml(err?.message ?? String(err))}</td></tr>`;
      setStatus("Failed to load tracked stocks.", "error");
    }
  }

  load();
}
