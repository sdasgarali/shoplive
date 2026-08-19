"use client";
import { useEffect, useRef, useState } from "react";
import { chatWsUrl } from "../lib/ws";
import { useAuth } from "../lib/auth";

type Msg = { username: string; text: string; ts: string };

export default function ChatPanel({ showId }: { showId: number }) {
  const { token, user } = useAuth();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const ws = new WebSocket(chatWsUrl(showId, token));
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (ev) => {
      const data = JSON.parse(ev.data);
      if (data.type === "message") {
        setMessages((m) => [...m.slice(-199), { username: data.username, text: data.text, ts: data.ts }]);
      }
    };
    return () => ws.close();
  }, [showId, token]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  function send(e: React.FormEvent) {
    e.preventDefault();
    const t = text.trim();
    if (!t || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: "message", text: t }));
    setText("");
  }

  return (
    <div className="flex h-[28rem] flex-col rounded-xl border border-white/10 bg-white/5">
      <div className="flex items-center justify-between border-b border-white/10 px-3 py-2 text-sm">
        <span className="font-semibold">Live chat</span>
        <span className={connected ? "text-emerald-400" : "text-white/40"}>
          {connected ? "● connected" : "connecting…"}
        </span>
      </div>
      <div className="flex-1 space-y-1.5 overflow-y-auto px-3 py-2 text-sm">
        {messages.length === 0 && <p className="text-white/40">Say hi to the room…</p>}
        {messages.map((m, i) => (
          <div key={i}>
            <span className="font-semibold text-rose-300">{m.username}</span>{" "}
            <span className="text-white/80">{m.text}</span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <form onSubmit={send} className="flex gap-2 border-t border-white/10 p-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={user ? "Message…" : "Log in to chat"}
          disabled={!user}
          className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm outline-none focus:border-rose-500 disabled:opacity-50"
        />
        <button
          disabled={!user}
          className="rounded-lg bg-rose-500 px-3 text-sm font-medium hover:bg-rose-400 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
