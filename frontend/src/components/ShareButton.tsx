"use client";

import { useState } from "react";
import { generateShareCard, ShareCardData } from "@/lib/shareCard";
import { shareOrDownload } from "@/lib/share";
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

  async function handleShare(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    setGenerating(true);
    try {
      trackEvent("share_card_generated", { surface, entity_id: entityId });
      const blob = await generateShareCard(cardData);
      const filename = `gatekeepify-${cardData.artistName.toLowerCase().replace(/\s+/g, "-")}.png`;
      await shareOrDownload(blob, filename, surface, entityId);
    } catch (err) {
      trackEvent("share_card_failed", { surface, entity_id: entityId, error: String(err) });
    } finally {
      setGenerating(false);
    }
  }

  if (variant === "button") {
    return (
      <button
        onClick={handleShare}
        disabled={generating}
        className={`btn-secondary text-sm flex items-center gap-2 ${className}`}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
          <polyline points="16 6 12 2 8 6" />
          <line x1="12" y1="2" x2="12" y2="15" />
        </svg>
        {generating ? "Generating..." : "Share"}
      </button>
    );
  }

  return (
    <button
      onClick={handleShare}
      disabled={generating}
      className={`w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-gray-500 hover:text-white hover:bg-white/10 transition-all ${generating ? "animate-pulse" : ""} ${className}`}
      title="Share"
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
        <polyline points="16 6 12 2 8 6" />
        <line x1="12" y1="2" x2="12" y2="15" />
      </svg>
    </button>
  );
}
