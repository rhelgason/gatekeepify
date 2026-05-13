const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function trackEvent(
  action: string,
  details?: Record<string, any>,
  entityType?: string,
  entityId?: string,
) {
  if (typeof window === "undefined") return;
  const token = localStorage.getItem("token");
  if (!token) return;

  fetch(`${API_URL}/track-event`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      action,
      details: { ...details, url: window.location.pathname, timestamp: new Date().toISOString() },
      entity_type: entityType,
      entity_id: entityId,
    }),
  }).catch(() => {});
}
