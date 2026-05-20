import { trackEvent } from "./track";

export async function tryNativeShare(
  blob: Blob,
  filename: string,
  surface: string,
  entityId?: string,
): Promise<boolean> {
  const file = new File([blob], filename, { type: "image/png" });

  if (typeof navigator !== "undefined" && navigator.canShare?.({ files: [file] })) {
    try {
      await navigator.share({ files: [file] });
      trackEvent("share_card_shared", { surface, entity_id: entityId, method: "web_share" });
      return true;
    } catch {
      return false;
    }
  }
  return false;
}

export function downloadBlob(blob: Blob, filename: string, surface: string, entityId?: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
  trackEvent("share_card_shared", { surface, entity_id: entityId, method: "download" });
}

export async function copyImageToClipboard(blob: Blob, surface: string, entityId?: string): Promise<boolean> {
  try {
    await navigator.clipboard.write([
      new ClipboardItem({ "image/png": blob }),
    ]);
    trackEvent("share_card_shared", { surface, entity_id: entityId, method: "clipboard" });
    return true;
  } catch {
    return false;
  }
}
