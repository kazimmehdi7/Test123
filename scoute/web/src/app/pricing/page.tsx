"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { ErrorNote } from "@/components/Empty";
import { api } from "@/lib/api";

const PLANS = [
  { id: "free", name: "Free", price: "$0", for: "Try it out", items: ["Top 3 opportunities a day, full math", "5 product checks a day", "Verdict on every product"] },
  { id: "pro", name: "Pro", price: "$15", for: "Dropshippers and resellers", items: ["Every opportunity, full math", "100 product checks a day", "Edit every number yourself", "Watch 25 products, email alerts", "Up to 8 categories"] },
  { id: "business", name: "Business", price: "$59", for: "Agencies", items: ["Everything in Pro", "5 client workspaces", "Branded client reports", "Watch 200 products", "500 product checks a day"] },
];

export default function Pricing() {
  const { user, refresh } = useAuth();
  const router = useRouter();
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function choose(plan: string) {
    if (!user) return router.push("/signup");
    setBusy(plan); setErr(null);
    try {
      const r = await api("/billing/checkout", { method: "POST", body: { plan } });
      if (r.url) window.location.href = r.url;
      else { await refresh(); router.push("/feed"); }
    } catch (e: any) { setErr(e.message); } finally { setBusy(null); }
  }

  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
        <Link href={user ? "/feed" : "/"} className="text-xl font-extrabold tracking-tight">Scoute</Link>
        {!user && <Link href="/login" className="text-sm text-muted">Log in</Link>}
      </header>
      <main className="mx-auto max-w-5xl px-6 pb-20 pt-8">
        <h1 className="text-3xl font-bold">One bad product costs more than a year of Scoute.</h1>
        <p className="mt-3 max-w-2xl text-muted">A failed product test usually burns $300–500 in samples and ads. Pro is $15 a month.</p>
        <ErrorNote message={err} />
        {user && !user.billing_enabled && <p className="mt-4 text-sm text-muted">Billing isn't connected yet (development mode): choosing a plan switches it instantly so you can try the features.</p>}
        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {PLANS.map(p => {
            const current = user?.plan === p.id;
            return (
              <div key={p.id} className={`panel flex flex-col p-6 ${p.id === "pro" ? "border-ink border-2" : ""}`}>
                <p className="text-sm text-muted">{p.for}</p>
                <h2 className="mt-1 text-xl font-bold">{p.name}</h2>
                <p className="mt-3"><span className="num text-3xl font-extrabold">{p.price}</span><span className="text-sm text-muted"> / month</span></p>
                <ul className="mt-5 flex-1 space-y-2 text-sm">{p.items.map(i => <li key={i} className="border-l-2 border-rule pl-3">{i}</li>)}</ul>
                {p.id === "free" ? <Link href={user ? "/feed" : "/signup"} className="btn-quiet mt-6">{current ? "Your plan" : user ? "Go to app" : "Start free"}</Link> :
                  <button className={`${p.id === "pro" ? "btn-primary" : "btn-quiet"} mt-6`} disabled={current || busy === p.id} onClick={() => choose(p.id)}>
                    {current ? "Your plan" : busy === p.id ? "Opening checkout…" : `Choose ${p.name}`}</button>}
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
