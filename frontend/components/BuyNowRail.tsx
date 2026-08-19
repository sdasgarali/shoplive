"use client";
import { useState } from "react";
import { Listing } from "../lib/api";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

export default function BuyNowRail({ listings }: { listings: Listing[] }) {
  const { token } = useAuth();
  const [msg, setMsg] = useState<string | null>(null);
  const buyNow = listings.filter((l) => l.type === "buy_now");

  async function add(l: Listing) {
    if (!token) { setMsg("Log in to add to cart."); return; }
    try {
      await api.addToCart(l.id, token, 1);
      setMsg(`Added “${l.title}” to cart.`);
    } catch (e) {
      setMsg((e as Error).message);
    }
    setTimeout(() => setMsg(null), 3000);
  }

  if (buyNow.length === 0) return null;

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-4">
      <div className="mb-3 font-semibold">Buy now</div>
      {msg && <div className="mb-2 rounded bg-white/10 p-2 text-sm">{msg}</div>}
      <div className="space-y-2">
        {buyNow.map((l) => (
          <div key={l.id} className="flex items-center gap-3 rounded-lg bg-white/5 p-2">
            {l.images ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={l.images.split(",")[0]} alt={l.title} className="h-12 w-12 rounded object-cover" />
            ) : (
              <div className="h-12 w-12 rounded bg-white/10" />
            )}
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm">{l.title}</div>
              <div className="text-sm font-semibold text-rose-300">${l.price.toFixed(2)}</div>
            </div>
            <button
              onClick={() => add(l)}
              className="rounded-lg bg-rose-500 px-3 py-1 text-sm font-medium hover:bg-rose-400"
            >
              Add
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
