"use client";
import { useEffect, useState } from "react";
import { api, Show } from "../lib/api";
import ShowCard from "../components/ShowCard";

const CATEGORIES = [
  "All", "Trading Cards", "Sneakers", "Collectibles", "Comics", "Electronics", "Fashion", "Toys", "Other",
];

export default function Home() {
  const [shows, setShows] = useState<Show[]>([]);
  const [category, setCategory] = useState("All");
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .listShows({ category: category === "All" ? undefined : category, q: q || undefined })
      .then((s) => { setShows(s); setError(null); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [category, q]);

  const liveShows = shows.filter((s) => s.status === "live");
  const upcoming = shows.filter((s) => s.status !== "live");

  return (
    <div>
      <section className="mb-6">
        <h1 className="text-2xl font-bold">Live shopping, right now</h1>
        <p className="text-white/60">Watch live shows, bid in real-time auctions, and buy instantly.</p>
      </section>

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search shows…"
          className="mr-2 w-48 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm outline-none focus:border-rose-500"
        />
        {CATEGORIES.map((c) => (
          <button
            key={c}
            onClick={() => setCategory(c)}
            className={`rounded-full px-3 py-1 text-sm ${
              category === c ? "bg-rose-500 text-white" : "bg-white/10 text-white/70 hover:bg-white/20"
            }`}
          >
            {c}
          </button>
        ))}
      </div>

      {error && <p className="rounded bg-rose-500/20 p-3 text-rose-200">{error}</p>}
      {loading && <p className="text-white/50">Loading…</p>}

      {!loading && liveShows.length > 0 && (
        <>
          <h2 className="mb-3 text-lg font-semibold">🔴 Live now</h2>
          <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {liveShows.map((s) => <ShowCard key={s.id} show={s} />)}
          </div>
        </>
      )}

      {!loading && upcoming.length > 0 && (
        <>
          <h2 className="mb-3 text-lg font-semibold">Upcoming</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {upcoming.map((s) => <ShowCard key={s.id} show={s} />)}
          </div>
        </>
      )}

      {!loading && shows.length === 0 && !error && (
        <p className="text-white/50">No shows yet. Seed the backend with demo data.</p>
      )}
    </div>
  );
}
