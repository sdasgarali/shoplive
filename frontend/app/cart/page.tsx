"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api, CartOut } from "../../lib/api";
import { useAuth } from "../../lib/auth";

export default function CartPage() {
  const { token, ready } = useAuth();
  const [cart, setCart] = useState<CartOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<{ order_id: number; total: number } | null>(null);

  const load = useCallback(() => {
    if (!token) return;
    api.getCart(token).then(setCart).catch((e) => setError(e.message));
  }, [token]);

  useEffect(() => { load(); }, [load]);

  async function remove(listingId: number) {
    if (!token) return;
    await api.removeFromCart(listingId, token);
    load();
  }

  async function checkout() {
    if (!token) return;
    try {
      const res = await api.checkout(token);
      setDone(res);
      load();
    } catch (e) { setError((e as Error).message); }
  }

  if (ready && !token)
    return <p className="text-white/60">Please <Link href="/login" className="text-rose-300 hover:underline">log in</Link> to view your cart.</p>;

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-4 text-2xl font-bold">Your cart</h1>
      {error && <p className="mb-3 rounded bg-rose-500/20 p-2 text-rose-200">{error}</p>}
      {done && (
        <p className="mb-3 rounded bg-emerald-500/20 p-3 text-emerald-200">
          Order #{done.order_id} placed — ${done.total.toFixed(2)}. See <Link href="/orders" className="underline">your orders</Link>.
        </p>
      )}
      {!cart ? (
        <p className="text-white/50">Loading…</p>
      ) : cart.items.length === 0 ? (
        <p className="text-white/50">Your cart is empty.</p>
      ) : (
        <>
          <div className="space-y-2">
            {cart.items.map((it) => (
              <div key={it.listing_id} className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 p-3">
                <div>
                  <div>{it.title}</div>
                  <div className="text-sm text-white/50">${it.price.toFixed(2)} × {it.qty}</div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-semibold">${it.subtotal.toFixed(2)}</span>
                  <button onClick={() => remove(it.listing_id)} className="text-sm text-white/50 hover:text-rose-300">Remove</button>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 flex items-center justify-between border-t border-white/10 pt-4">
            <span className="text-lg font-bold">Total: ${cart.total.toFixed(2)}</span>
            <button onClick={checkout} className="rounded-lg bg-rose-500 px-5 py-2 font-semibold hover:bg-rose-400">
              Checkout
            </button>
          </div>
        </>
      )}
    </div>
  );
}
