"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";
import { trackEvent } from "@/lib/track";

const PHASE_LABELS: Record<string, string> = {
  queued: "Queued...",
  extracting: "Extracting ZIP...",
  validating: "Validating listens...",
  inserting: "Writing to database...",
  enriching: "Fetching track metadata from Spotify...",
  analyzing: "Running anomaly detection...",
  done: "Complete!",
  error: "Failed",
};

export default function Upload() {
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [job, setJob] = useState<any>(null);
  const [status, setStatus] = useState<any>(null);
  const [error, setError] = useState("");
  const [checkingJob, setCheckingJob] = useState(true);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/");
      return;
    }
    api.getBackfillStatus().then(setStatus);
    api.getUploadStatus().then((j) => {
      if (j.status === "pending" || j.status === "running") {
        setJob(j);
        startPolling();
      } else if (j.status === "completed" || j.status === "error") {
        setJob(j);
      }
    }).catch(() => {}).finally(() => setCheckingJob(false));

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [router]);

  function startPolling() {
    if (pollRef.current) clearInterval(pollRef.current);
    let noneCount = 0;
    pollRef.current = setInterval(async () => {
      try {
        const j = await api.getUploadStatus();
        if (j.status === "none") {
          noneCount++;
          if (noneCount >= 3) {
            setJob(null);
            setError("Upload job was lost. Please try again.");
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;
          }
          return;
        }
        noneCount = 0;
        setJob(j);
        if (j.status === "completed" || j.status === "error") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
          api.getBackfillStatus().then(setStatus);
          if (j.status === "completed") {
            trackEvent("upload_completed", { accepted: j.accepted, rejected: j.rejected });
          }
        }
      } catch {
        // keep polling
      }
    }, 2000);
  }

  async function handleFile(file: File) {
    if (!file.name.endsWith(".zip")) {
      trackEvent("upload_invalid_file", { filename: file.name });
      setError("Please upload a ZIP file");
      return;
    }
    trackEvent("upload_started", { filename: file.name, size_bytes: file.size });
    setUploading(true);
    setError("");
    setJob(null);
    try {
      const data = await api.uploadBackfill(file);
      setJob({ status: "pending", phase: "queued", progress: 0 });
      startPolling();
    } catch (e: any) {
      trackEvent("upload_failed", { error: e.message });
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

  const isProcessing = job && (job.status === "pending" || job.status === "running");
  const isDone = job?.status === "completed";
  const isFailed = job?.status === "error";

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

      {checkingJob ? (
        <div className="card p-16 text-center">
          <div className="h-8 w-8 mx-auto bg-white/5 rounded animate-pulse mb-3" />
          <div className="h-4 w-48 mx-auto bg-white/5 rounded animate-pulse" />
        </div>
      ) : !isProcessing && (
        <div className="card overflow-hidden">
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInput.current?.click()}
            className={`cursor-pointer p-16 text-center transition-all duration-200 ${
              dragging
                ? "bg-[var(--green-dim)]"
                : "hover:bg-[#1a1a1a]"
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
                <p className="text-gray-400">Uploading file to server...</p>
                <p className="text-orange-400 text-xs mt-2">Do not navigate away until upload completes.</p>
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
          {(error || isFailed) && (
            <div className="border-t border-white/5 px-6 py-4 flex items-center justify-between">
              <p className="text-red-400 text-sm">
                {error || job?.error || "Upload failed. Please try again."}
              </p>
              <button
                onClick={(e) => { e.stopPropagation(); setError(""); setJob(null); }}
                className="text-gray-600 hover:text-gray-400 text-xs ml-3 flex-shrink-0"
              >
                Dismiss
              </button>
            </div>
          )}
        </div>
      )}

      <div className="card mt-6 p-6">
        <h2 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-3">
          Your Data
        </h2>
        <div className="grid grid-cols-3 gap-4 text-center mb-4">
          {status ? (
            <>
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
            </>
          ) : (
            <>
              <div>
                <div className="h-8 w-16 mx-auto bg-white/5 rounded animate-pulse" />
                <div className="text-gray-600 text-sm mt-1">Total Listens</div>
              </div>
              <div>
                <div className="h-8 w-16 mx-auto bg-white/5 rounded animate-pulse" />
                <div className="text-gray-600 text-sm mt-1">Unique Tracks</div>
              </div>
              <div>
                <div className="h-8 w-16 mx-auto bg-white/5 rounded animate-pulse" />
                <div className="text-gray-600 text-sm mt-1">Awaiting Metadata</div>
              </div>
            </>
          )}
        </div>

        {isProcessing && (
          <div className="border-t border-white/5 pt-4 animate-slide-up">
            <div className="flex items-center gap-3 mb-3">
              <div className="text-lg animate-pulse">⚙️</div>
              <div>
                <p className="font-bold text-sm">Processing your data...</p>
                <p className="text-gray-600 text-xs">You can navigate away — this runs in the background.</p>
              </div>
            </div>
            <div className="w-full bg-white/5 rounded-full h-2.5 mb-2 overflow-hidden">
              <div
                className="h-full bg-[var(--green)] rounded-full transition-all duration-500"
                style={{ width: `${job.progress || 0}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-gray-500">
              <span>{PHASE_LABELS[job.phase] || job.phase}</span>
              <span>{job.progress || 0}%</span>
            </div>
            {job.total_listens && (
              <p className="text-xs text-gray-600 mt-1">
                {job.total_listens.toLocaleString()} listens found
                {job.inserted != null && ` · ${job.inserted.toLocaleString()} inserted so far`}
                {job.phase === "enriching" && job.enrich_total != null && (
                  <> · Enriching {(job.enrich_done || 0).toLocaleString()} / {job.enrich_total.toLocaleString()} tracks</>
                )}
              </p>
            )}
            <button
              onClick={async () => {
                try {
                  await api.cancelUpload();
                  setJob(null);
                  if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
                  api.getBackfillStatus().then(setStatus);
                } catch {}
              }}
              className="text-gray-600 hover:text-red-400 text-xs mt-3 transition-colors"
            >
              Cancel upload
            </button>
          </div>
        )}

        {isDone && (
          <div className="border-t border-white/5 pt-4 animate-slide-up">
            <p className="text-[var(--green)] font-bold text-sm mb-3">Last upload complete</p>
            <div className="grid grid-cols-3 gap-3 text-center text-xs">
              <div>
                <div className="font-bold text-sm">{(job.total_listens || 0).toLocaleString()}</div>
                <div className="text-gray-600">Processed</div>
              </div>
              <div>
                <div className="font-bold text-sm text-[var(--green)]">{(job.accepted || 0).toLocaleString()}</div>
                <div className="text-gray-600">Accepted</div>
              </div>
              <div>
                <div className="font-bold text-sm text-red-400">{(job.rejected || 0).toLocaleString()}</div>
                <div className="text-gray-600">Rejected</div>
              </div>
            </div>
            {job.rejection_reasons && Object.keys(job.rejection_reasons).length > 0 && (
              <div className="mt-3 text-xs text-gray-600 bg-white/5 rounded-lg p-2">
                Rejections: {Object.entries(job.rejection_reasons).map(([k, v]) => `${k}: ${v}`).join(", ")}
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
