"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";
import Link from "next/link";

const TIER_COLORS: Record<string, string> = {
  discovery: "text-[var(--green)]",
  devotion: "text-purple-400",
  taste: "text-sky-400",
  dynamic: "text-orange-400",
};

const TIER_BG: Record<string, string> = {
  discovery: "bg-[var(--green-dim)] border-[var(--green)]/20",
  devotion: "bg-purple-500/10 border-purple-500/20",
  taste: "bg-sky-500/10 border-sky-500/20",
  dynamic: "bg-orange-500/10 border-orange-500/20",
};

const AWARD_EMOJI: Record<string, string> = {
  crown: "👑",
  archaeologist: "🦴",
  trendsetter: "🔥",
  patient_zero: "🦠",
  obsessive: "🔁",
  completionist: "✅",
  night_owl: "🦉",
  genre_snob: "🎭",
  time_traveler: "⏳",
  basic: "🫠",
  streak: "⚡",
  hypebeast: "📈",
};

export default function Trophies() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [friends, setFriends] = useState<any[]>([]);
  const [selectedAward, setSelectedAward] = useState<string | null>(null);
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
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-gray-500 animate-pulse text-lg">Loading trophies...</div>
      </div>
    );
  }

  const awards = data?.user_awards || [];
  const leaderboards = data?.leaderboards || {};
  const heldAwards = awards.filter((a: any) => a.held);
  const title = data?.title;

  return (
    <div className="animate-fade-in">
      {/* Hero */}
      <div className="text-center mb-10">
        <div className="text-5xl mb-3">
          {title ? AWARD_EMOJI[title.award_id] || "🏆" : "🏆"}
        </div>
        <h1 className="text-3xl font-black mb-1">Trophy Case</h1>
        {title && (
          <p className="text-lg">
            <span className={TIER_COLORS[awards.find((a: any) => a.award_id === title.award_id)?.tier || "discovery"]}>
              {title.display}
            </span>
          </p>
        )}
        <p className="text-gray-600 text-sm mt-2">
          {heldAwards.length} of {awards.length} awards held
        </p>
      </div>

      {/* Trophy Shelf */}
      <div className="flex gap-3 overflow-x-auto pb-4 mb-8 scrollbar-hide">
        {awards.map((a: any) => (
          <button
            key={a.award_id}
            onClick={() => setSelectedAward(selectedAward === a.award_id ? null : a.award_id)}
            className={`flex-shrink-0 card p-4 text-center transition-all duration-200 min-w-[100px] ${
              a.held
                ? `${TIER_BG[a.tier]} ring-1`
                : "opacity-40 hover:opacity-70"
            } ${selectedAward === a.award_id ? "ring-2 ring-white/30 scale-105" : ""}`}
          >
            <div className="text-2xl mb-1">{AWARD_EMOJI[a.award_id] || "🏆"}</div>
            <div className="text-[10px] font-bold truncate">{a.award_name}</div>
            {a.held && a.rank === 1 && (
              <div className={`text-[10px] mt-1 ${TIER_COLORS[a.tier]}`}>
                #{a.rank}
              </div>
            )}
          </button>
        ))}
      </div>

      {/* Selected Award Detail */}
      {selectedAward && (() => {
        const award = awards.find((a: any) => a.award_id === selectedAward);
        const lb = leaderboards[selectedAward] || [];
        if (!award) return null;

        return (
          <div className="card p-6 mb-8 animate-slide-up">
            <div className="flex items-center gap-3 mb-4">
              <span className="text-3xl">{AWARD_EMOJI[award.award_id]}</span>
              <div>
                <h2 className={`text-xl font-black ${TIER_COLORS[award.tier]}`}>{award.award_name}</h2>
                <p className="text-gray-500 text-sm">{award.description}</p>
              </div>
            </div>
            {award.stat_detail && (
              <p className="text-gray-300 mb-4">
                Your stat: <span className="font-bold">{award.stat_detail}</span>
              </p>
            )}
            {lb.length > 0 && (
              <div className="space-y-2">
                {lb.map((entry: any) => (
                  <div
                    key={entry.user_id}
                    className={`flex items-center justify-between py-2 px-3 rounded-xl ${
                      entry.rank === 1 ? TIER_BG[award.tier] : ""
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className={`font-mono text-sm w-6 text-right ${
                        entry.rank === 1 ? TIER_COLORS[award.tier] : "text-gray-600"
                      }`}>
                        {entry.rank}
                      </span>
                      <span className="font-medium text-sm">{entry.user_name || entry.user_id}</span>
                    </div>
                    <span className="text-gray-500 text-xs">{entry.stat_detail}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })()}

      {/* Head-to-Head CTA */}
      {friends.length > 0 && (
        <section className="mb-8">
          <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-4">
            Head-to-Head
          </h2>
          <div className="flex gap-2 flex-wrap">
            {friends.map((f: any) => (
              <Link
                key={f.user_id}
                href={`/trophies/head-to-head?friend=${f.user_id}`}
                className="card-hover px-5 py-3 flex items-center gap-3"
              >
                <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-sm text-gray-500">
                  {(f.user_name || f.user_id)[0]?.toUpperCase()}
                </div>
                <span className="text-sm font-medium">{f.user_name || f.user_id}</span>
                <span className="text-gray-600 text-xs">vs you →</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* All Awards Grid */}
      <section>
        <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-4">
          All Awards
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {awards.map((a: any) => (
            <button
              key={a.award_id}
              onClick={() => setSelectedAward(a.award_id)}
              className={`card-hover p-4 text-left flex items-center gap-4 ${
                a.held ? "" : "opacity-50"
              }`}
            >
              <span className="text-2xl">{AWARD_EMOJI[a.award_id]}</span>
              <div className="flex-1 min-w-0">
                <div className={`font-bold text-sm ${a.held ? TIER_COLORS[a.tier] : "text-gray-500"}`}>
                  {a.award_name}
                </div>
                <div className="text-xs text-gray-600 truncate">{a.description}</div>
                {a.stat_detail && (
                  <div className="text-xs text-gray-400 mt-1">{a.stat_detail}</div>
                )}
              </div>
              {a.held && (
                <span className={`text-xs font-bold ${TIER_COLORS[a.tier]}`}>#{a.rank}</span>
              )}
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
