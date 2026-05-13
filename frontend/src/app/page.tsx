"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";

export default function Landing() {
  const router = useRouter();

  useEffect(() => {
    if (isLoggedIn()) router.replace("/dashboard");
  }, [router]);

  async function handleLogin() {
    const { auth_url } = await api.getLoginUrl();
    window.location.href = auth_url;
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
        className="bg-green-500 hover:bg-green-400 text-black font-bold py-3 px-8 rounded-full text-lg transition"
      >
        Sign in with Spotify
      </button>
      <p className="text-gray-600 text-sm mt-6">
        We only read your listening history. We never post or modify anything.
      </p>
    </div>
  );
}
