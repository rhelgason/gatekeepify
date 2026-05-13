"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clearToken, isLoggedIn } from "@/lib/auth";

export default function Navbar() {
  const pathname = usePathname();
  const loggedIn = isLoggedIn();

  if (!loggedIn) return null;

  const links = [
    { href: "/dashboard", label: "Stats" },
    { href: "/gatekeep", label: "Gatekeep" },
    { href: "/leaderboard", label: "Crowns" },
    { href: "/friends", label: "Friends" },
    { href: "/upload", label: "Upload" },
  ];

  return (
    <nav className="sticky top-0 z-50 backdrop-blur-xl bg-[#0a0a0a]/80 border-b border-white/5">
      <div className="mx-auto max-w-6xl flex items-center justify-between px-6 py-4">
        <Link href="/dashboard" className="text-xl font-black gradient-text">
          gatekeepify
        </Link>
        <div className="flex gap-1 items-center">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`text-sm px-4 py-2 rounded-full transition-all duration-200 ${
                pathname.startsWith(link.href)
                  ? "bg-white/10 text-white font-medium"
                  : "text-gray-500 hover:text-white hover:bg-white/5"
              }`}
            >
              {link.label}
            </Link>
          ))}
          <button
            onClick={() => {
              clearToken();
              window.location.href = "/";
            }}
            className="text-sm text-gray-600 hover:text-red-400 ml-2 px-3 py-2 rounded-full transition-all duration-200"
          >
            Sign Out
          </button>
        </div>
      </div>
    </nav>
  );
}
