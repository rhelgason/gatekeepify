"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function WrappedRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/dashboard?view=wrapped");
  }, [router]);
  return null;
}
