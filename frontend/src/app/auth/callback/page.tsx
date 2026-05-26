"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { setToken } from "@/lib/auth";
import { trackEvent } from "@/lib/track";

function CallbackHandler() {
  const router = useRouter();
  const [processed, setProcessed] = useState(false);

  useEffect(() => {
    if (processed) return;

    // Read token from URL fragment hash (not query params) for security
    const hash = window.location.hash.substring(1); // remove leading '#'
    const params = new URLSearchParams(hash);
    const token = params.get("token");

    // Also check query params as fallback for backwards compatibility
    const urlParams = new URLSearchParams(window.location.search);
    const finalToken = token;

    // Clean token from URL to prevent leaking in browser history/referrer
    if (window.location.hash || urlParams.has("token")) {
      window.history.replaceState(null, "", window.location.pathname);
    }

    if (finalToken) {
      setToken(finalToken);
      trackEvent("login_completed");
      setProcessed(true);

      const invite = params.get("invite") || localStorage.getItem("pending_invite");
      if (invite && /^[a-zA-Z0-9_-]+$/.test(invite)) {
        localStorage.removeItem("pending_invite");
        router.replace(`/invite/${invite}`);
      } else {
        router.replace("/dashboard");
      }
    } else {
      router.replace("/");
    }
  }, [router, processed]);

  return (
    <div className="text-center">
      <div className="text-4xl mb-4 animate-pulse">🎵</div>
      <p className="text-gray-400 text-lg">Signing you in...</p>
    </div>
  );
}

export default function AuthCallback() {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-[#0a0a0a]">
      <Suspense fallback={<div className="fixed inset-0 flex items-center justify-center bg-[#0a0a0a]"><p className="text-gray-400 text-lg">Loading...</p></div>}>
        <CallbackHandler />
      </Suspense>
    </div>
  );
}
