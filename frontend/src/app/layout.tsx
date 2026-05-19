import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import PageTracker from "@/components/PageTracker";
import BackfillBanner from "@/components/BackfillBanner";
import ConnectionBanner from "@/components/ConnectionBanner";

export const metadata: Metadata = {
  title: "Gatekeepify",
  description: "Prove you listened first. Track your Spotify history, compare with friends, and settle it with timestamps.",
  manifest: "/manifest.json",
  themeColor: "#0a0a0a",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Gatekeepify",
  },
  openGraph: {
    title: "Gatekeepify",
    description: "Prove you listened first. Track your Spotify history, compare with friends, and settle it with timestamps.",
    siteName: "Gatekeepify",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Gatekeepify",
    description: "Prove you listened first. Track your Spotify history, compare with friends, and settle it with timestamps.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Navbar />
        <PageTracker />
        <main className="mx-auto max-w-6xl px-4 md:px-6 py-6 md:py-8">
          <BackfillBanner />
          {children}
        </main>
        <ConnectionBanner />
      </body>
    </html>
  );
}
