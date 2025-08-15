import { renderReports } from "./pages/reports";
import { renderSchedules } from "./pages/schedules";
import { initGoogle, getUser, clearToken } from "./auth";

function qs<T extends HTMLElement = HTMLElement>(root: ParentNode | null, sel: string) {
  return (root ? root.querySelector(sel) : null) as T | null;
}

function buildShell() {
  const root = document.getElementById("root");
  if (!root) return;

  if (!qs(root, ".topbar")) {
    root.innerHTML = `
      <header class="topbar" style="display:flex;align-items:center;gap:16px;padding:8px 12px;border-bottom:1px solid #eee;">
        <div class="brand" style="font-weight:600;">Stock Research</div>
        <nav class="nav" style="display:flex;gap:12px;">
          <a href="#/reports" data-link>Reports</a>
          <a href="#/schedules" data-link>Schedules</a>
        </nav>
        <div style="flex:1 1 auto;"></div>
        <div class="auth" style="display:flex;align-items:center;gap:8px;">
          <div id="googleBtn"></div>
          <div id="userArea" class="user-area" style="display:none;align-items:center;gap:8px;">
            <img id="userPic" alt="avatar" style="width:24px;height:24px;border-radius:50%;vertical-align:middle;" />
            <span id="userName"></span>
            <button id="signOutBtn" class="link" title="Sign out" style="background:none;border:none;color:#06c;cursor:pointer;">Sign out</button>
          </div>
        </div>
      </header>
      <main id="pageRoot" class="page-root"></main>
    `;

    const signOutBtn = qs<HTMLButtonElement>(root, "#signOutBtn");
    signOutBtn?.addEventListener("click", () => clearToken());

    const googleBtn = qs<HTMLElement>(root, "#googleBtn");
    initGoogle(updateAuthUI, googleBtn || null);

    updateAuthUI();
    window.addEventListener("auth:changed" as any, updateAuthUI as any);
  }
}

function updateAuthUI() {
  const root = document.getElementById("root");
  if (!root) return;

  const user = getUser();
  const userArea = qs<HTMLDivElement>(root, "#userArea");
  const googleBtn = qs<HTMLDivElement>(root, "#googleBtn");
  const userName = qs<HTMLSpanElement>(root, "#userName");
  const userPic = qs<HTMLImageElement>(root, "#userPic");

  if (user) {
    if (userArea) userArea.style.display = "flex";
    if (googleBtn) googleBtn.style.display = "none";
    if (userName) userName.textContent = user.name || user.email || user.id || "User";
    if (userPic) {
      if (user.picture) {
        userPic.src = user.picture;
        userPic.style.display = "";
      } else {
        userPic.style.display = "none";
      }
    }
  } else {
    if (userArea) userArea.style.display = "none";
    if (googleBtn) googleBtn.style.display = "";
  }
}

function route() {
  buildShell();

  const pageRoot = document.getElementById("pageRoot") as HTMLElement | null;
  if (!pageRoot) return;

  const path = (location.hash || "").replace(/^#/, "") || "/reports";
  switch (true) {
    case path === "/reports": {
      renderReports(pageRoot);
      break;
    }
    case path === "/schedules": {
      renderSchedules(pageRoot);
      break;
    }
    default: {
      renderReports(pageRoot);
    }
  }
}

window.addEventListener("hashchange", route);
window.addEventListener("DOMContentLoaded", route);
route();
