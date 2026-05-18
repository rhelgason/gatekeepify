"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";
import { trackEvent } from "@/lib/track";
import Link from "next/link";

type Period = "all" | "year" | "month" | "today";

export default function Profile() {
  const router = useRouter();
  const params = useParams();
  const userId = params.userId as string;

  const [period, setPeriod] = useState<Period>("all");
  const [tracks, setTracks] = useState<any[]>([]);
  const [artists, setArtists] = useState<any[]>([]);
  const [genres, setGenres] = useState<any[]>([]);
  const [userName, setUserName] = useState("");
  const [userImage, setUserImage] = useState<string | null>(null);
  const [compat, setCompat] = useState<any>(null);
  const [compatLoading, setCompatLoading] = useState(false);
  const [isSelf, setIsSelf] = useState(false);
  const [isFriend, setIsFriend] = useState(false);
  const [requestSent, setRequestSent] = useState(false);
  const [memberSince, setMemberSince] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/");
      return;
    }
    setLoading(true);
    Promise.all([
      api.getTopTracks(period, 10, 0, userId),
      api.getTopArtists(period, 10, 0, userId),
      api.getTopGenres(period, 5, 0, userId),
    ]).then(([t, a, g]) => {
      setTracks(t);
      setArtists(a);
      setGenres(g);
      setLoading(false);
    }).catch(() => {
      setLoading(false);
    });
  }, [period, userId, router]);

  useEffect(() => {
    api.getMe().then(me => {
      if (me.user_id === userId) {
        setIsSelf(true);
        setUserName(me.user_name || me.user_id);
        setUserImage(me.image_url);
        if (me.created_at) {
          setMemberSince(new Date(me.created_at).toLocaleDateString("en-US", { month: "long", year: "numeric" }));
        }
      } else {
        setIsSelf(false);
        api.getFriends().then(friends => {
          const friend = friends.find((f: any) => f.user_id === userId);
          if (friend) {
            setIsFriend(true);
            setUserName(friend.user_name || friend.user_id);
            setUserImage(friend.image_url);
            setCompatLoading(true);
            api.getCompatibility(userId).then(setCompat).catch(() => {}).finally(() => setCompatLoading(false));
          } else {
            setIsFriend(false);
            setUserName(userId);
          }
        });
      }
    }).catch(() => {
      setUserName(userId);
    });
    trackEvent("profile_viewed", { profile_user_id: userId });
  }, [userId]);

  const periods: { value: Period; label: string }[] = [
    { value: "today", label: "Today (UTC)" },
    { value: "month", label: "30 Days" },
    { value: "year", label: "Year" },
    { value: "all", label: "All Time" },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-gray-500 animate-pulse text-lg">Loading profile...</div>
      </div>
    );
  }

  const isEmpty = tracks.length === 0 && artists.length === 0;

  return (
    <div className="animate-fade-in">
      {!isSelf && (
        <button onClick={() => router.back()} className="text-xs text-gray-600 hover:text-gray-400 transition-colors">
          &larr; back
        </button>
      )}

      <div className="flex items-center gap-4 mt-4 mb-6">
        {userImage ? (
          <img src={userImage} alt="" className="w-16 h-16 rounded-full object-cover" />
        ) : (
          <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center text-2xl text-gray-500">
            {userName[0]?.toUpperCase() || "?"}
          </div>
        )}
        <div>
          <h1 className="text-3xl font-black">{userName}</h1>
          <p className="text-gray-500 text-sm">
            {isSelf ? (
              <>
                Your profile
                {memberSince && <span className="text-gray-600"> &middot; Member since {memberSince}</span>}
              </>
            ) : (
              "Friend’s listening stats"
            )}
          </p>
        </div>
      </div>

      {!isSelf && !isFriend && (
        <div className="card p-5 mb-8 flex items-center justify-between">
          <p className="text-gray-400 text-sm">You&apos;re not friends yet.</p>
          <button
            onClick={async () => {
              try {
                await api.sendFriendRequest(userId);
                trackEvent("friend_request_sent", { to_user: userId });
                setRequestSent(true);
              } catch {}
            }}
            disabled={requestSent}
            className={requestSent ? "text-gray-600 text-sm" : "btn-primary text-sm"}
          >
            {requestSent ? "Request Sent" : "Add Friend"}
          </button>
        </div>
      )}

      {!isSelf && isFriend && (
        <div className="card p-5 mb-8">
          {compatLoading || !compat ? (
            <div className="flex flex-col sm:flex-row items-center gap-6">
              <div className="text-center flex-shrink-0">
                <div className="h-12 w-24 bg-white/5 rounded animate-pulse mx-auto" />
                <div className="text-gray-600 text-xs uppercase tracking-wider mt-1">compatibility</div>
              </div>
              <div className="flex-1 w-full">
                <div className="flex gap-4 mb-3 text-center">
                  <div className="flex-1">
                    <div className="h-4 w-10 bg-white/5 rounded animate-pulse mx-auto" />
                    <div className="text-[10px] text-gray-600 mt-1">artist overlap</div>
                  </div>
                  <div className="flex-1">
                    <div className="h-4 w-10 bg-white/5 rounded animate-pulse mx-auto" />
                    <div className="text-[10px] text-gray-600 mt-1">genre overlap</div>
                  </div>
                  <div className="flex-1">
                    <div className="h-4 w-10 bg-white/5 rounded animate-pulse mx-auto" />
                    <div className="text-[10px] text-gray-600 mt-1">top 5 match</div>
                  </div>
                </div>
                <div className="h-3 w-48 bg-white/5 rounded animate-pulse mb-2" />
                <div className="h-3 w-36 bg-white/5 rounded animate-pulse" />
              </div>
            </div>
          ) : (
            <div className="flex flex-col sm:flex-row items-center gap-6 animate-slide-up">
              <div className="text-center flex-shrink-0">
                <div className={`stat-number text-5xl ${compat.score >= 70 ? "gradient-text" : compat.score >= 40 ? "text-yellow-400" : "text-red-400"}`}>
                  {compat.score}%
                </div>
                <div className="text-gray-600 text-xs uppercase tracking-wider mt-1">compatibility</div>
              </div>
              <div className="flex-1 w-full">
                <div className="flex gap-4 mb-3 text-center">
                  <div className="flex-1">
                    <div className="text-sm font-bold">{compat.artist_overlap}%</div>
                    <div className="text-[10px] text-gray-600">artist overlap</div>
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-bold">{compat.genre_overlap}%</div>
                    <div className="text-[10px] text-gray-600">genre overlap</div>
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-bold">{compat.top5_agreement}%</div>
                    <div className="text-[10px] text-gray-600">top 5 match</div>
                  </div>
                </div>
                {compat.shared_artists?.length > 0 && (
                  <div className="mb-2">
                    <span className="text-[10px] text-gray-500 uppercase tracking-wider">You both listen to: </span>
                    <span className="text-xs text-gray-300">{compat.shared_artists.slice(0, 5).join(", ")}</span>
                  </div>
                )}
                {compat.disagreement_genres?.length > 0 && (
                  <div>
                    <span className="text-[10px] text-gray-500 uppercase tracking-wider">You disagree on: </span>
                    <span className="text-xs text-gray-400">{compat.disagreement_genres.slice(0, 3).join(", ")}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-8">
        <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500">Stats</h2>
        <div className="flex gap-1 bg-white/5 rounded-full p-1">
          {periods.map((p) => (
            <button
              key={p.value}
              onClick={() => { setPeriod(p.value); trackEvent("profile_period_changed", { period: p.value, profile_user: userId }); }}
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

      {isEmpty ? (
        <div className="card p-12 text-center">
          <p className="text-gray-400 text-lg mb-2">No listening data yet</p>
          <p className="text-gray-600 text-sm">
            {isSelf
              ? "Your listening data will appear here as we collect it."
              : "This friend hasn’t accumulated enough data yet."}
          </p>
        </div>
      ) : (
        <>
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
                  <div key={t.track_id} className="card-hover flex items-center gap-4 px-4 py-3">
                    <span className="text-gray-600 font-mono text-sm w-6 text-right">{t.rank}</span>
                    {t.image_url ? (
                      <img src={t.image_url} alt="" className="w-10 h-10 rounded object-cover" />
                    ) : (
                      <div className="w-10 h-10 rounded bg-white/5" />
                    )}
                    <div className="flex-1 min-w-0">
                      <span className="font-medium truncate block text-sm">{t.track_name || "Unknown"}</span>
                      <span className="text-xs text-gray-600 truncate block">{t.album_name}</span>
                    </div>
                    <span className="text-sm text-gray-400">{t.listen_count} plays</span>
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
      )}
    </div>
  );
}
