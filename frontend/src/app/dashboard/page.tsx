"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";
import { trackEvent } from "@/lib/track";
import Link from "next/link";

type Period = "all" | "year" | "month" | "today";

export default function Dashboard() {
  const router = useRouter();
  const [period, setPeriod] = useState<Period>("all");
  const [tracks, setTracks] = useState<any[]>([]);
  const [artists, setArtists] = useState<any[]>([]);
  const [genres, setGenres] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/");
      return;
    }
    setLoading(true);
    Promise.all([
      api.getTopTracks(period),
      api.getTopArtists(period),
      api.getTopGenres(period, 5),
    ]).then(([t, a, g]) => {
      setTracks(t);
      setArtists(a);
      setGenres(g);
      setLoading(false);
    });
  }, [period, router]);

  const periods: { value: Period; label: string }[] = [
    { value: "today", label: "Today (UTC)" },
    { value: "month", label: "30 Days" },
    { value: "year", label: "Year" },
    { value: "all", label: "All Time" },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-gray-500 animate-pulse text-lg">Loading your stats...</div>
      </div>
    );
  }

  const isEmpty =
    tracks.length === 0 && artists.length === 0 && genres.length === 0;

  if (isEmpty) {
    return (
      <div className="mt-16 max-w-lg mx-auto text-center animate-fade-in">
        <h1 className="text-4xl font-black mb-4">Welcome to Gatekeepify</h1>
        <p className="text-gray-400 mb-8 text-lg">
          We&apos;re collecting your listening data now. Your recent history
          will appear here within 15 minutes.
        </p>
        <div className="space-y-4">
          <Link href="/upload" className="card block p-6 text-left hover:border-white/10 transition-all">
            <h2 className="font-bold text-[var(--green)] mb-1 text-lg">
              Upload your full history
            </h2>
            <p className="text-gray-500 text-sm">
              Spotify&apos;s API only gives us your last 50 listens. Upload your data
              export for years of history.
            </p>
          </Link>
          <Link href="/friends" className="card block p-6 text-left hover:border-white/10 transition-all">
            <h2 className="font-bold text-[var(--green)] mb-1 text-lg">
              Invite your friends
            </h2>
            <p className="text-gray-500 text-sm">
              Gatekeeping is a team sport. Add friends to see who listened first.
            </p>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-8">
        <h1 className="text-3xl font-black">Your Stats</h1>
        <div className="flex gap-1 bg-white/5 rounded-full p-1">
          {periods.map((p) => (
            <button
              key={p.value}
              onClick={() => { setPeriod(p.value); trackEvent("period_changed", { period: p.value }); }}
              className={`px-3 md:px-4 py-1.5 rounded-full text-xs md:text-sm transition-all duration-200 ${
                period === p.value
                  ? "bg-[var(--green)] text-black font-bold"
                  : "text-gray-500 hover:text-white"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Top Artists - large cards */}
      {artists.length > 0 && (
        <section className="mb-10">
          <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-4">
            Top Artists
          </h2>
          <div className="grid grid-cols-3 md:grid-cols-5 gap-2 md:gap-3">
            {artists.slice(0, 5).map((a) => (
              <Link
                key={a.artist_id}
                href={`/artist/${a.artist_id}`}
                className="card-hover group p-4 flex flex-col items-center text-center"
              >
                {a.image_url ? (
                  <img
                    src={a.image_url}
                    alt={a.artist_name}
                    className="w-16 h-16 md:w-24 md:h-24 rounded-full object-cover mb-2 md:mb-3 ring-2 ring-transparent group-hover:ring-[var(--green)] transition-all duration-200"
                  />
                ) : (
                  <div className="w-16 h-16 md:w-24 md:h-24 rounded-full bg-white/5 mb-2 md:mb-3 flex items-center justify-center text-xl md:text-3xl text-gray-600">
                    {a.artist_name?.[0] || "?"}
                  </div>
                )}
                <span className="font-bold text-xs md:text-sm truncate w-full">
                  {a.artist_name}
                </span>
                <span className="text-[10px] md:text-xs text-gray-500 mt-1">
                  {a.listen_count} plays
                </span>
              </Link>
            ))}
          </div>
          {artists.length > 5 && (
            <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
              {artists.slice(5).map((a) => (
                <Link
                  key={a.artist_id}
                  href={`/artist/${a.artist_id}`}
                  className="card-hover flex items-center gap-3 px-4 py-3"
                >
                  {a.image_url ? (
                    <img src={a.image_url} alt="" className="w-10 h-10 rounded-full object-cover" />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-sm text-gray-600">
                      {a.artist_name?.[0]}
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium truncate block">{a.artist_name}</span>
                    <span className="text-xs text-gray-600">
                      {a.genres?.slice(0, 2).join(", ")}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500">{a.listen_count} plays</span>
                </Link>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Top Tracks */}
      {tracks.length > 0 && (
        <section className="mb-10">
          <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-4">
            Top Tracks
          </h2>
          <div className="space-y-1">
            {tracks.map((t) => (
              <div
                key={t.track_id}
                className="card-hover flex items-center gap-4 px-4 py-3"
              >
                <span className="text-gray-600 font-mono text-sm w-6 text-right">
                  {t.rank}
                </span>
                {t.image_url ? (
                  <img src={t.image_url} alt="" className="w-10 h-10 rounded object-cover" />
                ) : (
                  <div className="w-10 h-10 rounded bg-white/5" />
                )}
                <div className="flex-1 min-w-0">
                  <span className="font-medium truncate block text-sm">
                    {t.track_name || "Unknown"}
                  </span>
                  <span className="text-xs text-gray-600 truncate block">
                    {t.album_name}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-sm text-gray-400">
                    {t.listen_count} plays
                  </span>
                  <span className="text-xs text-gray-600 block">
                    {t.total_minutes} min
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Top Genres */}
      {genres.length > 0 && (
        <section>
          <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-4">
            Top Genres
          </h2>
          <div className="flex gap-2 flex-wrap">
            {genres.map((g, i) => (
              <span
                key={g.genre}
                className={`card px-5 py-2.5 rounded-full text-sm font-medium ${
                  i === 0 ? "bg-[var(--green-dim)] text-[var(--green)] border-[var(--green)]/20" : ""
                }`}
              >
                {g.genre}
                <span className="text-gray-500 ml-2">{g.listen_count}</span>
              </span>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
