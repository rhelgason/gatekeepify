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
    return <p className="text-gray-400 mt-12 text-center">Loading...</p>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Leaderboard</h1>
      <p className="text-gray-500 mb-6">
        Who discovered the most artists first among your friend group?
        {data?.total_artists_contested > 0 && (
          <span>
            {" "}
            {data.total_artists_contested} artists contested.
          </span>
        )}
      </p>

      {!data?.entries?.length ? (
        <p className="text-gray-500">
          Add friends to start competing. No contested artists yet.
        </p>
      ) : (
        <div className="space-y-3">
          {data.entries.map((entry: any) => (
            <div
              key={entry.user_id}
              className={`flex items-center justify-between rounded-lg px-4 py-3 ${
                entry.rank === 1
                  ? "bg-green-500/10 border border-green-500/30"
                  : "bg-gray-900"
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="text-gray-500 font-mono w-6">
                  #{entry.rank}
                </span>
                {entry.rank === 1 && <span className="text-2xl">👑</span>}
                <span className="font-medium">
                  {entry.user_name || entry.user_id}
                </span>
              </div>
              <span className="text-green-400 font-semibold">
                {entry.crown_count}{" "}
                {entry.crown_count === 1 ? "crown" : "crowns"}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
