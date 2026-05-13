"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";

function GatekeepContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselected = searchParams.get("artist");

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [comparison, setComparison] = useState<any>(null);
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
    const data = await api.gatekeepArtist(artistId);
    setComparison(data);
    setLoading(false);
  }

  async function handleChallenge() {
    if (!comparison) return;
    const data = await api.createChallenge(comparison.artist_id);
    setChallenge(data);
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Gatekeep an Artist</h1>

      <div className="flex gap-2 mb-6">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Search for an artist..."
          className="flex-1 bg-gray-900 border border-gray-700 rounded px-4 py-2 text-gray-100 placeholder-gray-500 focus:border-green-500 focus:outline-none"
        />
        <button
          onClick={handleSearch}
          disabled={searching}
          className="bg-green-500 hover:bg-green-400 text-black font-semibold px-6 py-2 rounded transition"
        >
          {searching ? "..." : "Search"}
        </button>
      </div>

      {results.length > 0 && !comparison && (
        <div className="space-y-2 mb-6">
          {results.map((a) => (
            <button
              key={a.artist_id}
              onClick={() => loadArtist(a.artist_id)}
              className="w-full text-left bg-gray-900 hover:bg-gray-800 rounded px-4 py-3 transition"
            >
              <span className="font-medium">{a.artist_name}</span>
              <span className="text-gray-500 text-sm ml-3">
                {a.genres?.slice(0, 3).join(", ")}
              </span>
              {a.your_listen_count > 0 && (
                <span className="text-green-400 text-sm ml-3">
                  {a.your_listen_count} listens
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {loading && <p className="text-gray-400">Loading comparison...</p>}

      {comparison && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">
              {comparison.artist_name}
            </h2>
            <button
              onClick={() => {
                setComparison(null);
                setChallenge(null);
              }}
              className="text-gray-500 hover:text-gray-300 text-sm"
            >
              Search again
            </button>
          </div>

          {comparison.entries.length === 0 ? (
            <p className="text-gray-500">
              No one in your friend group has listened to this artist yet.
            </p>
          ) : (
            <div className="space-y-3">
              {comparison.entries.map((entry: any, i: number) => (
                <div
                  key={entry.user_id}
                  className={`rounded-lg px-4 py-3 ${
                    entry.is_winner
                      ? "bg-green-500/10 border border-green-500/30"
                      : "bg-gray-900"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {entry.is_winner && <span className="text-2xl">👑</span>}
                      <div>
                        <span className="font-medium">
                          {entry.user_name || entry.user_id}
                        </span>
                        <span
                          className={`ml-2 text-xs px-2 py-0.5 rounded-full ${
                            entry.first_listen_source === "api"
                              ? "bg-green-500/20 text-green-400"
                              : "bg-yellow-500/20 text-yellow-400"
                          }`}
                        >
                          {entry.first_listen_source === "api"
                            ? "verified"
                            : "self-reported"}
                        </span>
                      </div>
                    </div>
                    <div className="text-right text-sm">
                      <div className="text-gray-400">
                        {entry.total_listens} listens &middot;{" "}
                        {entry.total_minutes} min
                      </div>
                      <div className="text-gray-500">
                        First listen:{" "}
                        {new Date(entry.first_listen).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="mt-6">
            <button
              onClick={handleChallenge}
              className="bg-green-500 hover:bg-green-400 text-black font-semibold px-6 py-2 rounded transition"
            >
              Challenge a Friend
            </button>
          </div>

          {challenge && (
            <div className="mt-4 bg-gray-900 rounded-lg p-4 border border-gray-700">
              <p className="text-lg italic mb-3">
                &ldquo;{challenge.challenge_text}&rdquo;
              </p>
              <div className="flex items-center gap-2">
                <span className="text-gray-400 text-sm">Share invite code:</span>
                <code className="bg-gray-800 px-3 py-1 rounded text-green-400 text-sm">
                  {challenge.invite_code}
                </code>
                <button
                  onClick={() =>
                    navigator.clipboard.writeText(challenge.invite_code)
                  }
                  className="text-xs text-gray-500 hover:text-gray-300"
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
    <Suspense fallback={<p className="text-gray-400 mt-12 text-center">Loading...</p>}>
      <GatekeepContent />
    </Suspense>
  );
}
