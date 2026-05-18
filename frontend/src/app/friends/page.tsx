"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import { trackEvent } from "@/lib/track";
import Link from "next/link";

export default function Friends() {
  const router = useRouter();
  const [friends, setFriends] = useState<any[]>([]);
  const [pendingRequests, setPendingRequests] = useState<any[]>([]);
  const [inviteCode, setInviteCode] = useState("");
  const [copied, setCopied] = useState(false);
  const [userQuery, setUserQuery] = useState("");
  const [userResults, setUserResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const [message, setMessage] = useState("");
  const [compatScores, setCompatScores] = useState<Record<string, number>>({});
  const [compatLoading, setCompatLoading] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/");
      return;
    }
    loadData();
  }, [router]);

  async function loadData() {
    const [f, r] = await Promise.all([
      api.getFriends(),
      api.getPendingRequests(),
    ]);
    setFriends(f);
    setPendingRequests(r);
    setLoading(false);

    const loadingInit: Record<string, boolean> = {};
    for (const friend of f) {
      loadingInit[friend.user_id] = true;
    }
    setCompatLoading(loadingInit);

    for (const friend of f) {
      api.getCompatibility(friend.user_id).then(c => {
        setCompatScores(prev => ({ ...prev, [friend.user_id]: c.score }));
      }).catch(() => {}).finally(() => {
        setCompatLoading(prev => ({ ...prev, [friend.user_id]: false }));
      });
    }
  }

  async function handleCreateInvite() {
    trackEvent("invite_generated");
    const data = await api.createInvite();
    setInviteCode(data.invite_code);
  }

  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!userQuery.trim()) { setUserResults([]); return; }
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    searchDebounceRef.current = setTimeout(() => {
      handleSearchUsers(userQuery.trim());
    }, 300);
    return () => { if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current); };
  }, [userQuery]);

  async function handleSearchUsers(q?: string) {
    const searchQuery = q || userQuery.trim();
    if (!searchQuery) return;
    setSearching(true);
    trackEvent("friend_search", { query: searchQuery });
    const data = await api.searchUsers(searchQuery);
    setUserResults(data);
    setSearching(false);
  }

  async function handleSendRequest(toUserId: string) {
    trackEvent("friend_request_sent", { to_user: toUserId }, "user", toUserId);
    try {
      await api.sendFriendRequest(toUserId);
      setUserResults(prev =>
        prev.map(u => u.user_id === toUserId ? { ...u, request_sent: true } : u)
      );
    } catch (e) {
      if (e instanceof ApiError) setMessage(e.message);
    }
  }

  async function handleAcceptRequest(requestId: number) {
    trackEvent("friend_request_accepted", { request_id: requestId });
    await api.acceptFriendRequest(requestId);
    loadData();
  }

  async function handleDeclineRequest(requestId: number) {
    trackEvent("friend_request_declined", { request_id: requestId });
    await api.declineFriendRequest(requestId);
    loadData();
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-gray-500 animate-pulse text-lg">Loading...</div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <h1 className="text-3xl font-black mb-8">Friends</h1>

      {/* Pending Requests */}
      {pendingRequests.length > 0 && (
        <section className="mb-8">
          <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-4">
            Friend Requests ({pendingRequests.length})
          </h2>
          <div className="space-y-2">
            {pendingRequests.map((r) => (
              <div key={r.id} className="card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <span className="font-medium">{r.from_user_name || r.from_user_id}</span>
                  <span className="text-gray-600 text-sm ml-2">
                    {new Date(r.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleAcceptRequest(r.id)}
                    className="btn-primary text-xs py-1.5 px-4"
                  >
                    Accept
                  </button>
                  <button
                    onClick={() => handleDeclineRequest(r.id)}
                    className="btn-secondary text-xs py-1.5 px-4"
                  >
                    Decline
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Find Friends */}
      <section className="mb-8">
        <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-4">
          Find Friends
        </h2>
        <div className="relative mb-4">
          <input
            type="text"
            value={userQuery}
            onChange={(e) => setUserQuery(e.target.value)}
            placeholder="Search by name..."
            className="w-full bg-white/5 border border-white/10 rounded-full px-6 py-3 text-gray-100 placeholder-gray-600 focus:border-[var(--green)] focus:outline-none text-sm transition-all"
          />
          {searching && (
            <div className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 text-xs animate-pulse">searching...</div>
          )}
        </div>
        {userResults.length > 0 && (
          <div className="space-y-2 animate-slide-up">
            {userResults.map((u) => (
              <div key={u.user_id} className="card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-sm text-gray-500">
                    {(u.user_name || u.user_id)[0]?.toUpperCase()}
                  </div>
                  <span className="font-medium">{u.user_name || u.user_id}</span>
                </div>
                {u.is_friend ? (
                  <Link href={`/profile/${u.user_id}`} className="btn-secondary text-xs py-1.5 px-4">
                    View Profile
                  </Link>
                ) : u.request_sent ? (
                  <span className="text-gray-500 text-xs">Request sent</span>
                ) : (
                  <button
                    onClick={() => handleSendRequest(u.user_id)}
                    className="btn-primary text-xs py-1.5 px-4"
                  >
                    Add Friend
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Invite Link */}
      <section className="mb-10">
        <div className="card p-6">
          <h2 className="font-bold text-lg mb-3">Invite a Friend</h2>
          <p className="text-gray-500 text-sm mb-4">
            One click to copy an invite link with a message. Send it to anyone.
          </p>
          <button
            onClick={async () => {
              trackEvent("invite_generated");
              const data = await api.createInvite();
              const link = `${window.location.origin}/invite/${data.invite_code}`;
              const message = `Come prove your music taste on Gatekeepify: ${link}`;
              await navigator.clipboard.writeText(message);
              trackEvent("invite_link_copied");
              setCopied(true);
              setTimeout(() => setCopied(false), 3000);
            }}
            className="btn-primary w-full"
          >
            {copied ? "Copied to clipboard!" : "Copy Invite Link"}
          </button>
        </div>
      </section>

      {/* Friend List */}
      <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-4">
        Your Friends ({friends.length})
      </h2>
      {friends.length === 0 ? (
        <div className="card p-12 text-center">
          <p className="text-gray-400 text-lg mb-2">No friends yet</p>
          <p className="text-gray-600 text-sm">
            Search for friends above or share an invite code!
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {friends.map((f) => (
            <Link
              key={f.user_id}
              href={`/profile/${f.user_id}`}
              className="card-hover flex justify-between items-center px-5 py-4"
            >
              <div className="flex items-center gap-3">
                {f.image_url ? (
                  <img src={f.image_url} alt="" className="w-10 h-10 rounded-full object-cover" />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-sm text-gray-500">
                    {(f.user_name || f.user_id)[0]?.toUpperCase()}
                  </div>
                )}
                <div>
                  <span className="font-medium block">{f.user_name || f.user_id}</span>
                  <span className="text-gray-600 text-xs">
                    Since {new Date(f.friends_since).toLocaleDateString()}
                  </span>
                </div>
              </div>
              {compatScores[f.user_id] !== undefined ? (
                <span className={`text-sm font-bold ${
                  compatScores[f.user_id] >= 70 ? "text-[var(--green)]" :
                  compatScores[f.user_id] >= 40 ? "text-yellow-400" : "text-red-400"
                }`}>
                  {compatScores[f.user_id]}% match
                </span>
              ) : compatLoading[f.user_id] ? (
                <div className="w-12 h-5 bg-white/5 rounded-full animate-pulse" />
              ) : null}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
