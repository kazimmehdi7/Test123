"use client";
import Link from "next/link";
import { Stamp, Safety } from "./Stamp";
import { money, pct } from "@/lib/format";

export type Card = {
  id: string; title: string; category: string; image_url: string; action: string; net: number; margin: number;
  sell: number; safety: string; why_today: string; is_demo: boolean; supplier_price: number | null; supplier_ship: number | null;
  duty: number | null; costs: number; locked: boolean; max_buy_price?: number; max_ad_per_sale?: number;
  break_sell?: number | null; break_supplier?: number | null;
};

/** The feed is a ledger: one row per product, money columns aligned so they can be compared down the page. */
export function OpportunityTable({ items }: { items: Card[] }) {
  return (
    <div className="panel overflow-x-auto">
      <table className="w-full min-w-[860px] text-sm">
        <thead>
          <tr className="border-b border-rule text-left text-xs text-muted">
            <th className="px-4 py-3 font-medium">Product</th>
            <th className="px-3 py-3 text-right font-medium">Sell for</th>
            <th className="px-3 py-3 text-right font-medium">Buy for</th>
            <th className="px-3 py-3 text-right font-medium">Duty</th>
            <th className="px-3 py-3 text-right font-medium">Fees, ads, returns</th>
            <th className="px-3 py-3 text-right font-medium">You keep</th>
            <th className="px-3 py-3 text-right font-medium">Pay supplier max</th>
            <th className="px-3 py-3 font-medium">Room</th>
            <th className="px-4 py-3 font-medium">Verdict</th>
          </tr>
        </thead>
        <tbody>
          {items.map(c => (
            <tr key={c.id} className="border-b border-rule last:border-0 hover:bg-paper/60">
              <td className="max-w-[320px] px-4 py-3">
                <Link href={`/opportunity/${c.id}`} className="font-semibold hover:underline">{c.title}</Link>
                <p className="mt-0.5 text-xs text-muted">{c.why_today}</p>
              </td>
              <td className="num px-3 py-3 text-right">{money(c.sell)}</td>
              <td className="num px-3 py-3 text-right">
                {c.supplier_price !== null ? money(c.supplier_price) : "—"}
                {c.supplier_ship ? <span className="block text-xs text-muted">+{money(c.supplier_ship)} ship</span> : null}
              </td>
              <td className="num px-3 py-3 text-right">{c.duty !== null && c.duty !== undefined ? money(c.duty) : "—"}</td>
              <td className="num px-3 py-3 text-right">{c.costs ? money(c.costs) : "—"}</td>
              <td className="num px-3 py-3 text-right">
                <span className={`font-bold ${c.net > 0 ? "text-go" : "text-stop"}`}>{c.action === "NO_MATCH" ? "—" : money(c.net)}</span>
                {c.action !== "NO_MATCH" && <span className="block text-xs text-muted">{pct(c.margin)}</span>}
              </td>
              <td className="num px-3 py-3 text-right">
                {c.locked ? <Link href="/pricing" className="text-xs text-customs underline">Pro</Link> : money(c.max_buy_price)}
              </td>
              <td className="px-3 py-3">{c.locked ? <span className="text-xs text-muted">Pro</span> : <Safety level={c.safety} />}</td>
              <td className="px-4 py-3"><Stamp action={c.action} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
