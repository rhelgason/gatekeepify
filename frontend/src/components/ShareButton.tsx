"use client";

import { useEffect, useState } from "react";
import { generateShareCard, ShareCardData } from "@/lib/shareCard";
import { tryNativeShare, downloadBlob, copyImageToClipboard } from "@/lib/share";
import { trackEvent } from "@/lib/track";

interface ShareButtonProps {
  cardData: ShareCardData;
  surface: "artist" | "feed" | "dashboard" | "wrapped";
  entityId?: string;
  className?: string;
  variant?: "icon" | "button";
}

export default function ShareButton({ cardData, surface, entityId, className = "", variant = "icon" }: ShareButtonProps) {
  const [generating, setGenerating] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [copied, setCopied] = useState(false);

  const filename = `gatekeepify-${cardData.artistName.toLowerCase().replace(/\s+/g, "-")}.png`;

  async function handleShare(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    setGenerating(true);
    try {
      trackEvent("share_card_generated", { surface, entity_id: entityId });
      const b = await generateShareCard(cardData);
      const shared = await tryNativeShare(b, filename, surface, entityId);
      if (!shared) {
        const url = URL.createObjectURL(b);
        setBlob(b);
        setPreviewUrl(url);
      }
    } catch (err) {
      trackEvent("share_card_failed", { surface, entity_id: entityId, error: String(err) });
    } finally {
      setGenerating(false);
    }
  }

  function closeModal() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setBlob(null);
    setCopied(false);
  }

  // Close the preview modal on Escape.
  useEffect(() => {
    if (!previewUrl) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") closeModal();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [previewUrl]);

  const shareIcon = (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
      <polyline points="16 6 12 2 8 6" />
      <line x1="12" y1="2" x2="12" y2="15" />
    </svg>
  );

  return (
    <>
      {variant === "button" ? (
        <button
          onClick={handleShare}
          disabled={generating}
          className={`btn-secondary text-sm flex items-center gap-2 ${className}`}
        >
          {shareIcon}
          {generating ? "Generating..." : "Share"}
        </button>
      ) : (
        <button
          onClick={handleShare}
          disabled={generating}
          className={`w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-gray-500 hover:text-white hover:bg-white/10 transition-all ${generating ? "animate-pulse" : ""} ${className}`}
          title="Share"
          aria-label="Share"
        >
          {shareIcon}
        </button>
      )}

      {previewUrl && blob && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Share card preview"
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
          onClick={closeModal}
        >
          <div
            className="bg-[#141414] rounded-2xl border border-white/10 shadow-2xl max-w-sm w-full overflow-hidden animate-fade-in"
            onClick={(e) => e.stopPropagation()}
          >
            <img src={previewUrl} alt="Share card preview" className="w-full" />
            <div className="p-4 flex gap-2">
              <button
                onClick={async () => {
                  const ok = await copyImageToClipboard(blob, surface, entityId);
                  if (ok) {
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  }
                }}
                className="btn-primary flex-1 text-sm"
              >
                {copied ? "Copied!" : "Copy Image"}
              </button>
              <button
                onClick={() => {
                  downloadBlob(blob, filename, surface, entityId);
                  closeModal();
                }}
                className="btn-secondary flex-1 text-sm"
              >
                Download
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
