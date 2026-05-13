"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { setToken } from "@/lib/auth";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const token = searchParams.get("token");
    if (token) {
      setToken(token);
      router.replace("/dashboard");
    } else {
      router.replace("/");
    }
  }, [router, searchParams]);

  return <p className="text-gray-400">Signing you in...</p>;
}

export default function AuthCallback() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Suspense fallback={<p className="text-gray-400">Loading...</p>}>
        <CallbackHandler />
      </Suspense>
    </div>
  );
}
