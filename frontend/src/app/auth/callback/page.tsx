"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { setToken } from "@/lib/auth";
import { trackEvent } from "@/lib/track";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const token = searchParams.get("token");
    if (token) {
      setToken(token);
      trackEvent("login_completed");
      const pendingInvite = localStorage.getItem("pending_invite");
      if (pendingInvite) {
        localStorage.removeItem("pending_invite");
        router.replace(`/invite/${pendingInvite}`);
      } else {
        router.replace("/dashboard");
      }
    } else {
      router.replace("/");
    }
  }, [router, searchParams]);

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
