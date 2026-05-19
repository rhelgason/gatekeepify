export interface ShareCardData {
  artistName: string;
  imageUrl?: string | null;
  statNumber: string;
  statLabel: string;
  contextLine: string;
  secondaryStat?: string;
}

const W = 1080;
const H = 1080;
const GREEN = "#1DB954";

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = url;
  });
}

export async function generateShareCard(data: ShareCardData): Promise<Blob> {
  await document.fonts.ready;

  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d")!;

  // Background gradient
  const bg = ctx.createLinearGradient(0, 0, W, H);
  bg.addColorStop(0, "#0a0a0a");
  bg.addColorStop(0.5, "#111318");
  bg.addColorStop(1, "#0d1117");
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);

  // Subtle noise-like texture
  const accent = ctx.createRadialGradient(W * 0.3, H * 0.2, 0, W * 0.3, H * 0.2, W * 0.6);
  accent.addColorStop(0, "rgba(29, 185, 84, 0.06)");
  accent.addColorStop(1, "transparent");
  ctx.fillStyle = accent;
  ctx.fillRect(0, 0, W, H);

  // Artist image or initial
  const imgSize = 260;
  const imgX = (W - imgSize) / 2;
  const imgY = 140;

  let hasImage = false;
  if (data.imageUrl) {
    try {
      const img = await loadImage(data.imageUrl);
      ctx.save();
      ctx.beginPath();
      ctx.arc(imgX + imgSize / 2, imgY + imgSize / 2, imgSize / 2, 0, Math.PI * 2);
      ctx.clip();
      ctx.drawImage(img, imgX, imgY, imgSize, imgSize);
      ctx.restore();
      hasImage = true;
    } catch {
      // fall through to initial
    }
  }

  if (!hasImage) {
    ctx.beginPath();
    ctx.arc(imgX + imgSize / 2, imgY + imgSize / 2, imgSize / 2, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(255,255,255,0.05)";
    ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,0.3)";
    ctx.font = `bold 100px system-ui, -apple-system, sans-serif`;
    ctx.textAlign = "center";
    ctx.fillText(data.artistName[0]?.toUpperCase() || "?", W / 2, imgY + imgSize / 2 + 35);
  }

  // Ring around image
  ctx.beginPath();
  ctx.arc(imgX + imgSize / 2, imgY + imgSize / 2, imgSize / 2 + 3, 0, Math.PI * 2);
  ctx.strokeStyle = "rgba(255,255,255,0.1)";
  ctx.lineWidth = 2;
  ctx.stroke();

  // Artist name
  ctx.textAlign = "center";
  ctx.fillStyle = "#ffffff";
  ctx.font = `bold 52px system-ui, -apple-system, sans-serif`;
  ctx.fillText(truncate(data.artistName, 28), W / 2, 480);

  // Stat number (big)
  ctx.fillStyle = "#ffffff";
  ctx.font = `bold 140px system-ui, -apple-system, sans-serif`;
  ctx.fillText(data.statNumber, W / 2, 640);

  // Stat label
  ctx.fillStyle = "#999999";
  ctx.font = `500 36px system-ui, -apple-system, sans-serif`;
  ctx.fillText(data.statLabel, W / 2, 690);

  // Context line
  ctx.fillStyle = "#666666";
  ctx.font = `400 28px system-ui, -apple-system, sans-serif`;
  ctx.fillText(data.contextLine, W / 2, 745);

  // Secondary stat
  if (data.secondaryStat) {
    ctx.fillStyle = "#555555";
    ctx.font = `400 26px system-ui, -apple-system, sans-serif`;
    ctx.fillText(data.secondaryStat, W / 2, 790);
  }

  // Bottom branding
  ctx.fillStyle = GREEN;
  ctx.font = `900 38px system-ui, -apple-system, sans-serif`;
  ctx.fillText("gatekeepify", W / 2, 970);

  ctx.fillStyle = "#444444";
  ctx.font = `400 22px system-ui, -apple-system, sans-serif`;
  ctx.fillText("Prove you listened first.", W / 2, 1005);

  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error("Canvas toBlob failed"));
    }, "image/png");
  });
}

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max - 1) + "…" : s;
}
