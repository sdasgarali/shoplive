// WebSocket URL helpers, derived from the REST base URL.
import { API_BASE } from "./api";

function wsBase(): string {
  return API_BASE.replace(/^http/, "ws");
}

export function chatWsUrl(showId: number, token?: string | null): string {
  const q = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${wsBase()}/ws/shows/${showId}/chat${q}`;
}

export function auctionWsUrl(showId: number, token?: string | null): string {
  const q = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${wsBase()}/ws/shows/${showId}/auction${q}`;
}
