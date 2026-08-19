import Link from "next/link";
import { Show } from "../lib/api";

export default function ShowCard({ show }: { show: Show }) {
  const live = show.status === "live";
  return (
    <Link
      href={`/show/${show.id}`}
      className="group overflow-hidden rounded-xl border border-white/10 bg-white/5 transition hover:border-rose-500/50"
    >
      <div className="relative aspect-video bg-white/5">
        {show.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={show.thumbnail_url} alt={show.title} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center text-white/30">No preview</div>
        )}
        <span
          className={`absolute left-2 top-2 rounded px-2 py-0.5 text-xs font-semibold ${
            live ? "bg-rose-500 text-white" : "bg-white/20 text-white"
          }`}
        >
          {live ? "● LIVE" : "SOON"}
        </span>
        {live && (
          <span className="absolute right-2 top-2 rounded bg-black/60 px-2 py-0.5 text-xs">
            {show.viewer_count} watching
          </span>
        )}
      </div>
      <div className="p-3">
        <div className="line-clamp-1 font-medium group-hover:text-rose-300">{show.title}</div>
        <div className="mt-1 flex items-center justify-between text-xs text-white/50">
          <span>{show.seller_display_name ?? "Seller"}</span>
          <span className="rounded bg-white/10 px-2 py-0.5">{show.category}</span>
        </div>
      </div>
    </Link>
  );
}
