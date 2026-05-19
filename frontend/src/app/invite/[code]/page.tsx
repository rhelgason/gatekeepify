"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import { trackEvent } from "@/lib/track";

export default function InvitePage() {
  const router = useRouter();
  const params = useParams();
  const code = params.code as string;
  const [status, setStatus] = useState<"checking" | "accepting" | "success" | "error">("checking");
  const [message, setMessage] = useState("");

  const acceptInvite = useCallback(async () => {
    setStatus("accepting");
    trackEvent("invite_link_opened", { code });
    try {
      await api.acceptInvite(code);
      trackEvent("invite_link_accepted", { code });
      setStatus("success");
      setMessage("You're now friends! Redirecting to your dashboard...");
      setTimeout(() => router.replace("/dashboard"), 2000);
    } catch (e) {
      setStatus("error");
      if (e instanceof ApiError) {
        if (e.message.includes("Already friends")) {
          setMessage("You're already friends! Redirecting...");
          setTimeout(() => router.replace("/dashboard"), 2000);
        } else if (e.message.includes("your own invite")) {
          setMessage("You're signed in as the person who created this invite. Sign out first, then have your friend open this link on their device.");
        } else {
          setMessage(e.message);
        }
      } else {
        setMessage("Something went wrong. Try pasting the code on the Friends page.");
      }
    }
  }, [code, router]);

  useEffect(() => {
    if (!isLoggedIn()) {
      localStorage.setItem("pending_invite", code);
      router.replace(`/?invite=${encodeURIComponent(code)}`);
      return;
    }
    acceptInvite();
  }, [code, router, acceptInvite]);

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-[#0a0a0a]">
      <div className="text-center animate-fade-in">
        {status === "checking" && (
          <>
            <div className="text-4xl mb-4 animate-pulse">🤝</div>
            <p className="text-gray-400 text-lg">Checking invite...</p>
          </>
        )}
        {status === "accepting" && (
          <>
            <div className="text-4xl mb-4 animate-pulse">🤝</div>
            <p className="text-gray-400 text-lg">Accepting invite...</p>
          </>
        )}
        {status === "success" && (
          <>
            <div className="text-4xl mb-4">✅</div>
            <p className="text-[var(--green)] text-lg font-bold">{message}</p>
          </>
        )}
        {status === "error" && (
          <div className="max-w-sm">
            <div className="text-4xl mb-4">😕</div>
            <p className="text-gray-400 text-lg mb-4">{message}</p>
            <button
              onClick={() => router.replace("/friends")}
              className="btn-primary"
            >
              Go to Friends
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
