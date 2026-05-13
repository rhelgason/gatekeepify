import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import PageTracker from "@/components/PageTracker";
import BackfillBanner from "@/components/BackfillBanner";

export const metadata: Metadata = {
  title: "Gatekeepify",
  description: "Prove you listened first.",
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
        <main className="mx-auto max-w-6xl px-6 py-8">
          <BackfillBanner />
          {children}
        </main>
      </body>
    </html>
  );
}
