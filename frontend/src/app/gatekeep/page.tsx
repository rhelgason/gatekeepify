"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";
import { trackEvent } from "@/lib/track";
import Link from "next/link";

function GatekeepContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselected = searchParams.get("artist");
  const prefillQuery = searchParams.get("q");

  const [query, setQuery] = useState(prefillQuery || "");
  const [results, setResults] = useState<any[]>([]);
  const [spotifyResults, setSpotifyResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/");
  }, [router]);

  useEffect(() => {
    if (preselected) router.replace(`/artist/${preselected}`);
  }, [preselected, router]);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const doSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery) return;
    setSearching(true);
    setSpotifyResults([]);
    trackEvent("gatekeep_search", { query: searchQuery });
    const data = await api.searchArtists(searchQuery);
    setResults(data);
    if (data.length < 3) {
      const spotify = await api.searchSpotifyArtists(searchQuery).catch(() => []);
      const existingIds = new Set(data.map((a: any) => a.artist_id));
      setSpotifyResults(spotify.filter((a: any) => !existingIds.has(a.artist_id)));
    }
    setSearching(false);
  }, []);

  useEffect(() => {
    if (prefillQuery) doSearch(prefillQuery);
  }, [prefillQuery, doSearch]);

  useEffect(() => {
    if (!query.trim() || query === prefillQuery) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(query.trim()), 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, prefillQuery, doSearch]);

  return (
    <div className="animate-fade-in">
      <h1 className="text-3xl font-black mb-2">Gatekeep</h1>
      <p className="text-gray-500 mb-6">
        Search for an artist to see who in your friend group listened first.
      </p>

      <div className="relative mb-8">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for an artist..."
          aria-label="Search for an artist"
          className="w-full bg-white/5 border border-white/10 rounded-full px-6 py-3 text-gray-100 placeholder-gray-600 focus:border-[var(--green)] focus:outline-none focus:ring-1 focus:ring-[var(--green)] transition-all"
        />
        {searching && (
          <div className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 text-sm animate-pulse">searching...</div>
        )}
      </div>

      {results.length > 0 && (
        <div className="space-y-2 animate-slide-up">
          {results.map((a) => (
            <Link
              key={a.artist_id}
              href={`/artist/${a.artist_id}`}
              className="card-hover w-full flex items-center gap-4 px-4 py-3"
            >
              {a.image_url ? (
                <img
                  src={a.image_url}
                  alt=""
                  className="w-12 h-12 rounded-full object-cover"
                />
              ) : (
                <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center text-lg text-gray-600">
                  {a.artist_name?.[0]}
                </div>
              )}
              <div className="flex-1 min-w-0">
                <span className="font-bold">{a.artist_name}</span>
                <span className="text-gray-600 text-sm ml-3">
                  {a.genres?.slice(0, 3).join(", ")}
                </span>
              </div>
              {a.your_listen_count > 0 && (
                <span className="text-[var(--green)] text-sm font-medium">
                  {a.your_listen_count} listens
                </span>
              )}
            </Link>
          ))}
        </div>
      )}

      {spotifyResults.length > 0 && (
        <div className="mt-6 animate-slide-up">
          <h2 className="text-xs font-bold uppercase tracking-widest text-gray-600 mb-3">
            From Spotify
          </h2>
          <div className="space-y-2">
            {spotifyResults.map((a) => (
              <Link
                key={a.artist_id}
                href={`/artist/${a.artist_id}`}
                className="card-hover w-full flex items-center gap-4 px-4 py-3"
              >
                {a.image_url ? (
                  <img src={a.image_url} alt="" className="w-12 h-12 rounded-full object-cover" />
                ) : (
                  <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center text-lg text-gray-600">
                    {a.artist_name?.[0]}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <span className="font-bold">{a.artist_name}</span>
                  <span className="text-gray-600 text-sm ml-3">
                    {a.genres?.slice(0, 3).join(", ")}
                  </span>
                </div>
                {a.spotify_followers > 0 && (
                  <span className="text-gray-600 text-xs">
                    {a.spotify_followers.toLocaleString()} followers
                  </span>
                )}
              </Link>
            ))}
          </div>
        </div>
      )}

      {results.length === 0 && spotifyResults.length === 0 && query && !searching && (
        <div className="card p-12 text-center">
          <p className="text-gray-500">No artists found for &ldquo;{query}&rdquo;</p>
        </div>
      )}
    </div>
  );
}

export default function Gatekeep() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-gray-500 animate-pulse">Loading...</div>
        </div>
      }
    >
      <GatekeepContent />
    </Suspense>
  );
}
