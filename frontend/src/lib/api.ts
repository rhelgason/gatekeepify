const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
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

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

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
  getLoginUrl: () => {
    const returnUrl = typeof window !== "undefined" ? window.location.origin : "";
    const params = returnUrl ? `?return_url=${encodeURIComponent(returnUrl)}` : "";
    return request<{ auth_url: string }>(`/auth/login${params}`);
  },

  getMe: () => request<{ user_id: string; user_name: string; email: string }>(
    "/auth/me"
  ),

  getTopTracks: (period = "all", limit = 10, offset = 0) =>
    request<any[]>(
      `/stats/top-tracks?period=${period}&limit=${limit}&offset=${offset}`
    ),

  getTopArtists: (period = "all", limit = 10, offset = 0) =>
    request<any[]>(
      `/stats/top-artists?period=${period}&limit=${limit}&offset=${offset}`
    ),

  getTopGenres: (period = "all", limit = 10, offset = 0) =>
    request<any[]>(
      `/stats/top-genres?period=${period}&limit=${limit}&offset=${offset}`
    ),

  getWrapped: (year?: number) =>
    request<any>(`/stats/wrapped${year ? `?year=${year}` : ""}`),

  uploadBackfill: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<any>("/backfill/upload", { method: "POST", body: form });
  },

  getBackfillStatus: () => request<any>("/backfill/status"),

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

  searchArtists: (q: string) => request<any[]>(`/search/artists?q=${encodeURIComponent(q)}`),

  searchTracks: (q: string) => request<any[]>(`/search/tracks?q=${encodeURIComponent(q)}`),

  getArtistDetail: (artistId: string) => request<any>(`/search/artist/${artistId}`),

  resolveArtist: (name: string) =>
    request<{ artist_id: string; artist_name: string; resolved: string }>(
      `/search/resolve-artist?name=${encodeURIComponent(name)}`
    ),

  getTrackDetail: (trackId: string) => request<any>(`/search/track/${trackId}`),

  getTimeline: (artistId: string, mode: string = "personal") =>
    request<any>(`/stats/timeline?artist_id=${artistId}&mode=${mode}`),

  getLastfmTimeline: (artistName: string) =>
    request<any>(`/stats/lastfm-timeline?artist_name=${encodeURIComponent(artistName)}`),

  gatekeepArtist: (artistId: string) => request<any>(`/gatekeep/artist/${artistId}`),

  gatekeepTrack: (trackId: string) => request<any>(`/gatekeep/track/${trackId}`),

  getLeaderboard: () => request<any>("/gatekeep/leaderboard"),

  createChallenge: (artistId: string) =>
    request<any>(`/gatekeep/challenge?artist_id=${artistId}`, { method: "POST" }),
};
