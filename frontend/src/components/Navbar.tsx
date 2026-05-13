"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { clearToken, isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";

export default function Navbar() {
  const pathname = usePathname();
  const loggedIn = isLoggedIn();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    if (!loggedIn) return;
    api.getPendingRequests().then(r => setPendingCount(r.length)).catch(() => {});
    const interval = setInterval(() => {
      api.getPendingRequests().then(r => setPendingCount(r.length)).catch(() => {});
    }, 60000);
    return () => clearInterval(interval);
  }, [loggedIn]);

  if (!loggedIn) return null;

  const links = [
    { href: "/dashboard", label: "Stats" },
    { href: "/wrapped", label: "Wrapped" },
    { href: "/gatekeep", label: "Gatekeep" },
    { href: "/leaderboard", label: "Crowns" },
    { href: "/friends", label: "Friends", badge: pendingCount },
    { href: "/upload", label: "Upload" },
  ];

  return (
    <nav className="sticky top-0 z-50 backdrop-blur-xl bg-[#0a0a0a]/80 border-b border-white/5">
      <div className="mx-auto max-w-6xl flex items-center justify-between px-4 md:px-6 py-3 md:py-4">
        <Link href="/dashboard" className="text-xl font-black gradient-text">
          gatekeepify
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex gap-1 items-center">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`relative text-sm px-4 py-2 rounded-full transition-all duration-200 ${
                pathname.startsWith(link.href)
                  ? "bg-white/10 text-white font-medium"
                  : "text-gray-500 hover:text-white hover:bg-white/5"
              }`}
            >
              {link.label}
              {link.badge > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-[var(--green)] rounded-full text-[10px] font-bold text-black flex items-center justify-center">
                  {link.badge}
                </span>
              )}
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

        {/* Mobile hamburger */}
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="md:hidden text-gray-400 hover:text-white p-2"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            {mobileOpen ? (
              <path d="M6 6l12 12M6 18L18 6" />
            ) : (
              <path d="M3 6h18M3 12h18M3 18h18" />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden border-t border-white/5 bg-[#0a0a0a]/95 backdrop-blur-xl animate-slide-up">
          <div className="px-4 py-3 space-y-1">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center justify-between px-4 py-3 rounded-xl text-sm transition-all ${
                  pathname.startsWith(link.href)
                    ? "bg-white/10 text-white font-medium"
                    : "text-gray-400 hover:text-white hover:bg-white/5"
                }`}
              >
                {link.label}
                {link.badge > 0 && (
                  <span className="w-5 h-5 bg-[var(--green)] rounded-full text-[10px] font-bold text-black flex items-center justify-center">
                    {link.badge}
                  </span>
                )}
              </Link>
            ))}
            <button
              onClick={() => {
                clearToken();
                window.location.href = "/";
              }}
              className="block w-full text-left px-4 py-3 rounded-xl text-sm text-gray-600 hover:text-red-400 transition-all"
            >
              Sign Out
            </button>
          </div>
        </div>
      )}
    </nav>
  );
}
