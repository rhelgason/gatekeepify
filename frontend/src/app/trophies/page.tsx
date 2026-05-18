"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";
import { trackEvent } from "@/lib/track";
import Link from "next/link";

const TIER_META: Record<string, { label: string; color: string; bg: string }> = {
  discovery: { label: "Discovery", color: "text-[var(--green)]", bg: "bg-[var(--green-dim)] border-[var(--green)]/20" },
  devotion: { label: "Devotion", color: "text-purple-400", bg: "bg-purple-500/10 border-purple-500/20" },
  taste: { label: "Taste", color: "text-sky-400", bg: "bg-sky-500/10 border-sky-500/20" },
  dynamic: { label: "Dynamic", color: "text-orange-400", bg: "bg-orange-500/10 border-orange-500/20" },
};

const AWARD_EMOJI: Record<string, string> = {
  crown: "👑", archaeologist: "🦴", trendsetter: "🔥", patient_zero: "🦠",
  obsessive: "🔁", completionist: "✅",
  genre_snob: "🎭", time_traveler: "⏳", basic: "🫠",
  streak: "⚡", hypebeast: "📈",
};

const TIER_ORDER = ["discovery", "devotion", "taste", "dynamic"];

export default function Trophies() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [friends, setFriends] = useState<any[]>([]);
  const [expandedAward, setExpandedAward] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/");
      return;
    }
    Promise.all([api.getTrophies(), api.getFriends()]).then(([t, f]) => {
      setData(t);
      setFriends(f);
      setLoading(false);
    });
  }, [router]);

  if (loading) {
    return (
      <div className="animate-fade-in max-w-2xl mx-auto">
        {/* Hero skeleton */}
        <div className="text-center mb-10">
          <h1 className="text-3xl font-black mb-2">Trophy Case</h1>
          <div className="h-4 w-48 bg-white/5 rounded animate-pulse mx-auto mb-3" />
          <div className="flex items-center justify-center gap-1 mt-3">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="w-5 h-5 bg-white/5 rounded animate-pulse" />
            ))}
          </div>
          <div className="h-3 w-24 bg-white/5 rounded animate-pulse mx-auto mt-2" />
        </div>
        {/* Award tiers skeleton */}
        <div className="space-y-8">
          {[1, 2, 3, 4].map(tier => (
            <section key={tier}>
              <div className="h-3 w-20 bg-white/5 rounded animate-pulse mb-3" />
              <div className="space-y-2">
                {[1, 2, 3].map(award => (
                  <div key={award} className="card p-4 flex items-center gap-4">
                    <div className="w-8 h-8 bg-white/5 rounded animate-pulse flex-shrink-0" />
                    <div className="flex-1 space-y-2">
                      <div className="h-4 w-28 bg-white/5 rounded animate-pulse" />
                      <div className="h-3 w-48 bg-white/5 rounded animate-pulse" />
                    </div>
                    <div className="h-4 w-6 bg-white/5 rounded animate-pulse" />
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
        {/* Head-to-head skeleton */}
        <section className="mt-10">
          <div className="h-3 w-24 bg-white/5 rounded animate-pulse mb-4" />
          <div className="space-y-2">
            {[1, 2].map(i => (
              <div key={i} className="card px-4 py-3 flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-white/5 animate-pulse" />
                <div className="h-4 w-28 bg-white/5 rounded animate-pulse flex-1" />
                <div className="h-3 w-16 bg-white/5 rounded animate-pulse" />
              </div>
            ))}
          </div>
        </section>
      </div>
    );
  }

  const awards = data?.user_awards || [];
  const leaderboards = data?.leaderboards || {};
  const heldAwards = awards.filter((a: any) => a.held);
  const title = data?.title;

  const awardsByTier: Record<string, any[]> = {};
  for (const a of awards) {
    (awardsByTier[a.tier] ??= []).push(a);
  }

  return (
    <div className="animate-fade-in max-w-2xl mx-auto">
      {/* Hero */}
      <div className="text-center mb-10">
        <h1 className="text-3xl font-black mb-2">Trophy Case</h1>
        {title ? (
          <p className="text-gray-400 text-sm">
            Your title:{" "}
            <span className={`font-bold ${TIER_META[awards.find((a: any) => a.award_id === title.award_id)?.tier]?.color || "text-white"}`}>
              {AWARD_EMOJI[title.award_id] || "🏆"} {title.display}
            </span>
          </p>
        ) : (
          <p className="text-gray-600 text-sm">Add friends and keep listening to earn awards.</p>
        )}
        <div className="flex items-center justify-center gap-1 mt-3">
          {awards.map((a: any) => (
            <span
              key={a.award_id}
              className={`text-base ${a.held ? "" : "opacity-20 grayscale"}`}
              title={a.award_name}
            >
              {AWARD_EMOJI[a.award_id] || "🏆"}
            </span>
          ))}
        </div>
        <p className="text-gray-600 text-xs mt-2">
          {heldAwards.length} of {awards.length} held
        </p>
        {(() => {
          const streakAward = awards.find((a: any) => a.award_id === "streak");
          const currentStreak = streakAward?.extra?.current_streak;
          if (currentStreak != null && currentStreak > 0) {
            return (
              <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-orange-500/10 border border-orange-500/20">
                <span className="text-orange-400 text-sm font-bold">⚡ {currentStreak}-day streak</span>
                <span className="text-gray-500 text-xs">Keep it going!</span>
              </div>
            );
          }
          return null;
        })()}
      </div>

      {/* Awards by Tier */}
      <div className="space-y-8">
        {TIER_ORDER.map((tier) => {
          const tierAwards = awardsByTier[tier];
          if (!tierAwards?.length) return null;
          const meta = TIER_META[tier];

          return (
            <section key={tier}>
              <h2 className={`text-xs font-bold uppercase tracking-widest mb-3 ${meta.color}`}>
                {meta.label}
              </h2>
              <div className="space-y-2">
                {tierAwards.map((a: any) => {
                  const isExpanded = expandedAward === a.award_id;
                  const lb = leaderboards[a.award_id] || [];

                  return (
                    <div key={a.award_id}>
                      <button
                        onClick={() => {
                          const next = isExpanded ? null : a.award_id;
                          setExpandedAward(next);
                          if (next) trackEvent("award_viewed", { award_id: next });
                        }}
                        className={`w-full text-left card-hover p-4 flex items-center gap-4 transition-all duration-200 ${
                          a.held ? "" : "opacity-40"
                        } ${isExpanded ? `ring-1 ${meta.bg}` : ""}`}
                      >
                        <span className="text-2xl flex-shrink-0">{AWARD_EMOJI[a.award_id]}</span>
                        <div className="flex-1 min-w-0">
                          <div className={`font-bold text-sm ${a.held ? meta.color : "text-gray-500"}`}>
                            {a.award_name}
                          </div>
                          <div className="text-xs text-gray-600 truncate">{a.description}</div>
                          {a.rank > 0 && a.stat_detail && (
                            <div className="text-xs text-gray-400 mt-1">{a.stat_detail}</div>
                          )}
                        </div>
                        {a.rank > 0 && (
                          <span className={`text-sm font-black flex-shrink-0 ${a.held ? meta.color : "text-gray-600"}`}>#{a.rank}</span>
                        )}
                        <svg
                          width="14" height="14" viewBox="0 0 24 24" fill="none"
                          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                          className={`flex-shrink-0 text-gray-600 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
                        >
                          <polyline points="6 9 12 15 18 9" />
                        </svg>
                      </button>

                      {isExpanded && (
                        <div className="ml-4 mr-4 border-l border-white/5 pl-4 py-2 space-y-1 animate-slide-up">
                          {lb.length > 0 && lb.map((entry: any) => (
                            <div
                              key={entry.user_id}
                              className={`flex items-center justify-between py-2 px-3 rounded-lg text-sm ${
                                entry.rank === 1 ? meta.bg : ""
                              }`}
                            >
                              <div className="flex items-center gap-3">
                                <span className={`font-mono text-xs w-5 text-right ${
                                  entry.rank === 1 ? meta.color : "text-gray-600"
                                }`}>
                                  {entry.rank}
                                </span>
                                <span className="font-medium">{entry.user_name || entry.user_id}</span>
                              </div>
                              <span className="text-gray-500 text-xs">{entry.stat_detail}</span>
                            </div>
                          ))}
                          {a.award_id === "patient_zero" && a.extra?.infections_detail && (
                            <div className="mt-3 pt-3 border-t border-white/5">
                              <p className="text-xs text-gray-500 mb-2">Artists you spread:</p>
                              {a.extra.infections_detail.map((d: any) => (
                                <div key={d.artist_id} className="flex justify-between py-1 text-xs">
                                  <span className="text-gray-300">{d.artist_name}</span>
                                  <span className="text-gray-500">{d.friend_count} {d.friend_count === 1 ? "friend" : "friends"}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>

      {/* Head-to-Head */}
      {friends.length > 0 && (
        <section className="mt-10">
          <h2 className="text-xs font-bold uppercase tracking-widest text-gray-600 mb-4">
            Head-to-Head
          </h2>
          <div className="space-y-2">
            {friends.map((f: any) => (
              <Link
                key={f.user_id}
                href={`/trophies/head-to-head?friend=${f.user_id}`}
                className="card-hover px-4 py-3 flex items-center gap-3"
              >
                {f.image_url ? (
                  <img src={f.image_url} alt="" className="w-8 h-8 rounded-full object-cover" />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-sm text-gray-500">
                    {(f.user_name || f.user_id)[0]?.toUpperCase()}
                  </div>
                )}
                <span className="text-sm font-medium flex-1">{f.user_name || f.user_id}</span>
                <span className="text-gray-600 text-xs">Compare →</span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
