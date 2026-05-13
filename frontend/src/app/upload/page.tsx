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
    <div>
      <h1 className="text-2xl font-bold mb-2">Upload Listening History</h1>
      <p className="text-gray-500 mb-6">
        Upload your Spotify data export to backfill your full listening
        history. Without this, we can only track listens from when you signed
        up.
      </p>

      <div className="bg-gray-900 rounded-lg p-4 mb-6">
        <h2 className="font-semibold mb-2">How to get your data</h2>
        <ol className="text-gray-400 text-sm space-y-1 list-decimal list-inside">
          <li>Go to your Spotify Account &gt; Privacy Settings</li>
          <li>Request &ldquo;Extended streaming history&rdquo;</li>
          <li>Spotify sends you a ZIP file within a few days</li>
          <li>Upload that ZIP file here</li>
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
        className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition ${
          dragging
            ? "border-green-500 bg-green-500/5"
            : "border-gray-700 hover:border-gray-600"
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
          <p className="text-gray-400">Uploading and processing...</p>
        ) : (
          <div>
            <p className="text-gray-300 mb-1">
              Drop your ZIP file here, or click to browse
            </p>
            <p className="text-gray-600 text-sm">
              Accepts Spotify data export ZIP files (max 100 MB)
            </p>
          </div>
        )}
      </div>

      {error && (
        <p className="text-red-400 mt-3">{error}</p>
      )}

      {result && (
        <div className="mt-6 bg-gray-900 rounded-lg p-4">
          <h2 className="font-semibold mb-3 text-green-400">Upload Complete</h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold">
                {result.total_listens_processed}
              </div>
              <div className="text-gray-500 text-sm">Processed</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-400">
                {result.total_listens_accepted}
              </div>
              <div className="text-gray-500 text-sm">Accepted</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-red-400">
                {result.total_listens_rejected}
              </div>
              <div className="text-gray-500 text-sm">Rejected</div>
            </div>
          </div>
          {Object.keys(result.rejection_reasons || {}).length > 0 && (
            <div className="mt-3 text-sm text-gray-500">
              Rejections:{" "}
              {Object.entries(result.rejection_reasons)
                .map(([k, v]) => `${k}: ${v}`)
                .join(", ")}
            </div>
          )}
        </div>
      )}

      {status && (
        <div className="mt-6 bg-gray-900 rounded-lg p-4">
          <h2 className="font-semibold mb-2">Current Status</h2>
          <div className="text-sm text-gray-400 space-y-1">
            <p>Total listens: {status.total_listens.toLocaleString()}</p>
            <p>Unique tracks: {status.total_tracks.toLocaleString()}</p>
            <p>
              Tracks awaiting metadata:{" "}
              {status.tracks_missing_metadata.toLocaleString()}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
