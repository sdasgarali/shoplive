"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Order } from "../../lib/api";
import { useAuth } from "../../lib/auth";

export default function OrdersPage() {
  const { token, ready } = useAuth();
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    api.myOrders(token).then(setOrders).catch((e) => setError(e.message));
  }, [token]);

  if (ready && !token)
    return <p className="text-white/60">Please <Link href="/login" className="text-rose-300 hover:underline">log in</Link> to view your orders.</p>;

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-4 text-2xl font-bold">Your orders</h1>
      {error && <p className="mb-3 rounded bg-rose-500/20 p-2 text-rose-200">{error}</p>}
      {!orders ? (
        <p className="text-white/50">Loading…</p>
      ) : orders.length === 0 ? (
        <p className="text-white/50">No orders yet. Win an auction or buy something!</p>
      ) : (
        <div className="space-y-3">
          {orders.map((o) => (
            <div key={o.id} className="rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="font-semibold">Order #{o.id}</span>
                <span className="rounded bg-white/10 px-2 py-0.5 text-xs uppercase">{o.status}</span>
              </div>
              {o.items.map((it, i) => (
                <div key={i} className="flex justify-between text-sm text-white/70">
                  <span>{it.title} × {it.qty}</span>
                  <span>${(it.price * it.qty).toFixed(2)}</span>
                </div>
              ))}
              <div className="mt-2 border-t border-white/10 pt-2 text-right font-semibold">
                Total: ${o.total.toFixed(2)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
