import Link from "next/link";

export function AuthCard({ title, children, footer }: { title: string; children: React.ReactNode; footer: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-grad-mesh px-4 py-10">
      <Link href="/" className="mb-8 flex items-center gap-2 text-2xl font-extrabold tracking-tight">
        <span className="flex h-8 w-8 items-center justify-center rounded-md bg-grad-customs text-base text-white shadow-sm">S</span>
        Scoute
      </Link>
      <div className="panel-accent animate-pop-in w-full max-w-sm p-6">
        <h1 className="mb-5 text-xl font-bold tracking-tight">{title}</h1>
        {children}
      </div>
      <p className="mt-5 text-sm text-muted">{footer}</p>
    </div>
  );
}
