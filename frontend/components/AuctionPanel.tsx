"use client";
import { useEffect, useRef, useState } from "react";
import { auctionWsUrl } from "../lib/ws";
import { useAuth } from "../lib/auth";

type LotState = {
  type: string;
  lot_id?: number;
  title?: string;
  current_bid?: number;
  current_bidder_id?: number | null;
  min_next_bid?: number;
  seconds_left?: number;
  status?: string;
};

export default function AuctionPanel({ showId }: { showId: number }) {
  const { token, user } = useAuth();
  const [lot, setLot] = useState<LotState | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ended, setEnded] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(auctionWsUrl(showId, token));
    wsRef.current = ws;
    ws.onmessage = (ev) => {
      const d = JSON.parse(ev.data);
      switch (d.type) {
        case "lot_state":
        case "lot_open":
        case "new_bid":
          setLot(d); setEnded(false); break;
        case "lot_closed":
          setFlash(
            d.status === "sold"
              ? `Sold for $${Number(d.final_bid).toFixed(2)}!`
              : "Lot went unsold."
          );
          setLot(null);
          setTimeout(() => setFlash(null), 4000);
          break;
        case "auction_ended":
          setEnded(true); setLot(null); break;
        case "auction_idle":
          setLot(null); break;
        case "error":
          setError(d.error); setTimeout(() => setError(null), 3000); break;
      }
    };
    return () => ws.close();
  }, [showId, token]);

  function bid() {
    const amount = lot?.min_next_bid;
    if (!amount || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: "bid", amount }));
  }

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-semibold">Live auction</span>
        {lot?.seconds_left != null && (
          <span
            className={`rounded px-2 py-0.5 text-sm font-mono ${
              lot.seconds_left <= 5 ? "bg-rose-500 text-white" : "bg-white/10"
            }`}
          >
            {lot.seconds_left}s
          </span>
        )}
      </div>

      {flash && <div className="mb-2 rounded bg-emerald-500/20 p-2 text-emerald-200">{flash}</div>}
      {error && <div className="mb-2 rounded bg-rose-500/20 p-2 text-rose-200">{error}</div>}

      {ended && <p className="text-white/60">The auction has ended. Thanks for watching!</p>}

      {!ended && !lot && <p className="text-white/50">Waiting for the next lot…</p>}

      {lot && (
        <>
          <div className="mb-3 text-lg font-medium">{lot.title}</div>
          <div className="mb-3 flex items-end justify-between">
            <div>
              <div className="text-xs text-white/50">Current bid</div>
              <div className="text-2xl font-bold text-rose-300">
                ${Number(lot.current_bid ?? 0).toFixed(2)}
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-white/50">Next bid</div>
              <div className="text-lg font-semibold">${Number(lot.min_next_bid ?? 0).toFixed(2)}</div>
            </div>
          </div>
          <button
            onClick={bid}
            disabled={!user}
            className="w-full rounded-lg bg-rose-500 py-2.5 font-semibold hover:bg-rose-400 disabled:opacity-50"
          >
            {user ? `Bid $${Number(lot.min_next_bid ?? 0).toFixed(2)}` : "Log in to bid"}
          </button>
        </>
      )}
    </div>
  );
}
