import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "../lib/auth";
import NavBar from "../components/NavBar";

export const metadata: Metadata = {
  title: "ShopLive — live shopping",
  description: "Watch live shows, bid in real-time auctions, and buy instantly.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <AuthProvider>
          <NavBar />
          <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
