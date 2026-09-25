import Link from "next/link";

export function Empty({ title, body, href, cta }: { title: string; body: string; href?: string; cta?: string }) {
  return (
    <div className="panel px-6 py-12 text-center">
      <p className="text-lg font-semibold">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-sm text-muted">{body}</p>
      {href && cta && <Link href={href} className="btn-primary mt-5">{cta}</Link>}
    </div>
  );
}

export function Locked({ what, plan = "Pro" }: { what: string; plan?: string }) {
  return (
    <div className="border border-dashed border-rule bg-paper/60 px-4 py-5 text-sm">
      <p className="font-semibold">{what} is part of the {plan} plan.</p>
      <Link href="/pricing" className="mt-2 inline-block font-semibold text-customs underline">See plans</Link>
    </div>
  );
}

export function ErrorNote({ message }: { message: string | null }) {
  if (!message) return null;
  return <p role="alert" className="border-l-4 border-stop bg-[#FBEAE8] px-4 py-3 text-sm text-stop">{message}</p>;
}
