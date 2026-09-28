import Link from "next/link";

export function Empty({ title, body, href, cta }: { title: string; body: string; href?: string; cta?: string }) {
  return (
    <div className="panel animate-fade-in px-6 py-14 text-center">
      <span className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-full bg-customs-tint text-customs" aria-hidden>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" />
        </svg>
      </span>
      <p className="text-lg font-semibold">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-muted">{body}</p>
      {href && cta && <Link href={href} className="btn-primary mt-5">{cta}</Link>}
    </div>
  );
}

export function Locked({ what, plan = "Pro" }: { what: string; plan?: string }) {
  return (
    <div className="rounded-md border border-dashed border-rule-strong bg-surface-sunken px-4 py-5 text-sm">
      <p className="font-semibold">{what} is part of the {plan} plan.</p>
      <Link href="/pricing" className="mt-2 inline-block font-semibold text-customs underline">See plans</Link>
    </div>
  );
}

export function ErrorNote({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="animate-slide-up flex items-start gap-2 rounded-md border-l-4 border-stop bg-stop-tint px-4 py-3 text-sm text-stop">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mt-0.5 shrink-0"><circle cx="12" cy="12" r="10" /><path d="M12 8v5M12 16h.01" /></svg>
      <span>{message}</span>
    </p>
  );
}
