"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "../../lib/auth";

export default function SignupPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ email: "", username: "", password: "", is_seller: false, display_name: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function set<K extends keyof typeof form>(k: K, v: (typeof form)[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await register({
        email: form.email,
        username: form.username,
        password: form.password,
        is_seller: form.is_seller,
        display_name: form.is_seller ? form.display_name || form.username : undefined,
      });
      router.push("/");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm">
      <h1 className="mb-4 text-2xl font-bold">Create your account</h1>
      <form onSubmit={submit} className="space-y-3">
        <input type="email" required placeholder="Email" value={form.email}
          onChange={(e) => set("email", e.target.value)}
          className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 outline-none focus:border-rose-500" />
        <input required placeholder="Username" value={form.username}
          onChange={(e) => set("username", e.target.value)}
          className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 outline-none focus:border-rose-500" />
        <input type="password" required placeholder="Password (min 8 chars)" value={form.password}
          onChange={(e) => set("password", e.target.value)}
          className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 outline-none focus:border-rose-500" />
        <label className="flex items-center gap-2 text-sm text-white/70">
          <input type="checkbox" checked={form.is_seller} onChange={(e) => set("is_seller", e.target.checked)} />
          I want to sell (seller account)
        </label>
        {form.is_seller && (
          <input placeholder="Store display name" value={form.display_name}
            onChange={(e) => set("display_name", e.target.value)}
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 outline-none focus:border-rose-500" />
        )}
        {error && <p className="rounded bg-rose-500/20 p-2 text-sm text-rose-200">{error}</p>}
        <button disabled={busy}
          className="w-full rounded-lg bg-rose-500 py-2 font-semibold hover:bg-rose-400 disabled:opacity-50">
          {busy ? "…" : "Sign up"}
        </button>
      </form>
      <p className="mt-4 text-sm text-white/60">
        Have an account? <Link href="/login" className="text-rose-300 hover:underline">Log in</Link>
      </p>
    </div>
  );
}
