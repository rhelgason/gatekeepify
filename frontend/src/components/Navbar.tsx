"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { clearToken, isLoggedIn } from "@/lib/auth";
import { api } from "@/lib/api";
import { trackEvent } from "@/lib/track";

export default function Navbar() {
  const pathname = usePathname();
  const loggedIn = isLoggedIn();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const [user, setUser] = useState<{ user_id: string; user_name: string; image_url: string | null } | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!loggedIn) return;
    api.getMe().then(u => setUser({ user_id: u.user_id, user_name: u.user_name, image_url: u.image_url })).catch(() => {});
    api.getPendingRequests().then(r => setPendingCount(r.length)).catch(() => {});
    const interval = setInterval(() => {
      api.getPendingRequests().then(r => setPendingCount(r.length)).catch(() => {});
    }, 60000);
    return () => clearInterval(interval);
  }, [loggedIn]);

  useEffect(() => {
    if (!menuOpen) return;
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [menuOpen]);

  if (!loggedIn) return null;

  const links = [
    { href: "/dashboard", label: "Home" },
    { href: "/feed", label: "Feed" },
    { href: "/gatekeep", label: "Gatekeep" },
    { href: "/trophies", label: "Trophies" },
    { href: "/friends", label: "Friends", badge: pendingCount },
  ];

  const handleSignOut = () => {
    trackEvent("sign_out");
    clearToken();
    window.location.href = "/";
  };

  const userInitial = user?.user_name?.[0]?.toUpperCase() || "?";

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
              {(link.badge ?? 0) > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-[var(--green)] rounded-full text-[10px] font-bold text-black flex items-center justify-center">
                  {link.badge}
                </span>
              )}
            </Link>
          ))}

          {/* User menu */}
          <div className="relative ml-2" ref={menuRef}>
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-xs font-bold text-gray-400 hover:text-white hover:bg-white/15 transition-all duration-200 overflow-hidden"
            >
              {user?.image_url ? (
                <img src={user.image_url} alt="" className="w-full h-full object-cover" />
              ) : (
                userInitial
              )}
            </button>
            {menuOpen && (
              <div className="absolute right-0 mt-2 w-52 rounded-xl border border-white/10 bg-[#141414] shadow-xl overflow-hidden animate-fade-in">
                {user && (
                  <>
                    <div className="px-4 py-3 border-b border-white/5">
                      <div className="text-sm font-medium text-white truncate">{user.user_name}</div>
                      <div className="text-[10px] text-gray-600 truncate">{user.user_id}</div>
                    </div>
                  </>
                )}
                <Link
                  href={user ? `/profile/${user.user_id}` : "/dashboard"}
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center gap-3 px-4 py-3 text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-all"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                  Your Profile
                </Link>
                <Link
                  href="/upload"
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center gap-3 px-4 py-3 text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-all"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                  Upload Data
                </Link>
                <div className="border-t border-white/5" />
                <button
                  onClick={handleSignOut}
                  className="flex items-center gap-3 w-full px-4 py-3 text-sm text-gray-600 hover:text-red-400 transition-all"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                    <polyline points="16 17 21 12 16 7" />
                    <line x1="21" y1="12" x2="9" y2="12" />
                  </svg>
                  Sign Out
                </button>
              </div>
            )}
          </div>
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
            {user && (
              <div className="px-4 py-2 mb-1">
                <div className="text-sm font-medium text-white">{user.user_name}</div>
                <div className="text-[10px] text-gray-600">{user.user_id}</div>
              </div>
            )}
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
                {(link.badge ?? 0) > 0 && (
                  <span className="w-5 h-5 bg-[var(--green)] rounded-full text-[10px] font-bold text-black flex items-center justify-center">
                    {link.badge}
                  </span>
                )}
              </Link>
            ))}
            <div className="border-t border-white/5 my-2" />
            <Link
              href={user ? `/profile/${user.user_id}` : "/dashboard"}
              onClick={() => setMobileOpen(false)}
              className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-all"
            >
              Your Profile
            </Link>
            <Link
              href="/upload"
              onClick={() => setMobileOpen(false)}
              className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-all"
            >
              Upload Data
            </Link>
            <button
              onClick={() => {
                setMobileOpen(false);
                handleSignOut();
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
