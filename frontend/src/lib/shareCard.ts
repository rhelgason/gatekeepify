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

function getDominantColor(img: HTMLImageElement): [number, number, number] {
  const c = document.createElement("canvas");
  c.width = 50;
  c.height = 50;
  const ctx = c.getContext("2d")!;
  ctx.drawImage(img, 0, 0, 50, 50);
  const data = ctx.getImageData(0, 0, 50, 50).data;
  let r = 0, g = 0, b = 0, count = 0;
  for (let i = 0; i < data.length; i += 16) {
    const pr = data[i], pg = data[i + 1], pb = data[i + 2];
    if (pr + pg + pb > 30 && pr + pg + pb < 700) {
      r += pr; g += pg; b += pb; count++;
    }
  }
  if (count === 0) return [29, 185, 84];
  return [Math.round(r / count), Math.round(g / count), Math.round(b / count)];
}

export async function generateShareCard(data: ShareCardData): Promise<Blob> {
  await document.fonts.ready;

  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d")!;

  let accentR = 29, accentG = 185, accentB = 84;
  let img: HTMLImageElement | null = null;

  if (data.imageUrl) {
    try {
      img = await loadImage(data.imageUrl);
      [accentR, accentG, accentB] = getDominantColor(img);
    } catch {
      // no image
    }
  }

  // Dark base
  ctx.fillStyle = "#0a0a0a";
  ctx.fillRect(0, 0, W, H);

  // Blurred background image
  if (img) {
    ctx.save();
    ctx.globalAlpha = 0.35;
    ctx.filter = "blur(60px) saturate(1.5)";
    ctx.drawImage(img, -100, -100, W + 200, H + 200);
    ctx.restore();

    // Dark overlay
    const overlay = ctx.createLinearGradient(0, 0, 0, H);
    overlay.addColorStop(0, "rgba(10,10,10,0.4)");
    overlay.addColorStop(0.5, "rgba(10,10,10,0.7)");
    overlay.addColorStop(1, "rgba(10,10,10,0.95)");
    ctx.fillStyle = overlay;
    ctx.fillRect(0, 0, W, H);
  }

  // Accent glow at top
  const glow = ctx.createRadialGradient(W / 2, 200, 0, W / 2, 200, 500);
  glow.addColorStop(0, `rgba(${accentR},${accentG},${accentB},0.15)`);
  glow.addColorStop(1, "transparent");
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, W, H);

  // Artist image circle
  const imgSize = 240;
  const imgX = (W - imgSize) / 2;
  const imgY = 130;

  if (img) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(imgX + imgSize / 2, imgY + imgSize / 2, imgSize / 2, 0, Math.PI * 2);
    ctx.clip();
    ctx.drawImage(img, imgX, imgY, imgSize, imgSize);
    ctx.restore();

    // Ring
    ctx.beginPath();
    ctx.arc(imgX + imgSize / 2, imgY + imgSize / 2, imgSize / 2 + 2, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(${accentR},${accentG},${accentB},0.4)`;
    ctx.lineWidth = 2;
    ctx.stroke();
  } else {
    ctx.beginPath();
    ctx.arc(imgX + imgSize / 2, imgY + imgSize / 2, imgSize / 2, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${accentR},${accentG},${accentB},0.15)`;
    ctx.fill();
    ctx.fillStyle = `rgba(255,255,255,0.4)`;
    ctx.font = "bold 90px system-ui, -apple-system, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(data.artistName[0]?.toUpperCase() || "?", W / 2, imgY + imgSize / 2 + 32);
  }

  // Artist name
  ctx.textAlign = "center";
  ctx.fillStyle = "rgba(255,255,255,0.7)";
  ctx.font = "600 42px system-ui, -apple-system, sans-serif";
  ctx.fillText(truncate(data.artistName, 30), W / 2, 445);

  // Stat number glow
  ctx.save();
  ctx.shadowColor = `rgba(${accentR},${accentG},${accentB},0.5)`;
  ctx.shadowBlur = 40;
  ctx.fillStyle = "#ffffff";
  ctx.font = "bold 160px system-ui, -apple-system, sans-serif";
  ctx.fillText(data.statNumber, W / 2, 620);
  ctx.restore();

  // Stat number (crisp on top)
  ctx.fillStyle = "#ffffff";
  ctx.font = "bold 160px system-ui, -apple-system, sans-serif";
  ctx.fillText(data.statNumber, W / 2, 620);

  // Stat label
  ctx.fillStyle = `rgba(${accentR},${accentG},${accentB},0.9)`;
  ctx.font = "600 34px system-ui, -apple-system, sans-serif";
  ctx.fillText(data.statLabel, W / 2, 670);

  // Context line
  ctx.fillStyle = "rgba(255,255,255,0.4)";
  ctx.font = "400 26px system-ui, -apple-system, sans-serif";
  ctx.fillText(data.contextLine, W / 2, 725);

  // Secondary stat
  if (data.secondaryStat) {
    ctx.fillStyle = "rgba(255,255,255,0.25)";
    ctx.font = "400 24px system-ui, -apple-system, sans-serif";
    ctx.fillText(data.secondaryStat, W / 2, 770);
  }

  // Bottom branding
  ctx.fillStyle = GREEN;
  ctx.font = "900 36px system-ui, -apple-system, sans-serif";
  ctx.fillText("gatekeepify", W / 2, 960);

  ctx.fillStyle = "rgba(255,255,255,0.25)";
  ctx.font = "400 20px system-ui, -apple-system, sans-serif";
  ctx.fillText("Prove you listened first.", W / 2, 995);

  // Bottom accent line
  const lineGrad = ctx.createLinearGradient(W * 0.3, 0, W * 0.7, 0);
  lineGrad.addColorStop(0, "transparent");
  lineGrad.addColorStop(0.5, `rgba(${accentR},${accentG},${accentB},0.5)`);
  lineGrad.addColorStop(1, "transparent");
  ctx.fillStyle = lineGrad;
  ctx.fillRect(W * 0.2, 1030, W * 0.6, 1);

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
