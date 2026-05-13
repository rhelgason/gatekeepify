"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";

export default function Upload() {
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [status, setStatus] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/");
      return;
    }
    api.getBackfillStatus().then(setStatus);
  }, [router]);

  async function handleFile(file: File) {
    if (!file.name.endsWith(".zip")) {
      setError("Please upload a ZIP file");
      return;
    }
    setUploading(true);
    setError("");
    setResult(null);
    try {
      const data = await api.uploadBackfill(file);
      setResult(data);
      api.getBackfillStatus().then(setStatus);
    } catch (e: any) {
      setError(e.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  return (
    <div className="animate-fade-in">
      <h1 className="text-3xl font-black mb-2">Upload History</h1>
      <p className="text-gray-500 mb-8 max-w-xl">
        Upload your Spotify data export to unlock your full listening history.
        Without this, we can only track your last 50 listens.
      </p>

      <div className="card p-6 mb-8">
        <h2 className="font-bold text-lg mb-3">How to get your data</h2>
        <ol className="text-gray-400 text-sm space-y-2 list-decimal list-inside">
          <li>
            Go to{" "}
            <a
              href="https://www.spotify.com/account/privacy/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[var(--green)] hover:underline"
            >
              Spotify Account &gt; Privacy Settings
            </a>
          </li>
          <li>Request &ldquo;Extended streaming history&rdquo;</li>
          <li>Spotify sends you a ZIP file within a few days</li>
          <li>Upload that ZIP file below</li>
        </ol>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInput.current?.click()}
        className={`card cursor-pointer p-16 text-center transition-all duration-200 ${
          dragging
            ? "border-[var(--green)] bg-[var(--green-dim)] scale-[1.01]"
            : "hover:border-white/10 hover:bg-[#1a1a1a]"
        }`}
      >
        <input
          ref={fileInput}
          type="file"
          accept=".zip"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />
        {uploading ? (
          <div>
            <div className="text-3xl mb-3 animate-pulse">📦</div>
            <p className="text-gray-400">Uploading and processing...</p>
          </div>
        ) : (
          <div>
            <div className="text-3xl mb-3">📁</div>
            <p className="text-gray-300 font-medium mb-1">
              Drop your ZIP file here, or click to browse
            </p>
            <p className="text-gray-600 text-sm">Max 100 MB</p>
          </div>
        )}
      </div>

      {error && <p className="text-red-400 mt-4">{error}</p>}

      {result && (
        <div className="card mt-6 p-6 animate-slide-up">
          <h2 className="font-bold text-[var(--green)] mb-4 text-lg">Upload Complete</h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="stat-number">{result.total_listens_processed.toLocaleString()}</div>
              <div className="text-gray-500 text-sm">Processed</div>
            </div>
            <div>
              <div className="stat-number text-[var(--green)]">
                {result.total_listens_accepted.toLocaleString()}
              </div>
              <div className="text-gray-500 text-sm">Accepted</div>
            </div>
            <div>
              <div className="stat-number text-red-400">
                {result.total_listens_rejected.toLocaleString()}
              </div>
              <div className="text-gray-500 text-sm">Rejected</div>
            </div>
          </div>
          {Object.keys(result.rejection_reasons || {}).length > 0 && (
            <div className="mt-4 text-xs text-gray-600 bg-white/5 rounded-xl p-3">
              Rejections:{" "}
              {Object.entries(result.rejection_reasons)
                .map(([k, v]) => `${k}: ${v}`)
                .join(", ")}
            </div>
          )}
        </div>
      )}

      {status && (
        <div className="card mt-6 p-6">
          <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-3">
            Your Data
          </h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-black">{status.total_listens.toLocaleString()}</div>
              <div className="text-gray-600 text-sm">Total Listens</div>
            </div>
            <div>
              <div className="text-2xl font-black">{status.total_tracks.toLocaleString()}</div>
              <div className="text-gray-600 text-sm">Unique Tracks</div>
            </div>
            <div>
              <div className="text-2xl font-black">{status.tracks_missing_metadata.toLocaleString()}</div>
              <div className="text-gray-600 text-sm">Awaiting Metadata</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
