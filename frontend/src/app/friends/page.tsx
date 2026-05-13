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
    return <p className="text-gray-400 mt-12 text-center">Loading...</p>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Friends</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-gray-900 rounded-lg p-4">
          <h2 className="font-semibold mb-3">Invite a Friend</h2>
          <button
            onClick={handleCreateInvite}
            className="bg-green-500 hover:bg-green-400 text-black font-semibold px-4 py-2 rounded transition w-full"
          >
            Generate Invite Code
          </button>
          {inviteCode && (
            <div className="mt-3 flex items-center gap-2">
              <code className="bg-gray-800 px-3 py-2 rounded text-green-400 text-sm flex-1">
                {inviteCode}
              </code>
              <button
                onClick={() => navigator.clipboard.writeText(inviteCode)}
                className="text-xs text-gray-500 hover:text-gray-300 whitespace-nowrap"
              >
                Copy
              </button>
            </div>
          )}
        </div>

        <div className="bg-gray-900 rounded-lg p-4">
          <h2 className="font-semibold mb-3">Accept an Invite</h2>
          <div className="flex gap-2">
            <input
              type="text"
              value={acceptCode}
              onChange={(e) => setAcceptCode(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAcceptInvite()}
              placeholder="Paste invite code..."
              className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-gray-100 placeholder-gray-500 focus:border-green-500 focus:outline-none text-sm"
            />
            <button
              onClick={handleAcceptInvite}
              className="bg-green-500 hover:bg-green-400 text-black font-semibold px-4 py-2 rounded transition"
            >
              Accept
            </button>
          </div>
          {message && (
            <p className="text-sm mt-2 text-gray-400">{message}</p>
          )}
        </div>
      </div>

      <h2 className="font-semibold mb-3">
        Your Friends ({friends.length})
      </h2>
      {friends.length === 0 ? (
        <p className="text-gray-500">
          No friends yet. Generate an invite code and share it!
        </p>
      ) : (
        <div className="space-y-2">
          {friends.map((f) => (
            <div
              key={f.user_id}
              className="flex justify-between bg-gray-900 rounded px-4 py-3"
            >
              <span>{f.user_name || f.user_id}</span>
              <span className="text-gray-500 text-sm">
                Friends since{" "}
                {new Date(f.friends_since).toLocaleDateString()}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
