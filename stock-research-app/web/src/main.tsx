import { getUser, initGoogle, clearToken, getToken } from "./auth";
import { renderReports } from "./pages/reports";
import { renderSchedules } from "./pages/schedules";

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
        <div id="userArea" style="display:flex;align-items:center;gap:10px;"></div>
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
      <h3 style="margin-top:0;">Sign-in required</h3>
      <p>Please sign in with Google to use the app.</p>
      <div id="gsiBtn"></div>
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
      <span style="color:#cbd5e1;">${avatar ? avatar : ""} ${user.name || user.email}</span>
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
  appShell();
  renderUserArea();
  route();
  window.addEventListener("hashchange", route);
  window.addEventListener("auth:changed", route as any);
}

// Start
boot();
