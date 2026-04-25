import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <div className="flex max-w-md flex-col items-center text-center">
        <div className="mb-6 text-[10px] tracking-wider2 text-muted">
          404 — NOT FOUND
        </div>
        <div
          className="mb-8 h-12 w-12 rounded-full border border-accent"
          aria-hidden
        />
        <h1 className="text-balance text-[clamp(20px,3vw,28px)] font-light leading-tight tracking-tight">
          This branch was never spawned.
        </h1>
        <p className="mt-4 text-[13px] leading-relaxed text-fg/60">
          The path you tried doesn&apos;t exist. Head back to the trunk.
        </p>
        <Link
          href="/"
          className="focus-ring mt-8 border border-hairline px-4 py-2 text-[13px] tracking-wider2 text-fg transition-colors hover:border-accent hover:text-accent"
        >
          back to home <span aria-hidden>↗</span>
        </Link>
      </div>
    </main>
  );
}
