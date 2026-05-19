"use client";

import { useEffect, useState } from "react";

export default function ConnectionBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>;
    function handleUnreachable() {
      setVisible(true);
      clearTimeout(timeout);
      timeout = setTimeout(() => setVisible(false), 15000);
    }
    window.addEventListener("api-unreachable", handleUnreachable);
    return () => {
      window.removeEventListener("api-unreachable", handleUnreachable);
      clearTimeout(timeout);
    };
  }, []);

  if (!visible) return null;

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 bg-red-500/10 border border-red-500/20 text-red-400 px-6 py-3 rounded-xl text-sm shadow-xl animate-slide-up max-w-md text-center">
      Unable to reach the server. This may be a temporary outage — try refreshing in a few minutes.
    </div>
  );
}
