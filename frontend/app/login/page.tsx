"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "../../lib/auth";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      router.push("/");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm">
      <h1 className="mb-4 text-2xl font-bold">Log in</h1>
      <form onSubmit={submit} className="space-y-3">
        <input type="email" required placeholder="Email" value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 outline-none focus:border-rose-500" />
        <input type="password" required placeholder="Password" value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 outline-none focus:border-rose-500" />
        {error && <p className="rounded bg-rose-500/20 p-2 text-sm text-rose-200">{error}</p>}
        <button disabled={busy}
          className="w-full rounded-lg bg-rose-500 py-2 font-semibold hover:bg-rose-400 disabled:opacity-50">
          {busy ? "…" : "Log in"}
        </button>
      </form>
      <p className="mt-4 text-sm text-white/60">
        New here? <Link href="/signup" className="text-rose-300 hover:underline">Create an account</Link>
      </p>
      <p className="mt-2 text-xs text-white/40">Demo: buyer@shoplive.dev / password123</p>
    </div>
  );
}
