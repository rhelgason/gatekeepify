"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";

// Pages that don't require authentication
const PUBLIC_PATHS = ["/", "/auth/callback", "/invite"];

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p + "/")
  );
}

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (!isPublicPath(pathname) && !isLoggedIn()) {
      router.replace("/");
      return;
    }
    setChecked(true);
  }, [pathname, router]);

  if (!checked && !isPublicPath(pathname)) {
    return null;
  }

  return <>{children}</>;
}
