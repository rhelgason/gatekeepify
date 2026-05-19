const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

const cache = new Map<string, { data: any; ts: number }>();
const CACHE_TTL = 30_000; // 30 seconds

function getCached<T>(key: string): T | null {
  const entry = cache.get(key);
  if (entry && Date.now() - entry.ts < CACHE_TTL) return entry.data as T;
  if (entry) cache.delete(key);
  return null;
}

function setCache(key: string, data: any) {
  cache.set(key, { data, ts: Date.now() });
}

async function cachedRequest<T>(path: string): Promise<T> {
  const cached = getCached<T>(path);
  if (cached) return cached;
  const data = await request<T>(path);
  setCache(path, data);
  return data;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("api-unreachable"));
    }
    throw new ApiError("Unable to connect to server", 0);
  }

  if (res.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
      window.location.href = "/";
    }
    throw new ApiError("Unauthorized", 401);
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.detail || "Request failed", res.status);
  }

  return res.json();
}

export const api = {
  getLoginUrl: (inviteCode?: string) => {
    const returnUrl = typeof window !== "undefined" ? window.location.origin : "";
    const params = new URLSearchParams();
    if (returnUrl) params.set("return_url", returnUrl);
    if (inviteCode) params.set("invite_code", inviteCode);
    const qs = params.toString();
    return request<{ auth_url: string }>(`/auth/login${qs ? `?${qs}` : ""}`);
  },

  getMe: () => request<{ user_id: string; user_name: string; email: string; image_url: string | null; created_at: string | null }>(
    "/auth/me"
  ),

  getTopTracks: (period = "all", limit = 10, offset = 0, targetUserId?: string) =>
    cachedRequest<any[]>(
      `/stats/top-tracks?period=${period}&limit=${limit}&offset=${offset}${targetUserId ? `&target_user_id=${targetUserId}` : ""}`
    ),

  getTopArtists: (period = "all", limit = 10, offset = 0, targetUserId?: string) =>
    cachedRequest<any[]>(
      `/stats/top-artists?period=${period}&limit=${limit}&offset=${offset}${targetUserId ? `&target_user_id=${targetUserId}` : ""}`
    ),

  getTopGenres: (period = "all", limit = 10, offset = 0, targetUserId?: string) =>
    cachedRequest<any[]>(
      `/stats/top-genres?period=${period}&limit=${limit}&offset=${offset}${targetUserId ? `&target_user_id=${targetUserId}` : ""}`
    ),

  getWrapped: (year?: number) =>
    cachedRequest<any>(`/stats/wrapped${year ? `?year=${year}` : ""}`),

  uploadBackfill: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<any>("/backfill/upload", { method: "POST", body: form });
  },

  getBackfillStatus: () => request<any>("/backfill/status"),

  getUploadStatus: () => request<any>("/backfill/upload-status"),

  cancelUpload: () => request<any>("/backfill/cancel-upload", { method: "POST" }),

  getFriends: () => request<any[]>("/friends"),

  createInvite: () =>
    request<{ invite_code: string }>("/friends/invite", { method: "POST" }),

  acceptInvite: (code: string) =>
    request<any>(`/friends/accept/${code}`, { method: "POST" }),

  searchUsers: (q: string) =>
    request<any[]>(`/friends/search-users?q=${encodeURIComponent(q)}`),

  sendFriendRequest: (toUserId: string) =>
    request<any>(`/friends/request?to_user_id=${encodeURIComponent(toUserId)}`, { method: "POST" }),

  getPendingRequests: () => request<any[]>("/friends/requests"),

  acceptFriendRequest: (requestId: number) =>
    request<any>(`/friends/requests/${requestId}/accept`, { method: "POST" }),

  declineFriendRequest: (requestId: number) =>
    request<any>(`/friends/requests/${requestId}/decline`, { method: "POST" }),

  getCompatibility: (friendId: string) =>
    cachedRequest<any>(`/friends/compatibility/${friendId}`),

  searchArtists: (q: string) => request<any[]>(`/search/artists?q=${encodeURIComponent(q)}`),

  searchSpotifyArtists: (q: string) => request<any[]>(`/search/spotify-artists?q=${encodeURIComponent(q)}`),

  searchTracks: (q: string) => request<any[]>(`/search/tracks?q=${encodeURIComponent(q)}`),

  getArtistDetail: (artistId: string) => cachedRequest<any>(`/search/artist/${artistId}`),

  resolveArtist: (name: string) =>
    request<{ artist_id: string; artist_name: string; resolved: string }>(
      `/search/resolve-artist?name=${encodeURIComponent(name)}`
    ),

  getTrackDetail: (trackId: string) => request<any>(`/search/track/${trackId}`),

  getTimeline: (artistId: string, mode: string = "personal") =>
    cachedRequest<any>(`/stats/timeline?artist_id=${artistId}&mode=${mode}`),

  getLastfmTimeline: (artistName: string) =>
    cachedRequest<any>(`/stats/lastfm-timeline?artist_name=${encodeURIComponent(artistName)}`),

  gatekeepArtist: (artistId: string) => cachedRequest<any>(`/gatekeep/artist/${artistId}`),

  gatekeepTrack: (trackId: string) => cachedRequest<any>(`/gatekeep/track/${trackId}`),

  getLeaderboard: () => cachedRequest<any>("/gatekeep/leaderboard"),

  getTrophies: () => cachedRequest<any>("/gatekeep/awards/trophies"),

  getHeadToHead: (friendId: string) =>
    cachedRequest<any>(`/gatekeep/awards/head-to-head?friend_id=${friendId}`),

  getFriendsFreshFinds: (days = 7) =>
    cachedRequest<any[]>(`/discover/friends-fresh-finds?days=${days}`),

  getYoureLateOn: () => cachedRequest<any[]>("/discover/youre-late-on"),

  getRisingArtists: () => cachedRequest<any[]>("/discover/rising"),

  getActivityFeed: (limit = 20, days = 7) =>
    request<any[]>(`/discover/feed?limit=${limit}&days=${days}`),

  createChallenge: (artistId: string) =>
    request<any>(`/gatekeep/challenge?artist_id=${artistId}`, { method: "POST" }),
};
