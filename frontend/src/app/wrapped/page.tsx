"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";
import { trackEvent } from "@/lib/track";
import Link from "next/link";

export default function Wrapped() {
  const router = useRouter();
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/");
      return;
    }
    setLoading(true);
    api.getWrapped(year).then((d) => {
      setData(d);
      setLoading(false);
    });
  }, [year, router]);

  const years = Array.from({ length: 5 }, (_, i) => currentYear - i);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-gray-500 animate-pulse text-lg">
          Generating your Wrapped...
        </div>
      </div>
    );
  }

  const isEmpty =
    !data ||
    (data.top_artists?.length === 0 && data.top_tracks?.length === 0);

  return (
    <div className="animate-fade-in max-w-2xl mx-auto">
      {/* Year selector */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-10">
        <div>
          <h1 className="text-4xl font-black">
            Your <span className="gradient-text">Wrapped</span>
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            {year === currentYear
              ? "Predicted based on your listening so far"
              : `Your ${year} in review`}
          </p>
        </div>
        <div className="flex gap-1 bg-white/5 rounded-full p-1">
          {years.map((y) => (
            <button
              key={y}
              onClick={() => { setYear(y); trackEvent("wrapped_year_changed", { year: y }); }}
              className={`px-3 py-1.5 rounded-full text-xs transition-all ${
                year === y
                  ? "bg-[var(--green)] text-black font-bold"
                  : "text-gray-500 hover:text-white"
              }`}
            >
              {y}
            </button>
          ))}
        </div>
      </div>

      {isEmpty ? (
        <div className="card p-12 text-center">
          <span className="text-5xl mb-4 block">🎵</span>
          <p className="text-gray-400 text-lg mb-2">No data for {year}</p>
          <p className="text-gray-600 text-sm">
            Upload your Spotify data export to see past years.
          </p>
        </div>
      ) : (
        <div className="space-y-8">
          {data.data_period && (
            <p className="text-center text-gray-600 text-xs -mb-4">
              Based on {data.data_period}
            </p>
          )}

          {/* Total minutes */}
          <div className="card p-8 text-center bg-gradient-to-br from-[var(--green-dim)] to-transparent border-[var(--green)]/10">
            <div className="text-gray-400 text-sm uppercase tracking-widest mb-2">
              Minutes Listened
            </div>
            <div className="text-7xl font-black gradient-text">
              {data.total_minutes.toLocaleString()}
            </div>
            <div className="text-gray-600 text-sm mt-2">
              That&apos;s {Math.round(data.total_minutes / 60).toLocaleString()} hours
              {data.total_minutes > 1440 &&
                ` or ${Math.round(data.total_minutes / 1440).toLocaleString()} days`}
            </div>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-3 gap-3">
            <div className="card p-4 text-center">
              <div className="text-2xl font-black">{(data.total_listens || 0).toLocaleString()}</div>
              <div className="text-gray-600 text-xs">total listens</div>
            </div>
            <div className="card p-4 text-center">
              <div className="text-2xl font-black">{(data.unique_artists || 0).toLocaleString()}</div>
              <div className="text-gray-600 text-xs">artists</div>
            </div>
            <div className="card p-4 text-center">
              <div className="text-2xl font-black">{(data.unique_tracks || 0).toLocaleString()}</div>
              <div className="text-gray-600 text-xs">tracks</div>
            </div>
          </div>

          {/* Top Artists */}
          {data.top_artists?.length > 0 && (
            <div>
              <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-4">
                Your Top Artists
              </h2>
              <div className="space-y-3">
                {data.top_artists.map((a: any, i: number) => (
                  <Link
                    key={a.artist_id}
                    href={`/artist/${a.artist_id}`}
                    className="card-hover flex items-center gap-4 p-4 animate-slide-up"
                    style={{ animationDelay: `${i * 0.1}s` }}
                  >
                    <span
                      className={`text-3xl font-black w-10 text-center ${
                        i === 0
                          ? "gradient-text"
                          : "text-gray-600"
                      }`}
                    >
                      {i + 1}
                    </span>
                    {a.image_url ? (
                      <img
                        src={a.image_url}
                        alt=""
                        className="w-14 h-14 rounded-full object-cover ring-1 ring-white/10"
                      />
                    ) : (
                      <div className="w-14 h-14 rounded-full bg-white/5 flex items-center justify-center text-xl text-gray-600">
                        {a.artist_name?.[0]}
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="font-bold text-lg truncate">
                        {a.artist_name}
                      </div>
                      <div className="text-xs text-gray-600">
                        {a.genres?.slice(0, 2).join(", ")}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-bold">{a.listen_count}</div>
                      <div className="text-xs text-gray-600">plays</div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Top Tracks */}
          {data.top_tracks?.length > 0 && (
            <div>
              <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-4">
                Your Top Tracks
              </h2>
              <div className="space-y-3">
                {data.top_tracks.map((t: any, i: number) => (
                  <div
                    key={t.track_id}
                    className="card flex items-center gap-4 p-4 animate-slide-up"
                    style={{ animationDelay: `${i * 0.1}s` }}
                  >
                    <span
                      className={`text-3xl font-black w-10 text-center ${
                        i === 0
                          ? "gradient-text"
                          : "text-gray-600"
                      }`}
                    >
                      {i + 1}
                    </span>
                    {t.image_url ? (
                      <img
                        src={t.image_url}
                        alt=""
                        className="w-14 h-14 rounded-lg object-cover ring-1 ring-white/10"
                      />
                    ) : (
                      <div className="w-14 h-14 rounded-lg bg-white/5" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="font-bold truncate">{t.track_name}</div>
                      <div className="text-xs text-gray-600 truncate">
                        {t.album_name}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-bold">{t.listen_count}</div>
                      <div className="text-xs text-gray-600">plays</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Genres */}
          {data.top_genres?.length > 0 ? (
            <div>
              <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-4">
                Your Top Genres
              </h2>
              <div className="flex gap-2 flex-wrap">
                {data.top_genres.map((g: any, i: number) => (
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
            </div>
          ) : data.top_genre && (
            <div className="card p-8 text-center">
              <div className="text-gray-400 text-sm uppercase tracking-widest mb-2">
                Top Genre
              </div>
              <div className="text-4xl font-black">{data.top_genre}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
