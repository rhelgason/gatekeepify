"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clearToken, isLoggedIn } from "@/lib/auth";

export default function Navbar() {
  const pathname = usePathname();
  const loggedIn = isLoggedIn();

  if (!loggedIn) return null;

  const links = [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/gatekeep", label: "Gatekeep" },
    { href: "/leaderboard", label: "Leaderboard" },
    { href: "/friends", label: "Friends" },
    { href: "/upload", label: "Upload" },
  ];

  return (
    <nav className="border-b border-gray-800 bg-gray-900">
      <div className="mx-auto max-w-5xl flex items-center justify-between px-4 py-3">
        <Link href="/dashboard" className="text-lg font-bold text-green-400">
          Gatekeepify
        </Link>
        <div className="flex gap-4 items-center">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`text-sm ${
                pathname.startsWith(link.href)
                  ? "text-green-400"
                  : "text-gray-400 hover:text-gray-200"
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
            className="text-sm text-gray-500 hover:text-red-400"
          >
            Sign Out
          </button>
        </div>
      </div>
    </nav>
  );
}
