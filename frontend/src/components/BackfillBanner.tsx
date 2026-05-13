"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";

const HIDDEN_ON = ["/upload", "/auth", "/invite"];

export default function BackfillBanner() {
  const pathname = usePathname();
  const [show, setShow] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) return;
    if (show) return;
    if (typeof window !== "undefined" && sessionStorage.getItem("backfill_dismissed")) {
      return;
    }
    api.getBackfillStatus().then((status) => {
      if (!status.has_export_data) {
        setShow(true);
      }
    }).catch(() => {});
  }, [pathname]);

  if (!show || dismissed) return null;
  if (pathname === "/" || HIDDEN_ON.some((p) => pathname.startsWith(p))) return null;

  return (
    <div className="bg-gradient-to-r from-orange-500/10 to-yellow-500/10 border border-orange-500/20 rounded-2xl p-4 mb-6 flex items-center justify-between gap-4 animate-slide-up">
      <div className="flex items-center gap-3">
        <span className="text-2xl">📦</span>
        <div>
          <p className="text-sm font-bold text-orange-300">
            Upload your Spotify data for the full experience
          </p>
          <p className="text-xs text-gray-500">
            Without your data export, we only have your last few days of listening. Upload to unlock years of history, accurate timelines, and stronger gatekeeping claims.
          </p>
        </div>
      </div>
      <div className="flex gap-2 flex-shrink-0">
        <Link href="/upload" className="btn-primary text-xs py-2 px-4">
          Upload
        </Link>
        <button
          onClick={() => {
            setDismissed(true);
            sessionStorage.setItem("backfill_dismissed", "1");
          }}
          className="text-gray-600 hover:text-gray-400 text-xs px-2"
        >
          Later
        </button>
      </div>
    </div>
  );
}
