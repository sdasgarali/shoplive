"use client";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import { api, Show, Listing } from "../../../lib/api";
import ChatPanel from "../../../components/ChatPanel";
import AuctionPanel from "../../../components/AuctionPanel";
import BuyNowRail from "../../../components/BuyNowRail";

export default function ShowPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const showId = Number(id);
  const [show, setShow] = useState<Show | null>(null);
  const [listings, setListings] = useState<Listing[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getShow(showId), api.listListings({ show_id: showId })])
      .then(([s, l]) => { setShow(s); setListings(l); })
      .catch((e) => setError(e.message));
  }, [showId]);

  if (error) return <p className="rounded bg-rose-500/20 p-3 text-rose-200">{error}</p>;
  if (!show) return <p className="text-white/50">Loading show…</p>;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">{show.title}</h1>
          <p className="text-sm text-white/50">
            {show.status === "live" ? "🔴 Live" : "Scheduled"} ·{" "}
            <Link href={`/seller/${show.seller_id}`} className="hover:text-rose-300">
              {show.seller_display_name ?? "Seller"}
            </Link>{" "}
            · {show.category}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Video + auction */}
        <div className="space-y-4 lg:col-span-2">
          <div className="relative flex aspect-video items-center justify-center overflow-hidden rounded-xl border border-white/10 bg-black">
            {show.thumbnail_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={show.thumbnail_url} alt={show.title} className="h-full w-full object-cover opacity-70" />
            ) : null}
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="rounded-full bg-black/60 px-4 py-2 text-sm text-white/80">
                ▶ Live video (demo placeholder)
              </span>
            </div>
            {show.status === "live" && (
              <span className="absolute left-3 top-3 rounded bg-rose-500 px-2 py-0.5 text-xs font-semibold">
                ● LIVE · {show.viewer_count} watching
              </span>
            )}
          </div>
          <AuctionPanel showId={showId} />
          <BuyNowRail listings={listings} />
        </div>

        {/* Chat */}
        <div>
          <ChatPanel showId={showId} />
        </div>
      </div>
    </div>
  );
}
