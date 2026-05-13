"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";

export default function Landing() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isLoggedIn()) router.replace("/dashboard");
  }, [router]);

  async function handleLogin() {
    setLoading(true);
    setError("");
    try {
      const { auth_url } = await api.getLoginUrl();
      window.location.href = auth_url;
    } catch (e: any) {
      setError(e.message || "Failed to connect to server");
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] text-center">
      <h1 className="text-5xl font-bold mb-4">
        Prove you listened <span className="text-green-400">first</span>.
      </h1>
      <p className="text-gray-400 text-lg mb-8 max-w-md">
        Track your Spotify history, compare with friends, and settle the debate
        once and for all.
      </p>
      <button
        onClick={handleLogin}
        disabled={loading}
        className="bg-green-500 hover:bg-green-400 text-black font-bold py-3 px-8 rounded-full text-lg transition disabled:opacity-50"
      >
        {loading ? "Connecting..." : "Sign in with Spotify"}
      </button>
      {error && (
        <p className="text-red-400 text-sm mt-4">{error}</p>
      )}
      <p className="text-gray-600 text-sm mt-6">
        We only read your listening history. We never post or modify anything.
      </p>
    </div>
  );
}
