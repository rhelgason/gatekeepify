import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "You've been invited to Gatekeepify",
  description: "Someone wants to prove they listened first. Join Gatekeepify and settle it with timestamps.",
  openGraph: {
    title: "You've been invited to Gatekeepify",
    description: "Someone wants to prove they listened first. Join Gatekeepify and settle it with timestamps.",
  },
};

export default function InviteLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
