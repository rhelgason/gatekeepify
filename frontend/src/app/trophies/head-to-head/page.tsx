"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";
import { trackEvent } from "@/lib/track";

const AWARD_EMOJI: Record<string, string> = {
  crown: "👑", archaeologist: "🦴", trendsetter: "🔥", patient_zero: "🦠",
  obsessive: "🔁", completionist: "✅", night_owl: "🦉",
  genre_snob: "🎭", time_traveler: "⏳", basic: "🫠",
  streak: "⚡", hypebeast: "📈",
};

function HeadToHeadContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const friendId = searchParams.get("friend");

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/");
      return;
    }
    if (!friendId) {
      router.replace("/trophies");
      return;
    }
    api.getHeadToHead(friendId).then((d) => {
      setData(d);
      trackEvent("head_to_head_viewed", { friend_id: friendId });
    }).catch(() => {}).finally(() => setLoading(false));
  }, [friendId, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-gray-500 animate-pulse text-lg">Loading comparison...</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="card p-8 text-center mt-12">
        <p className="text-gray-500">Could not load comparison.</p>
      </div>
    );
  }

  const youName = data.you?.user_name || "You";
  const friendName = data.friend?.user_name || friendId;

  return (
    <div className="animate-fade-in max-w-2xl mx-auto">
      <button onClick={() => router.back()} className="text-xs text-gray-600 hover:text-gray-400 transition-colors">
        &larr; back
      </button>

      {/* Score */}
      <div className="card p-8 mt-4 mb-8 text-center">
        <h1 className="text-2xl font-black mb-6">Head-to-Head</h1>
        <div className="flex items-center justify-center gap-8">
          <div>
            <div className={`stat-number text-4xl ${data.you.wins > data.friend.wins ? "gradient-text" : "text-gray-400"}`}>
              {data.you.wins}
            </div>
            <div className="text-sm text-gray-500 mt-1">{youName}</div>
          </div>
          <div className="text-2xl text-gray-600 font-black">vs</div>
          <div>
            <div className={`stat-number text-4xl ${data.friend.wins > data.you.wins ? "gradient-text" : "text-gray-400"}`}>
              {data.friend.wins}
            </div>
            <div className="text-sm text-gray-500 mt-1">{friendName}</div>
          </div>
        </div>
      </div>

      {/* Comparisons */}
      <div className="space-y-3">
        {data.comparisons.map((c: any) => (
          <div key={c.award_id} className="card p-4 animate-slide-up">
            <div className="flex items-center gap-3 mb-3">
              <span className="text-xl">{AWARD_EMOJI[c.award_id] || "🏆"}</span>
              <span className="font-bold text-sm">{c.award_name}</span>
              {c.winner && (
                <span className={`text-xs font-bold ml-auto ${
                  c.winner === "you" ? "text-[var(--green)]" : "text-red-400"
                }`}>
                  {c.winner === "you" ? youName : friendName} wins
                </span>
              )}
              {!c.winner && c.you !== null && (
                <span className="text-xs text-gray-600 ml-auto">Tied</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <div className={`flex-1 text-right text-sm ${c.winner === "you" ? "font-bold text-white" : "text-gray-500"}`}>
                {c.you !== null ? (
                  typeof c.you === "number" && c.you % 1 !== 0 ? c.you.toFixed(1) : c.you
                ) : "—"}
              </div>
              <div className="w-32 h-2 bg-white/5 rounded-full overflow-hidden flex">
                {c.you !== null && c.friend !== null && (c.you > 0 || c.friend > 0) && (() => {
                  const total = Math.abs(c.you) + Math.abs(c.friend) || 1;
                  const youPct = Math.abs(c.you) / total * 100;
                  return (
                    <>
                      <div className="h-full bg-[var(--green)] rounded-l-full" style={{ width: `${youPct}%` }} />
                      <div className="h-full bg-red-400 rounded-r-full" style={{ width: `${100 - youPct}%` }} />
                    </>
                  );
                })()}
              </div>
              <div className={`flex-1 text-left text-sm ${c.winner === "friend" ? "font-bold text-white" : "text-gray-500"}`}>
                {c.friend !== null ? (
                  typeof c.friend === "number" && c.friend % 1 !== 0 ? c.friend.toFixed(1) : c.friend
                ) : "—"}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function HeadToHead() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-[60vh]"><div className="text-gray-500 animate-pulse">Loading...</div></div>}>
      <HeadToHeadContent />
    </Suspense>
  );
}
