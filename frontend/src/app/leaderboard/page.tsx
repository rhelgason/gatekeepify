"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";

export default function Leaderboard() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/");
      return;
    }
    api.getLeaderboard().then((d) => {
      setData(d);
      setLoading(false);
    });
  }, [router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-gray-500 animate-pulse text-lg">Loading...</div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <h1 className="text-3xl font-black mb-2">Crown Leaderboard</h1>
      <p className="text-gray-500 mb-8">
        Who discovered the most artists first?
        {data?.total_artists_contested > 0 && (
          <span className="text-gray-400 font-medium">
            {" "}{data.total_artists_contested} artists contested.
          </span>
        )}
      </p>

      {!data?.entries?.length ? (
        <div className="card p-12 text-center">
          <span className="text-5xl mb-4 block">👑</span>
          <p className="text-gray-400 text-lg mb-2">No crowns awarded yet</p>
          <p className="text-gray-600 text-sm">
            Add friends and start listening to compete for crowns.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {data.entries.map((entry: any) => (
            <div
              key={entry.user_id}
              className={`card p-5 flex items-center justify-between animate-slide-up ${
                entry.rank === 1
                  ? "ring-1 ring-[var(--green)]/30 bg-[var(--green-dim)]"
                  : ""
              }`}
              style={{ animationDelay: `${(entry.rank - 1) * 0.1}s` }}
            >
              <div className="flex items-center gap-4">
                <span className={`font-mono text-2xl font-black w-10 text-center ${
                  entry.rank === 1 ? "text-[var(--green)]" : "text-gray-600"
                }`}>
                  {entry.rank}
                </span>
                {entry.rank === 1 && <span className="text-3xl">👑</span>}
                <span className="font-bold text-lg">
                  {entry.user_name || entry.user_id}
                </span>
              </div>
              <div className="text-right">
                <span className="stat-number text-3xl">
                  {entry.crown_count}
                </span>
                <span className="text-gray-500 text-sm block">
                  {entry.crown_count === 1 ? "crown" : "crowns"}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
