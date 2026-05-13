"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";
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
    { value: "today", label: "Today" },
    { value: "month", label: "Last 30 Days" },
    { value: "year", label: "Last Year" },
    { value: "all", label: "All Time" },
  ];

  if (loading) {
    return <p className="text-gray-400 mt-12 text-center">Loading stats...</p>;
  }

  const isEmpty = tracks.length === 0 && artists.length === 0 && genres.length === 0;

  if (isEmpty) {
    return (
      <div className="mt-12 max-w-lg mx-auto text-center">
        <h1 className="text-2xl font-bold mb-4">Welcome to Gatekeepify</h1>
        <p className="text-gray-400 mb-6">
          We&apos;re collecting your listening data now. Your recent Spotify
          history will appear here within 15 minutes.
        </p>
        <div className="bg-gray-900 rounded-lg p-6 text-left space-y-4">
          <div>
            <h2 className="font-semibold text-green-400 mb-1">
              Want your full history?
            </h2>
            <p className="text-gray-400 text-sm">
              Spotify&apos;s API only gives us your last 50 listens. To see
              years of data, upload your Spotify data export.
            </p>
            <Link
              href="/upload"
              className="inline-block mt-2 text-sm text-green-400 hover:text-green-300"
            >
              Upload your data &rarr;
            </Link>
          </div>
          <div>
            <h2 className="font-semibold text-green-400 mb-1">
              Invite your friends
            </h2>
            <p className="text-gray-400 text-sm">
              Gatekeeping is a team sport. Add friends to compare who listened
              first.
            </p>
            <Link
              href="/friends"
              className="inline-block mt-2 text-sm text-green-400 hover:text-green-300"
            >
              Manage friends &rarr;
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Your Stats</h1>
        <div className="flex gap-2">
          {periods.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`px-3 py-1 rounded text-sm ${
                period === p.value
                  ? "bg-green-500 text-black"
                  : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <section>
          <h2 className="text-lg font-semibold mb-3 text-green-400">
            Top Tracks
          </h2>
          {tracks.length === 0 ? (
            <p className="text-gray-500 text-sm">No data yet</p>
          ) : (
            <div className="space-y-2">
              {tracks.map((t) => (
                <div
                  key={t.track_id}
                  className="flex justify-between bg-gray-900 rounded px-3 py-2"
                >
                  <div>
                    <span className="text-gray-500 text-sm mr-2">
                      {t.rank}.
                    </span>
                    <span>{t.track_name || "Unknown"}</span>
                    <span className="text-gray-500 text-sm ml-2">
                      {t.album_name}
                    </span>
                  </div>
                  <span className="text-gray-400 text-sm">
                    {t.listen_count} plays
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>

        <section>
          <h2 className="text-lg font-semibold mb-3 text-green-400">
            Top Artists
          </h2>
          {artists.length === 0 ? (
            <p className="text-gray-500 text-sm">No data yet</p>
          ) : (
            <div className="space-y-2">
              {artists.map((a) => (
                <Link
                  key={a.artist_id}
                  href={`/gatekeep?artist=${a.artist_id}`}
                  className="flex justify-between bg-gray-900 rounded px-3 py-2 hover:bg-gray-800 transition"
                >
                  <div>
                    <span className="text-gray-500 text-sm mr-2">
                      {a.rank}.
                    </span>
                    <span>{a.artist_name}</span>
                    <span className="text-gray-600 text-sm ml-2">
                      {a.genres?.slice(0, 2).join(", ")}
                    </span>
                  </div>
                  <span className="text-gray-400 text-sm">
                    {a.listen_count} plays
                  </span>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>

      {genres.length > 0 && (
        <section className="mt-6">
          <h2 className="text-lg font-semibold mb-3 text-green-400">
            Top Genres
          </h2>
          <div className="flex gap-3 flex-wrap">
            {genres.map((g) => (
              <span
                key={g.genre}
                className="bg-gray-900 px-3 py-1 rounded-full text-sm"
              >
                {g.genre}{" "}
                <span className="text-gray-500">{g.listen_count}</span>
              </span>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
