"use client";
import { use, useEffect, useState } from "react";
import { api, Seller } from "../../../lib/api";
import ShowCard from "../../../components/ShowCard";
import { useAuth } from "../../../lib/auth";

export default function SellerPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const sellerId = Number(id);
  const { token } = useAuth();
  const [seller, setSeller] = useState<Seller | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [following, setFollowing] = useState(false);
  const [followers, setFollowers] = useState(0);

  useEffect(() => {
    api.getSeller(sellerId)
      .then((s) => { setSeller(s); setFollowers(s.follower_count); })
      .catch((e) => setError(e.message));
  }, [sellerId]);

  async function toggleFollow() {
    if (!token) { setError("Log in to follow."); return; }
    try {
      if (following) { await api.unfollow(sellerId, token); setFollowers((n) => n - 1); }
      else { await api.follow(sellerId, token); setFollowers((n) => n + 1); }
      setFollowing((f) => !f);
    } catch (e) { setError((e as Error).message); }
  }

  if (error && !seller) return <p className="rounded bg-rose-500/20 p-3 text-rose-200">{error}</p>;
  if (!seller) return <p className="text-white/50">Loading…</p>;

  return (
    <div>
      <div className="mb-6 flex items-start justify-between rounded-xl border border-white/10 bg-white/5 p-5">
        <div>
          <h1 className="text-2xl font-bold">{seller.display_name}</h1>
          <p className="mt-1 max-w-xl text-white/60">{seller.bio}</p>
          <p className="mt-2 text-sm text-white/50">
            ⭐ {seller.rating.toFixed(1)} · {followers} followers
          </p>
        </div>
        <button onClick={toggleFollow}
          className={`rounded-lg px-4 py-2 font-medium ${
            following ? "bg-white/10 hover:bg-white/20" : "bg-rose-500 hover:bg-rose-400"
          }`}>
          {following ? "Following" : "Follow"}
        </button>
      </div>

      {seller.shows.length > 0 && (
        <>
          <h2 className="mb-3 text-lg font-semibold">Shows</h2>
          <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {seller.shows.map((s) => <ShowCard key={s.id} show={s} />)}
          </div>
        </>
      )}

      {seller.listings.length > 0 && (
        <>
          <h2 className="mb-3 text-lg font-semibold">Buy now</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {seller.listings.map((l) => (
              <div key={l.id} className="rounded-xl border border-white/10 bg-white/5 p-3">
                {l.images && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={l.images.split(",")[0]} alt={l.title} className="mb-2 aspect-square w-full rounded object-cover" />
                )}
                <div className="truncate text-sm">{l.title}</div>
                <div className="font-semibold text-rose-300">${l.price.toFixed(2)}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
