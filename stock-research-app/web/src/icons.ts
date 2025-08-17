/**
 * Lightweight inline SVG icon helpers (stroke-based, 24x24).
 * Usage: button.innerHTML = iconEye() + " View";
 */

function svg(pathD: string, opts: { stroke?: string; fill?: string } = {}) {
  const stroke = opts.stroke ?? "currentColor";
  const fill = opts.fill ?? "none";
  return `
<svg class="icon" width="16" height="16" viewBox="0 0 24 24" fill="${fill}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="${pathD}" stroke="${stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>`.trim();
}

export function iconEye() {
  return svg("M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12Zm11 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z");
}
export function iconDownload() {
  return svg("M12 3v12m0 0 4-4m-4 4-4-4M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2");
}
export function iconTrash() {
  return svg("M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m-1 0v14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V6h10Z");
}
export function iconEdit() {
  return svg("M12 20h9M16.5 3.5a2.121 2.121 0 1 1 3 3L8 18l-4 1 1-4 11.5-11.5Z");
}
export function iconPlay() {
  return svg("M8 5v14l11-7-11-7Z");
}
export function iconRefresh() {
  return svg("M4 4v6h6M20 20v-6h-6M20 8a8 8 0 0 0-14-3M4 16a8 8 0 0 0 14 3");
}
export function iconFilePdf() {
  return svg("M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12V8l-4-6Z");
}
export function iconFileHtml() {
  return svg("M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12V8l-4-6Z");
}
export function iconFileMd() {
  return svg("M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12V8l-4-6Z");
}
export function iconMarkdown() {
  return svg("M3 5h18v14H3V5Zm3 9V8h2l2 2 2-2h2v6h-2v-3l-2 2-2-2v3H6Zm11 0-3-3 3-3h2v6h-2Z");
}
