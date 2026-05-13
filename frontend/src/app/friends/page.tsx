"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import Link from "next/link";

export default function Friends() {
  const router = useRouter();
  const [friends, setFriends] = useState<any[]>([]);
  const [pendingRequests, setPendingRequests] = useState<any[]>([]);
  const [inviteCode, setInviteCode] = useState("");
  const [acceptCode, setAcceptCode] = useState("");
  const [userQuery, setUserQuery] = useState("");
  const [userResults, setUserResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const [message, setMessage] = useState("");
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
  }

  async function handleCreateInvite() {
    const data = await api.createInvite();
    setInviteCode(data.invite_code);
    setMessage("");
  }

  async function handleAcceptInvite() {
    if (!acceptCode.trim()) return;
    try {
      await api.acceptInvite(acceptCode.trim());
      setMessage("Friend added!");
      setAcceptCode("");
      loadData();
    } catch (e) {
      if (e instanceof ApiError) setMessage(e.message);
    }
  }

  async function handleSearchUsers() {
    if (!userQuery.trim()) return;
    setSearching(true);
    const data = await api.searchUsers(userQuery);
    setUserResults(data);
    setSearching(false);
  }

  async function handleSendRequest(toUserId: string) {
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
    await api.acceptFriendRequest(requestId);
    loadData();
  }

  async function handleDeclineRequest(requestId: number) {
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
              <div key={r.id} className="card p-4 flex items-center justify-between">
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
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={userQuery}
            onChange={(e) => setUserQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearchUsers()}
            placeholder="Search by name..."
            className="flex-1 bg-white/5 border border-white/10 rounded-full px-6 py-3 text-gray-100 placeholder-gray-600 focus:border-[var(--green)] focus:outline-none text-sm transition-all"
          />
          <button
            onClick={handleSearchUsers}
            disabled={searching}
            className="btn-primary text-sm"
          >
            {searching ? "..." : "Search"}
          </button>
        </div>
        {userResults.length > 0 && (
          <div className="space-y-2 animate-slide-up">
            {userResults.map((u) => (
              <div key={u.user_id} className="card p-4 flex items-center justify-between">
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

      {/* Invite Code */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10">
        <div className="card p-6">
          <h2 className="font-bold text-lg mb-4">Share Invite Code</h2>
          <p className="text-gray-500 text-sm mb-3">
            For friends not yet on Gatekeepify
          </p>
          <button onClick={handleCreateInvite} className="btn-primary w-full">
            Generate Code
          </button>
          {inviteCode && (
            <div className="mt-4 flex items-center gap-2 bg-white/5 rounded-xl p-3">
              <code className="font-mono text-[var(--green)] text-sm flex-1 truncate">
                {inviteCode}
              </code>
              <button
                onClick={() => navigator.clipboard.writeText(inviteCode)}
                className="btn-secondary text-xs py-1.5 px-4"
              >
                Copy
              </button>
            </div>
          )}
        </div>

        <div className="card p-6">
          <h2 className="font-bold text-lg mb-4">Have a Code?</h2>
          <p className="text-gray-500 text-sm mb-3">
            Paste an invite code from a friend
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              value={acceptCode}
              onChange={(e) => setAcceptCode(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAcceptInvite()}
              placeholder="Paste code..."
              className="flex-1 bg-white/5 border border-white/10 rounded-full px-5 py-3 text-gray-100 placeholder-gray-600 focus:border-[var(--green)] focus:outline-none text-sm transition-all"
            />
            <button onClick={handleAcceptInvite} className="btn-primary">
              Accept
            </button>
          </div>
          {message && <p className="text-sm mt-3 text-gray-400">{message}</p>}
        </div>
      </div>

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
                <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-sm text-gray-500">
                  {(f.user_name || f.user_id)[0]?.toUpperCase()}
                </div>
                <span className="font-medium">{f.user_name || f.user_id}</span>
              </div>
              <span className="text-gray-600 text-sm">
                Since {new Date(f.friends_since).toLocaleDateString()}
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
