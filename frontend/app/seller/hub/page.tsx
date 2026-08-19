"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { api, Listing, ListingPayload, Lot, Show } from "../../../lib/api";
import { useAuth } from "../../../lib/auth";

const CATEGORIES = [
  "Trading Cards",
  "Sneakers",
  "Collectibles",
  "Comics",
  "Electronics",
  "Fashion",
  "Toys",
  "Other",
];

const inputCls =
  "w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none focus:border-rose-500";
const btnPrimary =
  "rounded-lg bg-rose-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-rose-400 disabled:cursor-not-allowed disabled:opacity-40";
const btnSecondary =
  "rounded-lg bg-white/10 px-3 py-1.5 text-sm font-medium text-white/80 hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-40";

const SHOW_BADGES: Record<Show["status"], string> = {
  scheduled: "bg-white/10 text-white/70",
  live: "bg-rose-500 text-white",
  ended: "bg-white/10 text-white/50",
};

const LOT_BADGES: Record<Lot["status"], string> = {
  pending: "bg-white/10 text-white/70",
  open: "bg-rose-500 text-white",
  sold: "bg-emerald-500/20 text-emerald-300",
  unsold: "bg-white/10 text-white/50",
};

type ListingForm = {
  type: "auction" | "buy_now";
  title: string;
  category: string;
  start_price: string;
  increment: string;
  price: string;
  quantity: string;
};

const EMPTY_LISTING_FORM: ListingForm = {
  type: "auction",
  title: "",
  category: CATEGORIES[0],
  start_price: "",
  increment: "",
  price: "",
  quantity: "",
};

