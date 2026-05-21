import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center animate-fade-in">
      <div className="text-6xl mb-4">🔍</div>
      <h1 className="text-4xl font-black mb-2">Page not found</h1>
      <p className="text-gray-400 mb-8">The page you&apos;re looking for doesn&apos;t exist.</p>
      <Link
        href="/dashboard"
        className="px-6 py-3 bg-[var(--green)] text-black font-bold rounded-full hover:opacity-90 transition-opacity"
      >
        Back to Dashboard
      </Link>
    </div>
  );
}
