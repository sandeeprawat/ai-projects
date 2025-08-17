import { getUser, initGoogle, clearToken, getToken } from "./auth";
import { renderReports } from "./pages/reports";
import { renderSchedules } from "./pages/schedules";

type Theme = "light" | "dark";

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme === "dark" ? "dark" : "light");
  localStorage.setItem("theme", theme);
  const btn = document.getElementById("themeToggle") as HTMLButtonElement | null;
  if (btn) btn.textContent = theme === "dark" ? "Light" : "Dark";
}

function initTheme() {
  const saved = localStorage.getItem("theme") as Theme | null;
  const theme: Theme =
    saved ?? (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  applyTheme(theme);
}

function wireThemeToggle() {
  const btn = document.getElementById("themeToggle") as HTMLButtonElement | null;
  if (!btn) return;
  btn.addEventListener("click", () => {
    const current = (document.documentElement.getAttribute("data-theme") as Theme) || "light";
    applyTheme(current === "dark" ? "light" : "dark");
  });
  const current = (document.documentElement.getAttribute("data-theme") as Theme) || "light";
  btn.textContent = current === "dark" ? "Light" : "Dark";
}

function appShell() {
  const el = document.getElementById("root")!;
  el.innerHTML = `
    <div class="app">
      <div class="topbar">
        <div class="brand">
          <span class="dot"></span>
          <span>Stock Research</span>
        </div>
        <nav class="nav">
          <a href="#/schedules" id="nav-schedules">Schedules</a>
          <a href="#/reports" id="nav-reports">Reports</a>
        </nav>
        <div style="display:flex;align-items:center;gap:8px;">
          <button id="themeToggle" class="secondary" title="Toggle theme">Dark</button>
          <div id="userArea" style="display:flex;align-items:center;gap:10px;"></div>
        </div>
      </div>
      <main class="main">
        <div id="pageRoot"></div>
      </main>
    </div>
  `;
}

function setActiveNav() {
  const hash = location.hash || "#/schedules";
  const navs = [
    { id: "nav-schedules", href: "#/schedules" },
    { id: "nav-reports", href: "#/reports" }
  ];
  for (const n of navs) {
    const a = document.getElementById(n.id) as HTMLAnchorElement | null;
    if (!a) continue;
    a.classList.toggle("active", hash.startsWith(n.href));
  }
}

function requireAuthNotice(container: HTMLElement) {
  container.innerHTML = `
    <div class="card">
      <div style="display:flex; gap:16px; align-items:center;">
        <div aria-hidden="true">
          <svg width="72" height="72" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="g1" x1="0" y1="0" x2="48" y2="48" gradientUnits="userSpaceOnUse">
                <stop stop-color="#60a5fa"/>
                <stop offset="1" stop-color="#2563eb"/>
              </linearGradient>
            </defs>
            <rect x="4" y="8" width="40" height="32" rx="8" fill="url(#g1)" opacity="0.2"/>
            <path d="M16 22v-4a8 8 0 1 1 16 0v4" stroke="var(--primary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <rect x="12" y="22" width="24" height="16" rx="4" stroke="var(--primary)" stroke-width="2"/>
            <circle cx="24" cy="30" r="2" fill="var(--primary)"/>
          </svg>
        </div>
        <div>
          <h3 style="margin-top:0;">Sign-in required</h3>
          <p>Please sign in with Google to use the app.</p>
          <div id="gsiBtn"></div>
        </div>
      </div>
    </div>
  `;
  const host = container.querySelector("#gsiBtn") as HTMLElement | null;
  initGoogle(() => {}, host || undefined);
}

function renderUserArea() {
  const area = document.getElementById("userArea")!;
  const user = getUser();
  area.innerHTML = "";
  if (user) {
    const avatar = user.picture ? `<img src="${user.picture}" alt="" style="width:24px;height:24px;border-radius:50%;">` : "";
    area.innerHTML = `
      <span style="color:var(--muted);">${avatar ? avatar : ""} ${user.name || user.email}</span>
      <button id="signOutBtn" class="secondary">Sign out</button>
    `;
    const btn = area.querySelector("#signOutBtn") as HTMLButtonElement | null;
    btn?.addEventListener("click", () => clearToken());
  } else {
    area.innerHTML = `<div id="gsiBtnTop"></div>`;
    const host = area.querySelector("#gsiBtnTop") as HTMLElement | null;
    initGoogle(() => {}, host || undefined);
  }
}

function route() {
  setActiveNav();
  renderUserArea();
  const token = getToken();
  const pageRoot = document.getElementById("pageRoot")!;
  const hash = location.hash || "#/schedules";

  if (!token) {
    // Allow viewing shell but block pages until signed-in
    requireAuthNotice(pageRoot);
    return;
  }

  // Render requested page
  if (hash.startsWith("#/reports")) {
    renderReports(pageRoot);
  } else {
    renderSchedules(pageRoot);
  }
}

function boot() {
  initTheme();
  appShell();
  wireThemeToggle();
  renderUserArea();
  route();
  window.addEventListener("hashchange", route);
  window.addEventListener("auth:changed", route as any);
}

// Start
boot();
