"use client";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { ErrorNote } from "@/components/Empty";
import { Stamp } from "@/components/Stamp";
import { api } from "@/lib/api";
import { money, pct } from "@/lib/format";

export default function Report() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [r, setR] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { if (user) api(`/workspaces/${id}/report`).then(setR).catch(e => setErr(e.message)); }, [id, user]);

  if (err) return <div className="p-8"><ErrorNote message={err} /></div>;
  if (!r) return <p className="p-8 text-sm text-muted">Preparing report…</p>;
  const w = r.workspace;
  return (
    <div className="mx-auto max-w-4xl bg-surface px-8 py-10 print:px-0">
      <div className="no-print mb-6 flex justify-end gap-2"><button className="btn-primary" onClick={() => window.print()}>Save as PDF</button></div>
      <header className="flex items-start justify-between border-b-2 border-ink pb-5">
        <div>
          <p className="text-sm text-muted">Product opportunity report</p>
          <h1 className="text-3xl font-bold">{w.client_name || w.name}</h1>
          <p className="mt-1 text-sm text-muted">{new Date(r.generated_at + "Z").toLocaleDateString("en-US", { dateStyle: "long" })}{r.feed_date ? ` · market data from ${r.feed_date}` : ""}</p>
        </div>
        {w.logo_url && <img src={w.logo_url} alt="" className="h-14 max-w-[160px] object-contain" />}
      </header>
      {r.demo && <p className="mt-4 border-l-4 border-hold px-3 py-2 text-sm">Demo data — sample figures, not live market prices.</p>}
      <section className="mt-8">
        <h2 className="text-lg font-bold">Top opportunities</h2>
        <p className="mt-1 text-sm text-muted">Per unit sold, after supplier cost, shipping, estimated import duty, platform fees, ads and returns.</p>
        <table className="mt-4 w-full text-sm">
          <thead><tr className="border-b border-rule text-left text-xs text-muted"><th className="py-2">Product</th><th className="py-2 text-right">Sell</th><th className="py-2 text-right">Keep</th><th className="py-2 text-right">Margin</th><th className="py-2 text-right">Max supplier price</th><th className="py-2 pl-4">Verdict</th></tr></thead>
          <tbody>{r.opportunities.map((o: any) => (
            <tr key={o.id} className="border-b border-rule/70"><td className="py-2 pr-3"><p className="font-medium">{o.title}</p><p className="text-xs text-muted">{o.why_today}</p></td>
              <td className="num py-2 text-right">{money(o.sell)}</td><td className="num py-2 text-right font-semibold">{money(o.net)}</td>
              <td className="num py-2 text-right">{pct(o.margin)}</td><td className="num py-2 text-right">{money(o.max_buy_price)}</td><td className="py-2 pl-4"><Stamp action={o.action} /></td></tr>))}</tbody>
        </table>
      </section>
      {r.watchlist.length > 0 && (
        <section className="mt-10">
          <h2 className="text-lg font-bold">Products we're watching</h2>
          <table className="mt-4 w-full text-sm"><tbody>{r.watchlist.map((x: any) => (
            <tr key={x.id} className="border-b border-rule/70"><td className="py-2">{x.title}</td><td className="num py-2 text-right font-semibold">{money(x.last?.net)} / sale</td><td className="py-2 pl-4"><Stamp action={x.last?.action} /></td></tr>))}</tbody></table>
        </section>
      )}
      <footer className="mt-10 border-t border-rule pt-4 text-xs text-muted">
        Import duty figures are estimates (duty table as of {r.duty_as_of}); confirm with a customs broker before importing. Prices change daily.
      </footer>
    </div>
  );
}
