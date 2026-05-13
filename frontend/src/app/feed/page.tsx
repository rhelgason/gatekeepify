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
  const [feedDays, setFeedDays] = useState(7);
  const [feedLoading, setFeedLoading] = useState(false);
  const [feedHasMore, setFeedHasMore] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/");
      return;
    }
    api.getActivityFeed().then((f) => {
      setFeed(f);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-gray-500 animate-pulse text-lg">Loading feed...</div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in max-w-2xl mx-auto">
      <h1 className="text-3xl font-black mb-2">Activity</h1>
      <p className="text-gray-500 mb-8">
        What&apos;s happening in your circle.
      </p>

      {feed.length === 0 ? (
        <div className="card p-12 text-center">
          <span className="text-5xl mb-4 block">📢</span>
          <p className="text-gray-400 text-lg mb-2">No activity yet</p>
          <p className="text-gray-600 text-sm">
            Keep listening and add friends. Events appear as you and your friends use the app.
          </p>
        </div>
      ) : (
        <>
          <div className="space-y-3">
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
  );
}
