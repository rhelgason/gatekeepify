"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";
import { trackEvent } from "@/lib/track";
import ShareButton from "@/components/ShareButton";
import Link from "next/link";

export default function ArtistPage() {
  const router = useRouter();
  const params = useParams();
  const artistId = params.artistId as string;

  const [detail, setDetail] = useState<any>(null);
  const [comparison, setComparison] = useState<any>(null);
  const [timeline, setTimeline] = useState<any>(null);
  const [lastfmData, setLastfmData] = useState<any>(null);
  const [lastfmLoading, setLastfmLoading] = useState(false);
  const [timelineMode, setTimelineMode] = useState<"personal" | "friends" | "global">("personal");
  const [challenge, setChallenge] = useState<any>(null);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);
  const [hoveredPoint, setHoveredPoint] = useState<{ idx: number } | null>(null);
  const [selectedFriendIds, setSelectedFriendIds] = useState<string[] | null>(null);
  const [allFriends, setAllFriends] = useState<any[] | null>(null);
  const [totalFriendsWithData, setTotalFriendsWithData] = useState<number | null>(null);
  const [showFriendSelector, setShowFriendSelector] = useState(false);

  const loadArtist = useCallback(async () => {
    setLoading(true);
    try {
      const [d, c, t] = await Promise.all([
        api.getArtistDetail(artistId).catch(() => null),
        api.gatekeepArtist(artistId).catch(() => null),
        api.getTimeline(artistId, "personal").catch(() => null),
      ]);
      setDetail(d);
      setComparison(c);
      setTimeline(t);
    } catch {}
    setLoading(false);
  }, [artistId]);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/");
      return;
    }
    loadArtist();
  }, [artistId, router, loadArtist]);

  useEffect(() => {
    if (artistId && !loading) {
      if (timelineMode === "global") {
        api.getTimeline(artistId, "global").then(setTimeline).catch(() => {});
        if (detail?.artist_name) {
          setLastfmLoading(true);
          api.getLastfmTimeline(detail.artist_name).then(setLastfmData).catch(() => {}).finally(() => setLastfmLoading(false));
        }
      } else if (timelineMode === "friends" && selectedFriendIds) {
        api.getTimeline(artistId, "friends", selectedFriendIds).then(data => {
          setTimeline(data);
        }).catch(() => {});
      } else {
        api.getTimeline(artistId, timelineMode).then(data => {
          setTimeline(data);
          if (timelineMode === "friends") {
            setTotalFriendsWithData(data.total_friends_with_data ?? null);
            setAllFriends(data.all_friends ?? null);
          }
        }).catch(() => {});
      }
    }
  }, [artistId, timelineMode, loading, detail?.artist_name, selectedFriendIds]);

  async function handleChallenge() {
    trackEvent("challenge_created", { artist_id: artistId }, "artist", artistId);
    const data = await api.createChallenge(artistId);
    setChallenge(data);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-gray-500 animate-pulse text-lg">Loading artist...</div>
      </div>
    );
  }

  const name = detail?.artist_name || comparison?.artist_name || "Unknown Artist";
  const imageUrl = detail?.image_url;
  const genres = detail?.genres || [];

  return (
    <div className="animate-fade-in">
      <button onClick={() => router.back()} className="text-xs text-gray-600 hover:text-gray-400 transition-colors">
        &larr; back
      </button>

      {/* Hero */}
      <div className="mt-4 flex flex-col md:flex-row items-center md:items-end gap-6 md:gap-8 mb-10">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={name}
            className="w-32 h-32 md:w-48 md:h-48 rounded-3xl object-cover ring-2 ring-white/10 shadow-2xl shadow-black/50"
          />
        ) : (
          <div className="w-32 h-32 md:w-48 md:h-48 rounded-3xl bg-white/5 flex items-center justify-center text-4xl md:text-6xl text-gray-600 ring-2 ring-white/10">
            {name[0]}
          </div>
        )}
        <div className="text-center md:text-left">
          <div className="flex items-center gap-3 justify-center md:justify-start mb-3">
            <h1 className="text-3xl md:text-6xl font-black tracking-tight">{name}</h1>
            <a
              href={`https://open.spotify.com/artist/${artistId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-600 hover:text-[var(--green)] transition-colors flex-shrink-0"
              title="Open in Spotify"
              onClick={() => trackEvent("spotify_link_clicked", { artist_id: artistId }, "artist", artistId)}
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
              </svg>
            </a>
            {detail && (
              <ShareButton
                cardData={{
                  artistName: name,
                  imageUrl: imageUrl,
                  statNumber: detail.total_listens.toLocaleString(),
                  statLabel: "listens",
                  contextLine: detail.first_listen
                    ? `since ${new Date(detail.first_listen).toLocaleDateString("en-US", { month: "long", year: "numeric" })}`
                    : "",
                  secondaryStat: detail.total_minutes ? `${detail.total_minutes.toLocaleString()} minutes` : undefined,
                }}
                surface="artist"
                entityId={artistId}
              />
            )}
          </div>
          {genres.length > 0 && (
            <div className="flex gap-2 flex-wrap justify-center md:justify-start mb-4">
              {genres.slice(0, 5).map((g: string) => (
                <span key={g} className="text-xs bg-white/5 border border-white/10 px-3 py-1.5 rounded-full text-gray-400">
                  {g}
                </span>
              ))}
            </div>
          )}
          {detail && (
            <div className="flex gap-4 md:gap-6 justify-center md:justify-start">
              <div>
                <div className="stat-number text-xl md:text-3xl">{detail.total_listens.toLocaleString()}</div>
                <div className="text-gray-600 text-[10px] md:text-xs uppercase tracking-wider">listens</div>
              </div>
              <div>
                <div className="stat-number text-xl md:text-3xl">{detail.total_minutes.toLocaleString()}</div>
                <div className="text-gray-600 text-[10px] md:text-xs uppercase tracking-wider">minutes</div>
              </div>
              {detail.first_listen && (
                <div>
                  <div className="stat-number text-3xl">
                    {new Date(detail.first_listen).toLocaleDateString("en-US", { month: "short", year: "numeric" })}
                  </div>
                  <div className="text-gray-600 text-xs uppercase tracking-wider">first listen</div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Timeline */}
      <section className="mb-10">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mb-4">
          <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500">
            Listening Timeline
          </h2>
          <div className="flex gap-1 bg-white/5 rounded-full p-1">
            {([
              { key: "personal", label: "Yours" },
              { key: "friends", label: "Friends" },
              { key: "global", label: "Global" },
            ] as const).map(({ key, label }) => (
              <button
                key={key}
                onClick={() => { setTimelineMode(key); setSelectedFriendIds(null); setShowFriendSelector(false); trackEvent("timeline_mode_changed", { mode: key, artist_id: artistId }, "artist", artistId); }}
                className={`px-3 py-1.5 rounded-full text-xs transition-all ${
                  timelineMode === key
                    ? "bg-[var(--green)] text-black font-bold"
                    : "text-gray-500 hover:text-white"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {(() => {
          const lineColors = ["#1DB954", "#34d399", "#2dd4bf", "#22d3ee", "#38bdf8", "#a78bfa", "#f472b6", "#fb923c", "#facc15", "#4ade80"];

          function formatMonth(m: string) {
            const [y, mo] = m.split("-");
            const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
            return `${months[parseInt(mo) - 1]} '${y.slice(2)}`;
          }

          function niceYTicks(maxVal: number): number[] {
            if (maxVal <= 0) return [0];
            const raw = maxVal / 4;
            const mag = Math.pow(10, Math.floor(Math.log10(raw)));
            const nice = [1, 2, 2.5, 5, 10].find(n => n * mag >= raw)! * mag;
            const ceil = Math.ceil(maxVal / nice) * nice;
            const ticks: number[] = [];
            for (let v = 0; v <= ceil; v += nice) {
              ticks.push(Math.round(v));
            }
            return ticks;
          }

          function renderLineChart(datasets: { label: string; months: any[]; color: string }[], footnote?: string) {
            const allMonths = Array.from(new Set(datasets.flatMap(d => d.months.map((m: any) => m.month)))).sort();
            const rawMax = Math.max(...datasets.flatMap(d => d.months.map((m: any) => m.listen_count)), 1);
            const yTicks = niceYTicks(rawMax);
            const maxVal = yTicks[yTicks.length - 1] || 1;

            const W = 650, H = 160, padL = 45, padR = 10, padT = 15, padB = 25;
            const chartW = W - padL - padR, chartH = H - padT - padB;

            function getX(i: number) {
              return padL + (allMonths.length === 1 ? chartW / 2 : (i / (allMonths.length - 1)) * chartW);
            }
            function getY(val: number) {
              return padT + chartH - (val / maxVal) * chartH;
            }

            const allPoints = datasets.map(ds =>
              allMonths.map((month, i) => {
                const entry = ds.months.find((m: any) => m.month === month);
                return { x: getX(i), y: getY(entry?.listen_count || 0), val: entry?.listen_count || 0, month };
              })
            );

            return (
              <div className="card p-6 relative">
                <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-44" preserveAspectRatio="xMidYMid meet"
                  onMouseLeave={() => setHoveredPoint(null)}
                >
                  {yTicks.map(val => (
                    <g key={val}>
                      <line x1={padL} x2={W - padR} y1={getY(val)} y2={getY(val)}
                        stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
                      <text x={padL - 8} y={getY(val) + 3} textAnchor="end"
                        fill="rgba(255,255,255,0.3)" fontSize="9" fontFamily="monospace">
                        {val.toLocaleString()}
                      </text>
                    </g>
                  ))}
                  {allMonths.map((month, i) => {
                    const showLabel = allMonths.length <= 12 || i % Math.ceil(allMonths.length / 8) === 0 || i === allMonths.length - 1;
                    return showLabel ? (
                      <text key={month} x={getX(i)} y={H - 5} textAnchor="middle"
                        fill="rgba(255,255,255,0.3)" fontSize="9" fontFamily="sans-serif">
                        {formatMonth(month)}
                      </text>
                    ) : null;
                  })}
                  {datasets.map((ds, di) => {
                    const points = allPoints[di];
                    const smoothPath = (pts: typeof points) => {
                      if (pts.length < 2) return `M ${pts[0]?.x || 0} ${pts[0]?.y || 0}`;
                      let d = `M ${pts[0].x} ${pts[0].y}`;
                      for (let i = 0; i < pts.length - 1; i++) {
                        const p0 = pts[Math.max(i - 1, 0)];
                        const p1 = pts[i];
                        const p2 = pts[i + 1];
                        const p3 = pts[Math.min(i + 2, pts.length - 1)];
                        const t = 0.3;
                        const yFloor = getY(0);
                        const cp1x = p1.x + (p2.x - p0.x) * t;
                        const cp1y = Math.min(p1.y + (p2.y - p0.y) * t, yFloor);
                        const cp2x = p2.x - (p3.x - p1.x) * t;
                        const cp2y = Math.min(p2.y - (p3.y - p1.y) * t, yFloor);
                        d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
                      }
                      return d;
                    };
                    const pathD = smoothPath(points);
                    const areaD = pathD + ` L ${points[points.length - 1].x} ${padT + chartH} L ${points[0].x} ${padT + chartH} Z`;
                    return (
                      <g key={di}>
                        <path d={areaD} fill={ds.color} opacity="0.06" />
                        <path d={pathD} fill="none" stroke={ds.color} strokeWidth="2" strokeLinecap="round" />
                      </g>
                    );
                  })}
                  {hoveredPoint && (
                    <>
                      <line x1={getX(hoveredPoint.idx)} x2={getX(hoveredPoint.idx)}
                        y1={padT} y2={padT + chartH}
                        stroke="rgba(255,255,255,0.15)" strokeWidth="1" strokeDasharray="3,3" />
                      {allPoints.map((points, di) => (
                        <circle key={di} cx={points[hoveredPoint.idx].x} cy={points[hoveredPoint.idx].y}
                          r="4" fill={datasets[di].color} />
                      ))}
                    </>
                  )}
                  {allMonths.map((_, i) => (
                    <rect key={i}
                      x={getX(i) - (chartW / allMonths.length) / 2}
                      y={padT} width={chartW / allMonths.length} height={chartH}
                      fill="transparent"
                      onMouseEnter={() => setHoveredPoint({ idx: i })}
                    />
                  ))}
                </svg>
                {hoveredPoint && (() => {
                  const idx = hoveredPoint.idx;
                  const month = allMonths[idx];
                  const xPct = (getX(idx) / W) * 100;
                  return (
                    <div
                      className="absolute pointer-events-none z-10 rounded-lg bg-[#1a1a1a] border border-white/10 shadow-xl px-3 py-2 text-xs"
                      style={{
                        left: `${Math.min(Math.max(xPct, 10), 90)}%`,
                        top: "0.5rem",
                        transform: "translateX(-50%)",
                      }}
                    >
                      <div className="font-bold text-white mb-1">{formatMonth(month)}</div>
                      {datasets.map((ds, di) => (
                        <div key={di} className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: ds.color }} />
                          <span className="text-gray-400">{ds.label}:</span>
                          <span className="text-white font-medium">{allPoints[di][idx].val.toLocaleString()}</span>
                        </div>
                      ))}
                    </div>
                  );
                })()}
                {datasets.length > 1 && (
                  <div className="flex gap-4 mt-3 pt-3 border-t border-white/5">
                    {datasets.map((ds, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs text-gray-500">
                        <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: ds.color }} />
                        {ds.label}
                      </div>
                    ))}
                  </div>
                )}
                {footnote && <p className="text-center text-gray-600 text-xs mt-3">{footnote}</p>}
              </div>
            );
          }

          // Global mode: Gatekeepify aggregate line chart + Last.fm stats
          if (timelineMode === "global") {
            const users = timeline?.users || [];
            const hasChartData = users.some((u: any) => u.months?.length > 0);
            const d = lastfmData?.data;

            return (
              <div className="space-y-4">
                {hasChartData ? (
                  renderLineChart(
                    users.filter((u: any) => u.months?.length > 0).map((u: any, i: number) => ({
                      label: users.length > 1 ? (u.user_name || u.user_id) : "All Gatekeepify Users",
                      months: u.months,
                      color: lineColors[i % lineColors.length],
                    })),
                    "Listening activity across all Gatekeepify users"
                  )
                ) : (
                  <div className="card p-8 text-center">
                    <p className="text-gray-500 mb-2">Not enough Gatekeepify data for a timeline yet.</p>
                    <p className="text-gray-600 text-sm">The chart will populate as users listen over time.</p>
                  </div>
                )}
                {lastfmLoading && (
                  <>
                    {/* Last.fm stats skeleton */}
                    <div className="card p-6">
                      <div className="flex justify-center gap-10 mb-2">
                        <div className="text-center">
                          <div className="h-9 w-24 bg-white/5 rounded animate-pulse mx-auto" />
                          <div className="text-gray-600 text-xs uppercase tracking-wider mt-1">listeners</div>
                        </div>
                        <div className="text-center">
                          <div className="h-9 w-24 bg-white/5 rounded animate-pulse mx-auto" />
                          <div className="text-gray-600 text-xs uppercase tracking-wider mt-1">total plays</div>
                        </div>
                      </div>
                      <div className="flex gap-2 justify-center mt-4">
                        {[1, 2, 3].map(n => (
                          <div key={n} className="h-6 w-16 bg-white/5 rounded-full animate-pulse" />
                        ))}
                      </div>
                      <p className="text-center text-gray-600 text-xs mt-3">Global stats via Last.fm</p>
                    </div>
                    {/* Top tracks skeleton */}
                    <div className="card p-5">
                      <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-3">Top Tracks (Global)</h3>
                      <div className="space-y-2">
                        {[1, 2, 3, 4, 5].map(n => (
                          <div key={n} className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <div className="h-4 w-5 bg-white/5 rounded animate-pulse" />
                              <div className="h-4 w-32 bg-white/5 rounded animate-pulse" />
                            </div>
                            <div className="h-4 w-16 bg-white/5 rounded animate-pulse" />
                          </div>
                        ))}
                      </div>
                    </div>
                    {/* Similar artists skeleton */}
                    <div className="card p-5">
                      <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-3">Similar Artists</h3>
                      <div className="flex gap-2 flex-wrap">
                        {[1, 2, 3, 4, 5].map(n => (
                          <div key={n} className="h-8 w-24 bg-white/5 rounded-full animate-pulse" />
                        ))}
                      </div>
                    </div>
                  </>
                )}
                {!lastfmLoading && d && (
                  <>
                    <div className="card p-6">
                      <div className="flex justify-center gap-10 mb-2">
                        <div className="text-center">
                          <div className="stat-number text-3xl gradient-text">{d.total_listeners?.toLocaleString()}</div>
                          <div className="text-gray-600 text-xs uppercase tracking-wider">listeners</div>
                        </div>
                        <div className="text-center">
                          <div className="stat-number text-3xl">{d.total_playcount?.toLocaleString()}</div>
                          <div className="text-gray-600 text-xs uppercase tracking-wider">total plays</div>
                        </div>
                      </div>
                      {d.tags?.length > 0 && (
                        <div className="flex gap-2 justify-center mt-4 flex-wrap">
                          {d.tags.map((tag: string) => (
                            <span key={tag} className="text-xs bg-white/5 border border-white/10 px-3 py-1 rounded-full text-gray-400">{tag}</span>
                          ))}
                        </div>
                      )}
                      <p className="text-center text-gray-600 text-xs mt-3">Global stats via Last.fm</p>
                    </div>
                    {d.top_tracks?.length > 0 && (
                      <div className="card p-5">
                        <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-3">Top Tracks (Global)</h3>
                        <div className="space-y-2">
                          {d.top_tracks.map((t: any, i: number) => (
                            <div key={i} className="flex items-center justify-between text-sm">
                              <div className="flex items-center gap-3">
                                <span className={`font-mono w-5 text-right ${i === 0 ? "text-[var(--green)]" : "text-gray-600"}`}>{i + 1}</span>
                                <span className="text-gray-200">{t.name}</span>
                              </div>
                              <span className="text-gray-500 text-xs">{t.playcount.toLocaleString()} plays</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {d.similar_artists?.length > 0 && (
                      <div className="card p-5">
                        <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-3">Similar Artists</h3>
                        <div className="flex gap-2 flex-wrap">
                          {d.similar_artists.map((artistName: string) => (
                            <button key={artistName}
                              onClick={async () => {
                                trackEvent("similar_artist_clicked", { from_artist: artistId, to_artist: artistName });
                                try {
                                  const resolved = await api.resolveArtist(artistName);
                                  router.push(`/artist/${resolved.artist_id}`);
                                } catch {
                                  router.push(`/gatekeep?q=${encodeURIComponent(artistName)}`);
                                }
                              }}
                              className="text-sm bg-white/5 px-4 py-1.5 rounded-full text-gray-300 hover:bg-white/10 hover:text-white transition-all">
                              {artistName}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            );
          }

          // Personal / Friends modes
          const users = timeline?.users || [];
          const hasData = users.some((u: any) => u.months?.length > 0);

          if (!hasData) {
            return (
              <div className="card p-8 text-center">
                <p className="text-gray-500 mb-2">Not enough data to show a timeline yet.</p>
                <p className="text-gray-600 text-sm">
                  Keep listening, or{" "}
                  <Link href="/upload" className="text-[var(--green)] hover:underline">
                    upload your Spotify data export
                  </Link>{" "}
                  for full history.
                </p>
              </div>
            );
          }

          return (
            <div>
              {renderLineChart(
                users.filter((u: any) => u.months?.length > 0).map((u: any, i: number) => ({
                  label: u.user_name || u.user_id,
                  months: u.months,
                  color: lineColors[i % lineColors.length],
                }))
              )}
              {timelineMode === "friends" && totalFriendsWithData !== null && totalFriendsWithData > 5 && (
                <div className="mt-3 flex items-center justify-between">
                  <p className="text-xs text-gray-500">
                    Showing top 5 of {totalFriendsWithData} friends by listens
                  </p>
                  <button
                    onClick={() => setShowFriendSelector(!showFriendSelector)}
                    className="text-xs text-[var(--green)] hover:text-white transition-colors"
                  >
                    {showFriendSelector ? "Hide" : "Select friends"}
                  </button>
                </div>
              )}
              {showFriendSelector && allFriends && (
                <div className="mt-2 card p-4 space-y-2 animate-slide-up">
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Choose friends to display</p>
                  {allFriends.map((f: any) => (
                    <label key={f.user_id} className="flex items-center gap-3 cursor-pointer text-sm">
                      <input
                        type="checkbox"
                        checked={selectedFriendIds ? selectedFriendIds.includes(f.user_id) : allFriends.indexOf(f) < 5}
                        onChange={(e) => {
                          const current = selectedFriendIds || allFriends.slice(0, 5).map((af: any) => af.user_id);
                          if (e.target.checked) {
                            setSelectedFriendIds([...current, f.user_id]);
                          } else {
                            setSelectedFriendIds(current.filter((id: string) => id !== f.user_id));
                          }
                        }}
                        className="accent-[var(--green)]"
                      />
                      <span className="text-gray-300">{f.user_name || f.user_id}</span>
                      <span className="text-gray-600 text-xs ml-auto">{f.total_listens} listens</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          );
        })()}
      </section>

      {/* Gatekeep Comparison */}
      {comparison?.entries?.length > 0 && (
        <section className="mb-10">
          <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-4">
            Who Listened First?
          </h2>
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
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-lg">
                      {entry.total_listens}{" "}
                      <span className="text-gray-500 font-normal text-sm">listens</span>
                    </div>
                    <div className="text-xs text-gray-500">
                      First: {new Date(entry.first_listen).toLocaleDateString("en-US", { month: "short", year: "numeric" })}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Challenge */}
      <section>
        <button onClick={handleChallenge} className="btn-primary">
          Challenge a Friend
        </button>

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
                onClick={() => {
                  navigator.clipboard.writeText(challenge.invite_code);
                  trackEvent("challenge_code_copied", { artist_id: artistId });
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                }}
                className="btn-secondary text-xs py-1.5 px-4"
              >
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
