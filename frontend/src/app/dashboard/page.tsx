"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";
import { trackEvent } from "@/lib/track";
import ShareButton from "@/components/ShareButton";
import Link from "next/link";

type Period = "all" | "year" | "month" | "today";
type ViewMode = "recent" | "wrapped";

function DashboardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialView = searchParams.get("view") === "wrapped" ? "wrapped" : "recent";

  const [viewMode, setViewMode] = useState<ViewMode>(initialView);
  const [period, setPeriod] = useState<Period>("all");
  const [tracks, setTracks] = useState<any[]>([]);
  const [artists, setArtists] = useState<any[]>([]);
  const [genres, setGenres] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const [wrappedData, setWrappedData] = useState<any>(null);
  const [wrappedLoading, setWrappedLoading] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/");
      return;
    }
    if (viewMode === "recent") {
      let cancelled = false;
      setLoading(true);
      Promise.all([
        api.getTopTracks(period),
        api.getTopArtists(period),
        api.getTopGenres(period, 5),
      ]).then(([t, a, g]) => {
        if (!cancelled) { setTracks(t); setArtists(a); setGenres(g); }
      }).catch(() => {}).finally(() => { if (!cancelled) setLoading(false); });
      return () => { cancelled = true; };
    }
  }, [period, router, viewMode]);

  useEffect(() => {
    if (!isLoggedIn() || viewMode !== "wrapped") return;
    setWrappedLoading(true);
    api.getWrapped(year)
      .then((d) => setWrappedData(d))
      .catch(() => setWrappedData(null))
      .finally(() => setWrappedLoading(false));
  }, [year, viewMode]);

  const periods: { value: Period; label: string }[] = [
    { value: "today", label: "Last 24 Hours" },
    { value: "month", label: "30 Days" },
    { value: "year", label: "Year" },
    { value: "all", label: "All Time" },
  ];

  const years = Array.from({ length: 5 }, (_, i) => currentYear - i);

  const isLoading = viewMode === "recent" ? loading : wrappedLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-gray-500 animate-pulse text-lg">
          {viewMode === "wrapped" ? "Generating your Wrapped..." : "Loading your stats..."}
        </div>
      </div>
    );
  }

  const recentEmpty =
    viewMode === "recent" && tracks.length === 0 && artists.length === 0 && genres.length === 0;

  if (recentEmpty) {
    const periodLabel = periods.find((p) => p.value === period)?.label ?? "this period";
    const isDefaultPeriod = period === "today";
    return (
      <div className="animate-fade-in">
        {/* View mode toggle */}
        <div className="flex justify-center mb-6">
          <div className="flex gap-1 bg-white/5 rounded-full p-1">
            <button
              onClick={() => { setViewMode("recent"); trackEvent("view_mode_changed", { mode: "recent" }); }}
              className="px-4 py-1.5 rounded-full text-sm transition-all duration-200 bg-[var(--green)] text-black font-bold"
            >
              Recent
            </button>
            <button
              onClick={() => { setViewMode("wrapped"); trackEvent("view_mode_changed", { mode: "wrapped" }); }}
              className="px-4 py-1.5 rounded-full text-sm transition-all duration-200 text-gray-500 hover:text-white"
            >
              Wrapped
            </button>
          </div>
        </div>

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

        <div className="max-w-lg mx-auto text-center mt-12">
          <svg className="w-12 h-12 mx-auto mb-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 11-.99-3.467l2.31-.66a2.25 2.25 0 001.632-2.163zm0 0V4.228c0-.89-.922-1.48-1.735-1.11L6.286 5.526a1.886 1.886 0 00-1.036 1.684v3.04M5.25 21A2.25 2.25 0 013 18.75v0A2.25 2.25 0 015.25 16.5h0A2.25 2.25 0 017.5 18.75v0A2.25 2.25 0 015.25 21z" /></svg>
          <h2 className="text-2xl font-bold mb-2">
            {isDefaultPeriod ? "Nothing in the last 24 hours" : `No listens for ${periodLabel}`}
          </h2>
          <p className="text-gray-400 mb-8">
            {isDefaultPeriod
              ? "Play something on Spotify and check back soon — we poll every 15 minutes."
              : "Try switching to a different time period above."}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Link href="/upload" className="card p-5 text-center hover:border-white/10 transition-all">
              <svg className="w-6 h-6 mx-auto mb-2 text-[var(--green)]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" /></svg>
              <h3 className="font-bold text-[var(--green)] text-sm mb-1">Upload History</h3>
              <p className="text-gray-500 text-xs">Import your full Spotify data export</p>
            </Link>
            <Link href="/friends" className="card p-5 text-center hover:border-white/10 transition-all">
              <svg className="w-6 h-6 mx-auto mb-2 text-[var(--green)]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" /></svg>
              <h3 className="font-bold text-[var(--green)] text-sm mb-1">Add Friends</h3>
              <p className="text-gray-500 text-xs">See who listened first</p>
            </Link>
            <Link href="/feed" className="card p-5 text-center hover:border-white/10 transition-all">
              <svg className="w-6 h-6 mx-auto mb-2 text-[var(--green)]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" /></svg>
              <h3 className="font-bold text-[var(--green)] text-sm mb-1">Activity Feed</h3>
              <p className="text-gray-500 text-xs">See what friends are playing</p>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const wrappedEmpty = viewMode === "wrapped" && (!wrappedData || (wrappedData.top_artists?.length === 0 && wrappedData.top_tracks?.length === 0));

  return (
    <div className="animate-fade-in">
      {/* View mode toggle */}
      <div className="flex justify-center mb-6">
        <div className="flex gap-1 bg-white/5 rounded-full p-1">
          <button
            onClick={() => { setViewMode("recent"); trackEvent("view_mode_changed", { mode: "recent" }); }}
            className={`px-4 py-1.5 rounded-full text-sm transition-all duration-200 ${
              viewMode === "recent"
                ? "bg-[var(--green)] text-black font-bold"
                : "text-gray-500 hover:text-white"
            }`}
          >
            Recent
          </button>
          <button
            onClick={() => { setViewMode("wrapped"); trackEvent("view_mode_changed", { mode: "wrapped" }); }}
            className={`px-4 py-1.5 rounded-full text-sm transition-all duration-200 ${
              viewMode === "wrapped"
                ? "bg-[var(--green)] text-black font-bold"
                : "text-gray-500 hover:text-white"
            }`}
          >
            Wrapped
          </button>
        </div>
      </div>

      {viewMode === "recent" ? (
        /* ===== RECENT STATS ===== */
        <>
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
        </>
      ) : (
        /* ===== WRAPPED ===== */
        <div className="max-w-2xl mx-auto">
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

          {wrappedEmpty ? (
            <div className="card p-12 text-center">
              <svg className="w-12 h-12 mx-auto mb-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 11-.99-3.467l2.31-.66a2.25 2.25 0 001.632-2.163zm0 0V4.228c0-.89-.922-1.48-1.735-1.11L6.286 5.526a1.886 1.886 0 00-1.036 1.684v3.04M5.25 21A2.25 2.25 0 013 18.75v0A2.25 2.25 0 015.25 16.5h0A2.25 2.25 0 017.5 18.75v0A2.25 2.25 0 015.25 21z" /></svg>
              <p className="text-gray-400 text-lg mb-2">No data for {year}</p>
              <p className="text-gray-600 text-sm">
                Upload your Spotify data export to see past years.
              </p>
            </div>
          ) : wrappedData && (
            <div className="space-y-8">
              {wrappedData.data_period && (
                <p className="text-center text-gray-600 text-xs -mb-4">
                  Based on {wrappedData.data_period}
                </p>
              )}

              <div className="card p-8 text-center bg-gradient-to-br from-[var(--green-dim)] to-transparent border-[var(--green)]/10 relative">
                <div className="absolute top-4 right-4">
                  <ShareButton
                    cardData={{
                      artistName: wrappedData.top_artists?.[0]?.artist_name || "Your Year",
                      imageUrl: wrappedData.top_artists?.[0]?.image_url,
                      statNumber: (wrappedData.total_minutes ?? 0).toLocaleString(),
                      statLabel: "minutes listened",
                      contextLine: `${year} Wrapped`,
                      secondaryStat: `${(wrappedData.unique_artists || 0).toLocaleString()} artists · ${(wrappedData.unique_tracks || 0).toLocaleString()} tracks`,
                    }}
                    surface="wrapped"
                  />
                </div>
                <div className="text-gray-400 text-sm uppercase tracking-widest mb-2">
                  Minutes Listened
                </div>
                <div className="text-7xl font-black gradient-text">
                  {(wrappedData.total_minutes ?? 0).toLocaleString()}
                </div>
                <div className="text-gray-600 text-sm mt-2">
                  That&apos;s {Math.round((wrappedData.total_minutes ?? 0) / 60).toLocaleString()} hours
                  {(wrappedData.total_minutes ?? 0) > 1440 &&
                    ` or ${Math.round((wrappedData.total_minutes ?? 0) / 1440).toLocaleString()} days`}
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="card p-4 text-center">
                  <div className="text-2xl font-black">{(wrappedData.total_listens || 0).toLocaleString()}</div>
                  <div className="text-gray-600 text-xs">total listens</div>
                </div>
                <div className="card p-4 text-center">
                  <div className="text-2xl font-black">{(wrappedData.unique_artists || 0).toLocaleString()}</div>
                  <div className="text-gray-600 text-xs">artists</div>
                </div>
                <div className="card p-4 text-center">
                  <div className="text-2xl font-black">{(wrappedData.unique_tracks || 0).toLocaleString()}</div>
                  <div className="text-gray-600 text-xs">tracks</div>
                </div>
              </div>

              {wrappedData.top_artists?.length > 0 && (
                <div>
                  <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-4">
                    Your Top Artists
                  </h2>
                  <div className="space-y-3">
                    {wrappedData.top_artists.map((a: any, i: number) => (
                      <Link
                        key={a.artist_id}
                        href={`/artist/${a.artist_id}`}
                        className="card-hover flex items-center gap-4 p-4 animate-slide-up"
                        style={{ animationDelay: `${i * 0.1}s` }}
                      >
                        <span
                          className={`text-3xl font-black w-10 text-center ${
                            i === 0 ? "gradient-text" : "text-gray-600"
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

              {wrappedData.top_tracks?.length > 0 && (
                <div>
                  <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-4">
                    Your Top Tracks
                  </h2>
                  <div className="space-y-3">
                    {wrappedData.top_tracks.map((t: any, i: number) => (
                      <div
                        key={t.track_id}
                        className="card flex items-center gap-4 p-4 animate-slide-up"
                        style={{ animationDelay: `${i * 0.1}s` }}
                      >
                        <span
                          className={`text-3xl font-black w-10 text-center ${
                            i === 0 ? "gradient-text" : "text-gray-600"
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

              {wrappedData.top_genres?.length > 0 ? (
                <div>
                  <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-4">
                    Your Top Genres
                  </h2>
                  <div className="flex gap-2 flex-wrap">
                    {wrappedData.top_genres.map((g: any, i: number) => (
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
              ) : wrappedData.top_genre && (
                <div className="card p-8 text-center">
                  <div className="text-gray-400 text-sm uppercase tracking-widest mb-2">
                    Top Genre
                  </div>
                  <div className="text-4xl font-black">{wrappedData.top_genre}</div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function Dashboard() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-gray-500 animate-pulse text-lg">Loading your stats...</div>
      </div>
    }>
      <DashboardContent />
    </Suspense>
  );
}
