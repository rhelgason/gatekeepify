"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";
import { trackEvent } from "@/lib/track";
import Link from "next/link";

export default function Feed() {
  const router = useRouter();
  const [feed, setFeed] = useState<any[]>([]);
  const [freshFinds, setFreshFinds] = useState<any[]>([]);
  const [lateOn, setLateOn] = useState<any[]>([]);
  const [rising, setRising] = useState<any[]>([]);
  const [feedDays, setFeedDays] = useState(7);
  const [feedLoading, setFeedLoading] = useState(false);
  const [feedHasMore, setFeedHasMore] = useState(true);
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
      api.getActivityFeed().catch(() => []),
    ]).then(([ff, lo, r, f]) => {
      setFreshFinds(ff);
      setLateOn(lo);
      setRising(r);
      setFeed(f);
      setLoading(false);
    });
  }, [router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-gray-500 animate-pulse text-lg">Loading feed...</div>
      </div>
    );
  }

  const hasDiscover = freshFinds.length > 0 || lateOn.length > 0 || rising.length > 0;
  const isEmpty = !hasDiscover && feed.length === 0;

  if (isEmpty) {
    return (
      <div className="animate-fade-in max-w-2xl mx-auto">
        <h1 className="text-3xl font-black mb-2">Feed</h1>
        <p className="text-gray-500 mb-8">What&apos;s happening in your circle.</p>
        <div className="card p-12 text-center">
          <span className="text-5xl mb-4 block">📢</span>
          <p className="text-gray-400 text-lg mb-2">Nothing here yet</p>
          <p className="text-gray-600 text-sm">
            Keep listening and add friends. Recommendations and activity appear as your network grows.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <h1 className="text-3xl font-black mb-2">Feed</h1>
      <p className="text-gray-500 mb-8">What&apos;s happening in your circle.</p>

      <div className={`${hasDiscover ? "grid grid-cols-1 lg:grid-cols-2 gap-8" : ""}`}>
        {/* ===== DISCOVER COLUMN ===== */}
        {hasDiscover && (
          <div className="space-y-6">
            <h2 className="text-xs font-bold uppercase tracking-widest text-gray-600">Discover</h2>

            {/* You're Late On */}
            {lateOn.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-lg">⚠️</span>
                  <h3 className="text-sm font-black text-orange-400">You&apos;re Late On...</h3>
                </div>
                <div className="space-y-2">
                  {lateOn.slice(0, 5).map((a) => (
                    <Link
                      key={a.artist_id}
                      href={`/artist/${a.artist_id}`}
                      className="card-hover flex items-center gap-3 px-3 py-2.5 animate-slide-up"
                    >
                      {a.image_url ? (
                        <img src={a.image_url} alt="" className="w-10 h-10 rounded-full object-cover" />
                      ) : (
                        <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-sm text-gray-600">
                          {a.artist_name?.[0]}
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <span className="font-bold text-sm block truncate">{a.artist_name}</span>
                        <span className="text-xs text-gray-600 truncate block">
                          {a.genres?.join(", ")}
                        </span>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <span className="text-orange-400 text-xs font-bold block">
                          {a.friend_count} friends
                        </span>
                      </div>
                    </Link>
                  ))}
                </div>
              </section>
            )}

            {/* Friends' Fresh Finds */}
            {freshFinds.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-lg">✨</span>
                  <h3 className="text-sm font-black text-[var(--green)]">Friends&apos; Fresh Finds</h3>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {freshFinds.slice(0, 6).map((a) => (
                    <Link
                      key={a.artist_id}
                      href={`/artist/${a.artist_id}`}
                      className="card-hover group p-3 flex flex-col items-center text-center animate-slide-up"
                    >
                      {a.image_url ? (
                        <img
                          src={a.image_url}
                          alt=""
                          className="w-14 h-14 rounded-full object-cover mb-2 ring-2 ring-transparent group-hover:ring-[var(--green)] transition-all"
                        />
                      ) : (
                        <div className="w-14 h-14 rounded-full bg-white/5 mb-2 flex items-center justify-center text-lg text-gray-600">
                          {a.artist_name?.[0]}
                        </div>
                      )}
                      <span className="font-bold text-xs truncate w-full">{a.artist_name}</span>
                      <span className="text-[var(--green)] text-[10px] mt-0.5">
                        {a.friend_count} {a.friend_count === 1 ? "friend" : "friends"}
                      </span>
                    </Link>
                  ))}
                </div>
              </section>
            )}

            {/* Rising on Gatekeepify */}
            {rising.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-lg">📈</span>
                  <h3 className="text-sm font-black text-purple-400">Rising on Gatekeepify</h3>
                </div>
                <div className="space-y-2">
                  {rising.slice(0, 5).map((a, i) => (
                    <Link
                      key={a.artist_id}
                      href={`/artist/${a.artist_id}`}
                      className="card-hover flex items-center gap-3 px-3 py-2.5 animate-slide-up"
                    >
                      <span className={`font-mono text-xs w-5 text-right ${
                        i === 0 ? "text-purple-400" : "text-gray-600"
                      }`}>
                        {i + 1}
                      </span>
                      {a.image_url ? (
                        <img src={a.image_url} alt="" className="w-8 h-8 rounded-full object-cover" />
                      ) : (
                        <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-xs text-gray-600">
                          {a.artist_name?.[0]}
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <span className="font-medium text-sm block truncate">{a.artist_name}</span>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <span className="text-purple-400 text-xs font-bold">
                          +{a.new_listeners}
                        </span>
                        {a.you_listen && (
                          <span className="text-[var(--green)] text-[10px] block">✓</span>
                        )}
                      </div>
                    </Link>
                  ))}
                </div>
              </section>
            )}
          </div>
        )}

        {/* ===== ACTIVITY COLUMN ===== */}
        <div>
          {hasDiscover && (
            <h2 className="text-xs font-bold uppercase tracking-widest text-gray-600 mb-6 lg:mb-0 lg:mt-0 mt-2">Activity</h2>
          )}

          {feed.length === 0 ? (
            <div className="card p-8 text-center mt-4">
              <span className="text-3xl mb-3 block">📢</span>
              <p className="text-gray-400 text-sm">No recent activity</p>
              <p className="text-gray-600 text-xs mt-1">
                Events appear as you and your friends listen.
              </p>
            </div>
          ) : (
            <>
              <div className="space-y-3 mt-4">
                {feed.map((event, i) => (
                  <Link
                    key={`${event.type}-${event.user_id}-${event.ts}-${i}`}
                    href={event.artist_id ? `/artist/${event.artist_id}` : event.type === "data_uploaded" ? "/upload" : "/feed"}
                    className="card-hover p-4 block animate-slide-up"
                    style={{ animationDelay: `${i * 0.03}s` }}
                  >
                    <div className="flex items-start gap-3">
                      <span className="text-xl flex-shrink-0 mt-0.5">{event.emoji}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-200 leading-relaxed">
                          {event.message}
                        </p>
                        <div className="flex items-center gap-3 mt-2">
                          <span className="text-xs text-gray-600">
                            {new Date(event.ts).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                          </span>
                          {event.stat && (
                            <span className="text-xs text-gray-500">{event.stat}</span>
                          )}
                          {event.artist_name && (
                            <span className="text-xs text-[var(--green)]">{event.artist_name}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>

              {feedHasMore && (
                <button
                  onClick={async () => {
                    setFeedLoading(true);
                    trackEvent("feed_load_more", { days: feedDays + 14 });
                    const newDays = feedDays + 14;
                    const more = await api.getActivityFeed(50, newDays).catch(() => []);
                    setFeed(more);
                    setFeedDays(newDays);
                    setFeedHasMore(more.length > feed.length);
                    setFeedLoading(false);
                  }}
                  disabled={feedLoading}
                  className="btn-secondary w-full mt-4 text-sm"
                >
                  {feedLoading ? "Loading..." : "Load more"}
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
