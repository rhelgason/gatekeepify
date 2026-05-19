import { trackEvent } from "./track";

export async function shareOrDownload(
  blob: Blob,
  filename: string,
  surface: string,
  entityId?: string,
): Promise<void> {
  const file = new File([blob], filename, { type: "image/png" });

  if (typeof navigator !== "undefined" && navigator.canShare?.({ files: [file] })) {
    try {
      await navigator.share({ files: [file] });
      trackEvent("share_card_shared", { surface, entity_id: entityId, method: "web_share" });
      return;
    } catch {
      // User cancelled or share failed — fall through to download
    }
  }

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
  trackEvent("share_card_shared", { surface, entity_id: entityId, method: "download" });
}
