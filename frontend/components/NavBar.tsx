"use client";
import Link from "next/link";
import { useAuth } from "../lib/auth";

export default function NavBar() {
  const { user, logout, ready } = useAuth();
  return (
    <header className="sticky top-0 z-20 border-b border-white/10 bg-black/60 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2 text-lg font-bold">
          <span className="inline-block h-3 w-3 rounded-full bg-rose-500 shadow-[0_0_10px] shadow-rose-500" />
          Shop<span className="text-rose-400">Live</span>
        </Link>
        <div className="flex items-center gap-4 text-sm">
          <Link href="/" className="text-white/70 hover:text-white">Discover</Link>
          <Link href="/cart" className="text-white/70 hover:text-white">Cart</Link>
          <Link href="/orders" className="text-white/70 hover:text-white">Orders</Link>
          {ready && user ? (
            <>
              <span className="text-white/50">@{user.username}</span>
              <button onClick={logout} className="rounded bg-white/10 px-3 py-1 hover:bg-white/20">
                Logout
              </button>
            </>
          ) : (
            <Link href="/login" className="rounded bg-rose-500 px-3 py-1 font-medium text-white hover:bg-rose-400">
              Log in
            </Link>
          )}
        </div>
      </nav>
    </header>
  );
}
