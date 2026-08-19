// REST client for the ShopLive API. Reads NEXT_PUBLIC_API_URL.
export const API_BASE =
  (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

export type Show = {
  id: number;
  seller_id: number;
  title: string;
  category: string;
  status: "scheduled" | "live" | "ended";
  scheduled_at: string | null;
  viewer_count: number;
  thumbnail_url: string;
  created_at: string;
  seller_display_name: string | null;
};

export type Listing = {
  id: number;
  seller_id: number;
  show_id: number | null;
  type: "auction" | "buy_now";
  title: string;
  description: string;
  images: string;
  price: number;
  start_price: number;
  increment: number;
  category: string;
  condition: string;
  quantity: number;
};

export type Seller = {
  user_id: number;
  display_name: string;
  bio: string;
  rating: number;
  follower_count: number;
  shows: Show[];
  listings: Listing[];
};

export type CartOut = {
  items: { listing_id: number; title: string; price: number; qty: number; subtotal: number }[];
  total: number;
};

export type Order = {
  id: number;
  buyer_id: number;
  seller_id: number;
  status: string;
  total: number;
  items: { listing_id: number; title: string; price: number; qty: number }[];
};

export type Lot = {
  id: number;
  show_id: number;
  listing_id: number;
  order_index: number;
  status: "pending" | "open" | "sold" | "unsold";
  current_bid: number;
  current_bidder_id: number | null;
  ends_at: string | null;
};

export type ListingPayload = {
  title: string;
  category: string;
  type: "auction" | "buy_now";
  price?: number;
  start_price?: number;
  increment?: number;
  quantity?: number;
  show_id?: number;
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function authHeader(token?: string | null): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError(0, `Cannot reach the API at ${API_BASE}. Is the backend running?`);
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch { /* ignore */ }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  // auth
  register: (data: { email: string; username: string; password: string; is_seller?: boolean; display_name?: string }) =>
    req<{ access_token: string }>("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  login: (email: string, password: string) => {
    const form = new URLSearchParams({ username: email, password });
    return req<{ access_token: string }>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form.toString(),
    });
  },
  me: (token: string) =>
    req<{ id: number; email: string; username: string; is_seller: boolean }>("/auth/me", { headers: authHeader(token) }),

  // shows
  listShows: (params: { status?: string; category?: string; q?: string } = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v) as [string, string][]);
    return req<Show[]>(`/shows${qs.toString() ? `?${qs}` : ""}`);
  },
  getShow: (id: number) => req<Show>(`/shows/${id}`),

  // listings
  listListings: (params: { show_id?: number; seller_id?: number; category?: string; type?: string } = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v != null) as [string, string][]);
    return req<Listing[]>(`/listings${qs.toString() ? `?${qs}` : ""}`);
  },
  buyListing: (id: number, token: string, quantity = 1) =>
    req<{ order_id: number; status: string; total: number }>(`/listings/${id}/buy`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeader(token) },
      body: JSON.stringify({ quantity }),
    }),

  // sellers
  getSeller: (id: number) => req<Seller>(`/sellers/${id}`),
  follow: (id: number, token: string) =>
    req(`/sellers/${id}/follow`, { method: "POST", headers: authHeader(token) }),
  unfollow: (id: number, token: string) =>
    req(`/sellers/${id}/follow`, { method: "DELETE", headers: authHeader(token) }),

  // cart
  getCart: (token: string) => req<CartOut>("/cart", { headers: authHeader(token) }),
  addToCart: (listing_id: number, token: string, qty = 1) =>
    req("/cart/items", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeader(token) },
      body: JSON.stringify({ listing_id, qty }),
    }),
  removeFromCart: (listing_id: number, token: string) =>
    req(`/cart/items/${listing_id}`, { method: "DELETE", headers: authHeader(token) }),
  checkout: (token: string) =>
    req<{ order_id: number; total: number }>("/cart/checkout", { method: "POST", headers: authHeader(token) }),

  // orders
  myOrders: (token: string) => req<Order[]>("/orders", { headers: authHeader(token) }),

  // seller hub
  createShow: (data: { title: string; category: string; scheduled_at?: string | null }, token: string) =>
    req<Show>("/shows", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeader(token) },
      body: JSON.stringify(data),
    }),
  updateShowStatus: (id: number, status: "live" | "ended", token: string) =>
    req<Show>(`/shows/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeader(token) },
      body: JSON.stringify({ status }),
    }),
  createListing: (data: ListingPayload, token: string) =>
    req<Listing>("/listings", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeader(token) },
      body: JSON.stringify(data),
    }),
  createLot: (show_id: number, listing_id: number, token: string) =>
    req<Lot>(`/shows/${show_id}/lots`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeader(token) },
      body: JSON.stringify({ listing_id }),
    }),
  listLots: (show_id: number) => req<Lot[]>(`/shows/${show_id}/lots`),
};
