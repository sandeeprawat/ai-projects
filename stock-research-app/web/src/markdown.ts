/**
 * Markdown preview module using local deps (marked + DOMPurify).
 * - Sanitizes and renders content inside a themed modal.
 */

import { marked } from "marked";
import createDOMPurify from "dompurify";

marked.setOptions({ gfm: true });

const DOMPurify = createDOMPurify(window);

// Convert bare URLs to autolink form so markdown preview links render without altering authored syntax
function linkifyBareUrls(md: string): string {
  try {
    // Wrap bare http(s) URLs not already in angle brackets/markdown links
    return md.replace(/(^|[\s(])((https?:\/\/)[^\s<>)]+)/g, (_m, pre, url) => `${pre}<${url}>`);
  } catch {
    return md;
  }
}

// Modal UI
let modalHost: HTMLDivElement | null = null;
let modalTitleEl: HTMLElement | null = null;
let modalBodyEl: HTMLDivElement | null = null;

function ensureModal() {
  if (modalHost) return;

  modalHost = document.createElement("div");
  modalHost.className = "modal-backdrop hidden";
  modalHost.setAttribute("role", "dialog");
  modalHost.setAttribute("aria-modal", "true");

  const modal = document.createElement("div");
  modal.className = "modal";

  const header = document.createElement("div");
  header.className = "modal-header";

  modalTitleEl = document.createElement("div");
  modalTitleEl.className = "modal-title";
  modalTitleEl.textContent = "Preview";

  const closeBtn = document.createElement("button");
  closeBtn.className = "modal-close";
  closeBtn.type = "button";
  closeBtn.innerHTML = "&times;";
  closeBtn.addEventListener("click", () => closeModal());

  header.appendChild(modalTitleEl);
  header.appendChild(closeBtn);

  modalBodyEl = document.createElement("div");
  modalBodyEl.className = "modal-body markdown-body";

  modal.appendChild(header);
  modal.appendChild(modalBodyEl);
  modalHost.appendChild(modal);

  modalHost.addEventListener("click", (e) => {
    if (e.target === modalHost) closeModal();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modalHost!.classList.contains("hidden")) {
      closeModal();
    }
  });

  document.body.appendChild(modalHost);
}

function openModal(title?: string) {
  ensureModal();
  if (modalTitleEl) modalTitleEl.textContent = title || "Preview";
  modalHost!.classList.remove("hidden");
  document.documentElement.style.overflow = "hidden";
}

function closeModal() {
  if (!modalHost) return;
  modalHost.classList.add("hidden");
  document.documentElement.style.overflow = "";
}

function toProxiedUrl(u: string): string {
  try {
    const parsed = new URL(u);
    const isAzurite =
      (parsed.hostname === "127.0.0.1" || parsed.hostname === "localhost") &&
      parsed.port === "10000";
    if (isAzurite) {
      // Route via Vite proxy (/blob -> 127.0.0.1:10000)
      return `/blob${parsed.pathname}${parsed.search}`;
    }
  } catch {
    // ignore parse errors, return original
  }
  return u;
}

async function fetchText(url: string): Promise<string> {
  const target = toProxiedUrl(url);
  const res = await fetch(target, { credentials: "include" });
  if (!res.ok) throw new Error(`Fetch failed: ${res.status} ${res.statusText}`);
  return await res.text();
}

export async function openMarkdownFromText(md: string, title?: string) {
  const html = await marked.parse(linkifyBareUrls(md));
  const safe = DOMPurify.sanitize(html, { USE_PROFILES: { html: true }, ADD_TAGS: ["sup", "sub"] });
  ensureModal();
  if (modalBodyEl) modalBodyEl.innerHTML = safe;
  openModal(title);
}

export async function openMarkdownFromUrl(url: string, title?: string) {
  const md = await fetchText(url);
  await openMarkdownFromText(md, title);
}

export async function openHtmlFromUrl(url: string, title?: string) {
  const html = await fetchText(url);
  const safe = DOMPurify.sanitize(html, { USE_PROFILES: { html: true }, ADD_TAGS: ["sup", "sub"] });
  ensureModal();
  if (modalBodyEl) modalBodyEl.innerHTML = safe;
  openModal(title);
}

/**
 * Try to preview report content:
 * - Prefer Markdown if available, else sanitized HTML.
 * Returns true if preview opened, false otherwise.
 */
export async function openReportPreview(urls: { md?: string | null; html?: string | null }, title?: string): Promise<boolean> {
  if (urls?.html) {
    await openHtmlFromUrl(urls.html, title);
    return true;
  }
  if (urls?.md) {
    await openMarkdownFromUrl(urls.md, title);
    return true;
  }
  return false;
}
