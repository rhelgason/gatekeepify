"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { trackEvent } from "@/lib/track";
import { api } from "@/lib/api";

function LandingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const inviteCode = searchParams.get("invite");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isLoggedIn()) router.replace("/dashboard");
  }, [router]);

  async function handleLogin() {
    setLoading(true);
    setError("");
    trackEvent("login_clicked");
    try {
      const { auth_url } = await api.getLoginUrl(inviteCode || undefined);
      window.location.href = auth_url;
    } catch (e: any) {
      trackEvent("login_error", { error: e.message });
      setError(e.message || "Failed to connect to server");
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[85vh] text-center animate-fade-in">
      <div className="mb-8">
        <div className="inline-block px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-sm text-gray-400 mb-8">
          for music snobs, by music snobs
        </div>
        <h1 className="text-6xl md:text-8xl font-black tracking-tight leading-[0.9] mb-6">
          Prove you
          <br />
          listened{" "}
          <span className="gradient-text">first</span>.
        </h1>
        <p className="text-gray-500 text-lg md:text-xl max-w-lg mx-auto leading-relaxed">
          Track your listening history. Compare with friends.
          <br />
          Settle it with timestamps, not opinions.
        </p>
      </div>
      <button
        onClick={handleLogin}
        disabled={loading}
        className="btn-primary text-lg disabled:opacity-50 disabled:scale-100"
      >
        {loading ? "Connecting..." : "Sign in with Spotify"}
      </button>
      {inviteCode && (
        <p className="text-[var(--green)] text-sm mt-4">
          You&apos;ve been invited! Sign in to accept.
        </p>
      )}
      {error && <p className="text-red-400 text-sm mt-4">{error}</p>}
      <p className="text-gray-700 text-xs mt-8 max-w-sm">
        We only read your listening history. We never post, modify, or share
        anything on your behalf.
      </p>
    </div>
  );
}

export default function Landing() {
  return (
    <Suspense fallback={
      <div className="flex flex-col items-center justify-center min-h-[85vh] text-center">
        <div className="text-gray-500 animate-pulse text-lg">Loading...</div>
      </div>
    }>
      <LandingContent />
    </Suspense>
  );
}
