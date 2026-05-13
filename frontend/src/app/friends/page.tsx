"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";

export default function Friends() {
  const router = useRouter();
  const [friends, setFriends] = useState<any[]>([]);
  const [inviteCode, setInviteCode] = useState("");
  const [acceptCode, setAcceptCode] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/");
      return;
    }
    loadFriends();
  }, [router]);

  async function loadFriends() {
    const data = await api.getFriends();
    setFriends(data);
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
      loadFriends();
    } catch (e) {
      if (e instanceof ApiError) {
        setMessage(e.message);
      }
    }
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

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10">
        <div className="card p-6">
          <h2 className="font-bold text-lg mb-4">Invite a Friend</h2>
          <button onClick={handleCreateInvite} className="btn-primary w-full">
            Generate Invite Code
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
          <h2 className="font-bold text-lg mb-4">Accept an Invite</h2>
          <div className="flex gap-2">
            <input
              type="text"
              value={acceptCode}
              onChange={(e) => setAcceptCode(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAcceptInvite()}
              placeholder="Paste invite code..."
              className="flex-1 bg-white/5 border border-white/10 rounded-full px-5 py-3 text-gray-100 placeholder-gray-600 focus:border-[var(--green)] focus:outline-none text-sm transition-all"
            />
            <button onClick={handleAcceptInvite} className="btn-primary">
              Accept
            </button>
          </div>
          {message && (
            <p className="text-sm mt-3 text-gray-400">{message}</p>
          )}
        </div>
      </div>

      <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-4">
        Your Friends ({friends.length})
      </h2>
      {friends.length === 0 ? (
        <div className="card p-12 text-center">
          <p className="text-gray-400 text-lg mb-2">No friends yet</p>
          <p className="text-gray-600 text-sm">
            Generate an invite code above and share it!
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {friends.map((f) => (
            <div
              key={f.user_id}
              className="card flex justify-between items-center px-5 py-4"
            >
              <span className="font-medium">{f.user_name || f.user_id}</span>
              <span className="text-gray-600 text-sm">
                Since {new Date(f.friends_since).toLocaleDateString()}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
