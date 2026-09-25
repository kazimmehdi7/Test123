import Link from "next/link";

export function AuthCard({ title, children, footer }: { title: string; children: React.ReactNode; footer: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4">
      <Link href="/" className="mb-8 text-2xl font-extrabold tracking-tight">Scoute</Link>
      <div className="panel w-full max-w-sm p-6">
        <h1 className="mb-5 text-xl font-bold">{title}</h1>
        {children}
      </div>
      <p className="mt-5 text-sm text-muted">{footer}</p>
    </div>
  );
}
