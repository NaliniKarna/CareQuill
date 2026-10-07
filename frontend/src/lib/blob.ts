/**
 * Opens (or downloads) a Blob from an async handler.
 *
 * Uses a synthetic `<a>` click rather than `window.open()`: by the time the
 * blob is ready the browser is outside the original click's call stack, and
 * `window.open()` there is routinely popup-blocked, while an anchor click is
 * not.
 */
export function openBlob(blob: Blob, options: { download?: string } = {}): void {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  if (options.download) {
    link.download = options.download;
  } else {
    link.target = "_blank";
    link.rel = "noopener noreferrer";
  }
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => window.URL.revokeObjectURL(url), 60_000);
}
