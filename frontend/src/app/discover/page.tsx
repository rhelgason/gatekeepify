"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";
import Link from "next/link";

export default function Discover() {
  const router = useRouter();
  const [freshFinds, setFreshFinds] = useState<any[]>([]);
  const [lateOn, setLateOn] = useState<any[]>([]);
  const [rising, setRising] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/");
      return;
    }
    Promise.all([
      api.getFriendsFreshFinds().catch(() => []),
      api.getYoureLateOn().catch(() => []),
      api.getRisingArtists().catch(() => []),
    ]).then(([ff, lo, r]) => {
      setFreshFinds(ff);
      setLateOn(lo);
      setRising(r);
      setLoading(false);
    });
  }, [router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-gray-500 animate-pulse text-lg">Finding music...</div>
      </div>
    );
  }

  const isEmpty = freshFinds.length === 0 && lateOn.length === 0 && rising.length === 0;

  return (
    <div className="animate-fade-in">
      <h1 className="text-3xl font-black mb-2">Discover</h1>
      <p className="text-gray-500 mb-8">
        Get in early. Find music before your friends can gatekeep you.
      </p>

      {isEmpty ? (
        <div className="card p-12 text-center">
          <span className="text-5xl mb-4 block">🔍</span>
          <p className="text-gray-400 text-lg mb-2">Nothing to discover yet</p>
          <p className="text-gray-600 text-sm">
            Add friends and keep listening. Recommendations appear as your network grows.
          </p>
        </div>
      ) : (
        <>
          {/* You're Late On */}
          {lateOn.length > 0 && (
            <section className="mb-10">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-2xl">⚠️</span>
                <div>
                  <h2 className="text-lg font-black text-orange-400">You&apos;re Late On...</h2>
                  <p className="text-gray-600 text-xs">Artists your friends listen to that you haven&apos;t touched</p>
                </div>
              </div>
              <div className="space-y-2">
                {lateOn.map((a) => (
                  <Link
                    key={a.artist_id}
                    href={`/artist/${a.artist_id}`}
                    className="card-hover flex items-center gap-4 px-4 py-3 animate-slide-up"
                  >
                    {a.image_url ? (
                      <img src={a.image_url} alt="" className="w-12 h-12 rounded-full object-cover" />
                    ) : (
                      <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center text-lg text-gray-600">
                        {a.artist_name?.[0]}
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <span className="font-bold block">{a.artist_name}</span>
                      <span className="text-xs text-gray-600">
                        {a.genres?.join(", ")}
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="text-orange-400 text-sm font-bold block">
                        {a.friend_count} friends
                      </span>
                      <span className="text-gray-600 text-xs">already listen</span>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {/* Friends' Fresh Finds */}
          {freshFinds.length > 0 && (
            <section className="mb-10">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-2xl">✨</span>
                <div>
                  <h2 className="text-lg font-black text-[var(--green)]">Friends&apos; Fresh Finds</h2>
                  <p className="text-gray-600 text-xs">What your friends have been listening to this week</p>
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {freshFinds.slice(0, 8).map((a) => (
                  <Link
                    key={a.artist_id}
                    href={`/artist/${a.artist_id}`}
                    className="card-hover group p-4 flex flex-col items-center text-center animate-slide-up"
                  >
                    {a.image_url ? (
                      <img
                        src={a.image_url}
                        alt=""
                        className="w-20 h-20 rounded-full object-cover mb-3 ring-2 ring-transparent group-hover:ring-[var(--green)] transition-all"
                      />
                    ) : (
                      <div className="w-20 h-20 rounded-full bg-white/5 mb-3 flex items-center justify-center text-2xl text-gray-600">
                        {a.artist_name?.[0]}
                      </div>
                    )}
                    <span className="font-bold text-sm truncate w-full">{a.artist_name}</span>
                    <span className="text-[var(--green)] text-xs mt-1">
                      {a.friend_count} {a.friend_count === 1 ? "friend" : "friends"} listening
                    </span>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {/* Rising on Gatekeepify */}
          {rising.length > 0 && (
            <section className="mb-10">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-2xl">📈</span>
                <div>
                  <h2 className="text-lg font-black text-purple-400">Rising on Gatekeepify</h2>
                  <p className="text-gray-600 text-xs">Artists gaining listeners on the platform</p>
                </div>
              </div>
              <div className="space-y-2">
                {rising.map((a, i) => (
                  <Link
                    key={a.artist_id}
                    href={`/artist/${a.artist_id}`}
                    className="card-hover flex items-center gap-4 px-4 py-3 animate-slide-up"
                  >
                    <span className={`font-mono text-sm w-6 text-right ${
                      i === 0 ? "text-purple-400" : "text-gray-600"
                    }`}>
                      {i + 1}
                    </span>
                    {a.image_url ? (
                      <img src={a.image_url} alt="" className="w-10 h-10 rounded-full object-cover" />
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-sm text-gray-600">
                        {a.artist_name?.[0]}
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <span className="font-medium text-sm block">{a.artist_name}</span>
                    </div>
                    <div className="text-right">
                      <span className="text-purple-400 text-sm font-bold">
                        +{a.new_listeners} new
                      </span>
                      {a.you_listen && (
                        <span className="text-[var(--green)] text-xs block">you listen ✓</span>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