export default function SellerHubPage() {
  const { user, token, ready } = useAuth();
  const [shows, setShows] = useState<Show[]>([]);
  const [loadingShows, setLoadingShows] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // create-show form
  const [showForm, setShowForm] = useState({ title: "", category: CATEGORIES[0], scheduled_at: "" });
  const [creatingShow, setCreatingShow] = useState(false);

  // expanded show section
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [lotsByShow, setLotsByShow] = useState<Record<number, Lot[]>>({});
  const [listingsByShow, setListingsByShow] = useState<Record<number, Listing[]>>({});
  const [listingForm, setListingForm] = useState<ListingForm>(EMPTY_LISTING_FORM);
  const [createdAuction, setCreatedAuction] = useState<{ showId: number; listingId: number } | null>(null);
  const [busy, setBusy] = useState(false);

  const refreshShows = useCallback(async () => {
    if (!user) return;
    try {
      const seller = await api.getSeller(user.id);
      setShows(seller.shows);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoadingShows(false);
    }
  }, [user]);

  useEffect(() => {
    if (!ready || !user?.is_seller) return;
    let cancelled = false;
    (async () => {
      try {
        const seller = await api.getSeller(user.id);
        if (cancelled) return;
        setShows(seller.shows);
        setError(null);
      } catch (e) {
        if (cancelled) return;
        setError((e as Error).message);
      } finally {
        if (!cancelled) setLoadingShows(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ready, user]);

  async function loadLots(showId: number) {
    try {
      const [lots, listings] = await Promise.all([
        api.listLots(showId),
        api.listListings({ show_id: showId }),
      ]);
      setLotsByShow((m) => ({ ...m, [showId]: lots }));
      setListingsByShow((m) => ({ ...m, [showId]: listings }));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  function toggleShow(showId: number) {
    if (expandedId === showId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(showId);
    if (!(showId in lotsByShow)) loadLots(showId);
  }

  async function createShow(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setCreatingShow(true);
    setError(null);
    try {
      const scheduled_at = showForm.scheduled_at ? new Date(showForm.scheduled_at).toISOString() : null;
      await api.createShow({ title: showForm.title.trim(), category: showForm.category, scheduled_at }, token);
      setShowForm({ title: "", category: CATEGORIES[0], scheduled_at: "" });
      await refreshShows();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setCreatingShow(false);
    }
  }

  async function setStatus(show: Show, status: "live" | "ended") {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await api.updateShowStatus(show.id, status, token);
      await refreshShows();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function createListingForShow(showId: number, e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const f = listingForm;
      const payload: ListingPayload = {
        title: f.title.trim(),
        category: f.category,
        type: f.type,
        show_id: showId,
      };
      if (f.type === "auction") {
        payload.start_price = f.start_price ? Number(f.start_price) : undefined;
        payload.increment = f.increment ? Number(f.increment) : undefined;
      } else {
        payload.price = f.price ? Number(f.price) : undefined;
        payload.quantity = f.quantity ? Number(f.quantity) : undefined;
      }
      const listing = await api.createListing(payload, token);
      setCreatedAuction(f.type === "auction" ? { showId, listingId: listing.id } : null);
      setListingForm(EMPTY_LISTING_FORM);
      await Promise.all([loadLots(showId), refreshShows()]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function addAsLot(showId: number, listingId: number) {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await api.createLot(showId, listingId, token);
      setCreatedAuction(null);
      await loadLots(showId);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!ready) return <p className="text-white/50">Loading…</p>;

  if (!user) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-6">
        <h1 className="mb-2 text-xl font-bold">Seller Hub</h1>
        <p className="text-white/70">
          Log in to access the seller hub.{" "}
          <Link href="/login" className="font-medium text-rose-400 hover:text-rose-300">
            Log in
          </Link>
        </p>
      </div>
    );
  }

  if (!user.is_seller) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-6">
        <h1 className="mb-2 text-xl font-bold">Seller Hub</h1>
        <p className="text-white/70">Seller account required.</p>
      </div>
    );
  }

  const expandedLots = expandedId != null ? lotsByShow[expandedId] ?? [] : [];
  const expandedListings = expandedId != null ? listingsByShow[expandedId] ?? [] : [];
  const showCreatedAuction = createdAuction && expandedId === createdAuction.showId ? createdAuction : null;

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-2xl font-bold">Seller Hub</h1>
        <p className="text-white/60">Create shows, add lots and buy-now listings, and go live.</p>
      </header>

      {error && <p className="mb-4 rounded-lg bg-rose-500/20 p-3 text-rose-200">{error}</p>}

      {/* Create show */}
      <section className="mb-8 rounded-xl border border-white/10 bg-white/5 p-5">
        <h2 className="mb-3 text-lg font-semibold">Create a show</h2>
        <form onSubmit={createShow} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <input
            required
            value={showForm.title}
            onChange={(e) => setShowForm((f) => ({ ...f, title: e.target.value }))}
            placeholder="Show title"
            className={inputCls}
          />
          <select
            value={showForm.category}
            onChange={(e) => setShowForm((f) => ({ ...f, category: e.target.value }))}
            className={inputCls}
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c} className="bg-[#0b0b0f]">
                {c}
              </option>
            ))}
          </select>
          <label className="flex flex-col gap-1 text-xs text-white/50 sm:col-span-2">
            Scheduled start (optional)
            <input
              type="datetime-local"
              value={showForm.scheduled_at}
              onChange={(e) => setShowForm((f) => ({ ...f, scheduled_at: e.target.value }))}
              className={inputCls}
            />
          </label>
          <div className="sm:col-span-2">
            <button type="submit" disabled={creatingShow} className={btnPrimary}>
              {creatingShow ? "Creating…" : "Create show"}
            </button>
          </div>
        </form>
      </section>

      {/* My shows */}
      <section>
        <h2 className="mb-3 text-lg font-semibold">My shows</h2>
        {loadingShows && <p className="text-white/50">Loading…</p>}
        {!loadingShows && shows.length === 0 && (
          <p className="text-white/50">No shows yet — create your first one above.</p>
        )}
        <div className="space-y-3">
          {shows.map((show) => {
            const expanded = expandedId === show.id;
            return (
              <div key={show.id} className="rounded-xl border border-white/10 bg-white/5 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="truncate font-medium">{show.title}</span>
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-semibold uppercase ${SHOW_BADGES[show.status]}`}
                      >
                        {show.status}
                      </span>
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-white/50">
                      <span className="rounded bg-white/10 px-2 py-0.5">{show.category}</span>
                      {show.scheduled_at && (
                        <span>{new Date(show.scheduled_at).toLocaleString()}</span>
                      )}
                      <span>{show.viewer_count} watching</span>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      onClick={() => setStatus(show, "live")}
                      disabled={busy || show.status === "live" || show.status === "ended"}
                      className={btnPrimary}
                    >
                      Go Live
                    </button>
                    <button
                      onClick={() => setStatus(show, "ended")}
                      disabled={busy || show.status === "ended"}
                      className={btnSecondary}
                    >
                      End
                    </button>
                    <button onClick={() => toggleShow(show.id)} className={btnSecondary}>
                      {expanded ? "Collapse" : "Manage"}
                    </button>
                  </div>
                </div>

                {expanded && (
                  <div className="mt-4 border-t border-white/10 pt-4">
                    {/* Add listing */}
                    <h3 className="mb-2 text-sm font-semibold text-white/80">Add a listing</h3>
                    <form
                      onSubmit={(e) => createListingForShow(show.id, e)}
                      className="grid grid-cols-1 gap-3 sm:grid-cols-2"
                    >
                      <div className="flex gap-2 sm:col-span-2">
                        <button
                          type="button"
                          onClick={() => setListingForm((f) => ({ ...f, type: "auction" }))}
                          className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
                            listingForm.type === "auction"
                              ? "bg-rose-500 text-white"
                              : "bg-white/10 text-white/70 hover:bg-white/20"
                          }`}
                        >
                          Auction
                        </button>
                        <button
                          type="button"
                          onClick={() => setListingForm((f) => ({ ...f, type: "buy_now" }))}
                          className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
                            listingForm.type === "buy_now"
                              ? "bg-rose-500 text-white"
                              : "bg-white/10 text-white/70 hover:bg-white/20"
                          }`}
                        >
                          Buy now
                        </button>
                      </div>
                      <input
                        required
                        value={listingForm.title}
                        onChange={(e) => setListingForm((f) => ({ ...f, title: e.target.value }))}
                        placeholder="Listing title"
                        className={inputCls}
                      />
                      <select
                        value={listingForm.category}
                        onChange={(e) => setListingForm((f) => ({ ...f, category: e.target.value }))}
                        className={inputCls}
                      >
                        {CATEGORIES.map((c) => (
                          <option key={c} value={c} className="bg-[#0b0b0f]">
                            {c}
                          </option>
                        ))}
                      </select>
                      {listingForm.type === "auction" ? (
                        <>
                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            value={listingForm.start_price}
                            onChange={(e) => setListingForm((f) => ({ ...f, start_price: e.target.value }))}
                            placeholder="Start price"
                            className={inputCls}
                          />
                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            value={listingForm.increment}
                            onChange={(e) => setListingForm((f) => ({ ...f, increment: e.target.value }))}
                            placeholder="Bid increment"
                            className={inputCls}
                          />
                        </>
                      ) : (
                        <>
                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            value={listingForm.price}
                            onChange={(e) => setListingForm((f) => ({ ...f, price: e.target.value }))}
                            placeholder="Price"
                            className={inputCls}
                          />
                          <input
                            type="number"
                            min="1"
                            step="1"
                            value={listingForm.quantity}
                            onChange={(e) => setListingForm((f) => ({ ...f, quantity: e.target.value }))}
                            placeholder="Quantity"
                            className={inputCls}
                          />
                        </>
                      )}
                      <div className="sm:col-span-2">
                        <button type="submit" disabled={busy} className={btnPrimary}>
                          {busy ? "Saving…" : "Create listing"}
                        </button>
                      </div>
                    </form>

                    {/* Add as lot (auction listings) */}
                    {showCreatedAuction && (
                      <div className="mt-3 rounded-lg bg-rose-500/10 p-3">
                        <p className="mb-2 text-sm text-rose-200">
                          Auction listing created. Add it as a lot so bidders can see it in this show.
                        </p>
                        <button
                          onClick={() => addAsLot(show.id, showCreatedAuction.listingId)}
                          disabled={busy}
                          className={btnPrimary}
                        >
                          {busy ? "Adding…" : "Add as lot"}
                        </button>
                      </div>
                    )}

                    {/* Lots */}
                    <div className="mt-4">
                      <h3 className="mb-2 text-sm font-semibold text-white/80">Lots</h3>
                      {expandedLots.length === 0 ? (
                        <p className="text-sm text-white/50">
                          No lots yet — create an auction listing and add it as a lot.
                        </p>
                      ) : (
                        <ul className="space-y-2">
                          {expandedLots.map((lot) => {
                            const listing = expandedListings.find((l) => l.id === lot.listing_id);
                            return (
                              <li
                                key={lot.id}
                                className="flex items-center justify-between gap-3 rounded-lg bg-white/5 px-3 py-2 text-sm"
                              >
                                <span className="flex min-w-0 items-center gap-2">
                                  <span className="text-white/40">#{lot.order_index + 1}</span>
                                  <span className="truncate">
                                    {listing?.title ?? `Listing #${lot.listing_id}`}
                                  </span>
                                </span>
                                <span className="flex shrink-0 items-center gap-2">
                                  <span className="text-white/70">${lot.current_bid.toFixed(2)}</span>
                                  <span
                                    className={`rounded px-2 py-0.5 text-xs font-semibold uppercase ${LOT_BADGES[lot.status]}`}
                                  >
                                    {lot.status}
                                  </span>
                                </span>
                              </li>
                            );
                          })}
                        </ul>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
