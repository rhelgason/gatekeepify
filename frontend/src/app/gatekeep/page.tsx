"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";
import Link from "next/link";

function GatekeepContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselected = searchParams.get("artist");

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [comparison, setComparison] = useState<any>(null);
  const [artistDetail, setArtistDetail] = useState<any>(null);
  const [challenge, setChallenge] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/");
  }, [router]);

  useEffect(() => {
    if (preselected) loadArtist(preselected);
  }, [preselected]);

  async function handleSearch() {
    if (!query.trim()) return;
    setSearching(true);
    setComparison(null);
    setArtistDetail(null);
    setChallenge(null);
    const data = await api.searchArtists(query);
    setResults(data);
    setSearching(false);
  }

  async function loadArtist(artistId: string) {
    setLoading(true);
    setChallenge(null);
    setResults([]);
    setQuery("");
    try {
      const [comp, detail] = await Promise.all([
        api.gatekeepArtist(artistId),
        api.getArtistDetail(artistId).catch(() => null),
      ]);
      setComparison(comp);
      setArtistDetail(detail);
    } catch {
      setComparison({ artist_id: artistId, artist_name: "Unknown", entries: [] });
    }
    setLoading(false);
  }

  async function handleChallenge() {
    if (!comparison) return;
    const data = await api.createChallenge(comparison.artist_id);
    setChallenge(data);
  }

  return (
    <div className="animate-fade-in">
      <h1 className="text-3xl font-black mb-6">Gatekeep</h1>

      <div className="flex gap-2 mb-8">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Search for an artist..."
          className="flex-1 bg-white/5 border border-white/10 rounded-full px-6 py-3 text-gray-100 placeholder-gray-600 focus:border-[var(--green)] focus:outline-none focus:ring-1 focus:ring-[var(--green)] transition-all"
        />
        <button
          onClick={handleSearch}
          disabled={searching}
          className="btn-primary"
        >
          {searching ? "..." : "Search"}
        </button>
      </div>

      {results.length > 0 && !comparison && (
        <div className="space-y-2 mb-6 animate-slide-up">
          {results.map((a) => (
            <Link
              key={a.artist_id}
              href={`/artist/${a.artist_id}`}
              className="card-hover w-full text-left flex items-center gap-4 px-4 py-3"
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
              {a.your_listen_count > 0 && (
                <span className="text-[var(--green)] text-sm font-medium">
                  {a.your_listen_count} listens
                </span>
              )}
            </Link>
          ))}
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="text-gray-500 animate-pulse">Loading comparison...</div>
        </div>
      )}

      {comparison && !loading && (
        <div className="animate-slide-up">
          {/* Artist header */}
          <div className="card p-6 mb-6 flex items-center gap-6">
            {artistDetail?.image_url ? (
              <img
                src={artistDetail.image_url}
                alt={comparison.artist_name}
                className="w-28 h-28 rounded-2xl object-cover ring-2 ring-white/10"
              />
            ) : (
              <div className="w-28 h-28 rounded-2xl bg-white/5 flex items-center justify-center text-4xl text-gray-600">
                {comparison.artist_name?.[0]}
              </div>
            )}
            <div>
              <button
                onClick={() => {
                  setComparison(null);
                  setArtistDetail(null);
                  setChallenge(null);
                }}
                className="text-xs text-gray-600 hover:text-gray-400 mb-1 block transition-colors"
              >
                &larr; back to search
              </button>
              <h2 className="text-3xl font-black">{comparison.artist_name}</h2>
              {artistDetail?.genres?.length > 0 && (
                <div className="flex gap-2 mt-2 flex-wrap">
                  {artistDetail.genres.slice(0, 4).map((g: string) => (
                    <span key={g} className="text-xs bg-white/5 px-3 py-1 rounded-full text-gray-400">
                      {g}
                    </span>
                  ))}
                </div>
              )}
              {artistDetail && (
                <p className="text-sm text-gray-500 mt-2">
                  You&apos;ve listened {artistDetail.total_listens} times &middot; {artistDetail.total_minutes} minutes
                  {artistDetail.first_listen && (
                    <> &middot; since {new Date(artistDetail.first_listen).toLocaleDateString()}</>
                  )}
                </p>
              )}
            </div>
          </div>

          {/* Comparison entries */}
          {comparison.entries.length === 0 ? (
            <div className="card p-8 text-center">
              <p className="text-gray-500 text-lg">
                No one in your friend group has listened to this artist yet.
              </p>
              <p className="text-gray-600 text-sm mt-2">
                Challenge a friend to prove they know this artist.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {comparison.entries.map((entry: any, i: number) => (
                <div
                  key={entry.user_id}
                  className={`card p-5 animate-slide-up ${
                    entry.is_winner
                      ? "ring-1 ring-[var(--green)]/30 bg-[var(--green-dim)]"
                      : ""
                  }`}
                  style={{ animationDelay: `${i * 0.1}s` }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      {entry.is_winner && <span className="text-3xl">👑</span>}
                      <div>
                        <span className="font-bold text-lg">
                          {entry.user_name || entry.user_id}
                        </span>
                        <span className={`ml-3 ${
                          entry.first_listen_source === "api"
                            ? "badge-verified"
                            : "badge-self-reported"
                        }`}>
                          {entry.first_listen_source === "api"
                            ? "verified"
                            : "self-reported"}
                        </span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-bold text-lg">
                        {entry.total_listens}{" "}
                        <span className="text-gray-500 font-normal text-sm">
                          listens
                        </span>
                      </div>
                      <div className="text-xs text-gray-500">
                        First: {new Date(entry.first_listen).toLocaleDateString("en-US", {
                          month: "short",
                          year: "numeric",
                        })}
                        {entry.verified_listens > 0 && entry.verified_listens < entry.total_listens && (
                          <> &middot; {entry.verified_listens} verified</>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Challenge */}
          <div className="mt-6 flex gap-3">
            <button onClick={handleChallenge} className="btn-primary">
              Challenge a Friend
            </button>
          </div>

          {challenge && (
            <div className="mt-4 card p-6 animate-slide-up border-[var(--green)]/20">
              <p className="text-xl font-bold italic mb-4 leading-relaxed">
                &ldquo;{challenge.challenge_text}&rdquo;
              </p>
              <div className="flex items-center gap-3 bg-white/5 rounded-xl p-3">
                <span className="text-gray-500 text-sm">Invite code:</span>
                <code className="font-mono text-[var(--green)] text-sm flex-1">
                  {challenge.invite_code}
                </code>
                <button
                  onClick={() => navigator.clipboard.writeText(challenge.invite_code)}
                  className="btn-secondary text-xs py-1.5 px-4"
                >
                  Copy
                </button>
              </div>
            </div>
          )}
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
