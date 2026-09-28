"use client";

import Link from "next/link";
import { useState } from "react";
import { Stamp, Safety } from "./Stamp";
import { money, pct } from "@/lib/format";

export type Card = {
  id: string;
  title: string;
  category: string;
  image_url: string;
  action: string;
  net: number;
  margin: number;
  sell: number;
  safety: string;
  why_today: string;
  is_demo: boolean;
  supplier_price: number | null;
  supplier_ship: number | null;
  duty: number | null;
  costs: number;
  locked: boolean;
  max_buy_price?: number;
  max_ad_per_sale?: number;
  break_sell?: number | null;
  break_supplier?: number | null;
};

export function OpportunityTable({ items }: { items: Card[] }) {
  const [sortKey, setSortKey] = useState<"net" | "margin" | "sell" | "supplier">("net");
  const [sortAsc, setSortAsc] = useState(false);

  function handleSort(key: "net" | "margin" | "sell" | "supplier") {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  }

  const sorted = [...items].sort((a, b) => {
    let valA = 0;
    let valB = 0;
    if (sortKey === "net") {
      valA = a.net || 0;
      valB = b.net || 0;
    } else if (sortKey === "margin") {
      valA = a.margin || 0;
      valB = b.margin || 0;
    } else if (sortKey === "sell") {
      valA = a.sell || 0;
      valB = b.sell || 0;
    } else if (sortKey === "supplier") {
      valA = a.supplier_price || 999;
      valB = b.supplier_price || 999;
    }
    return sortAsc ? valA - valB : valB - valA;
  });

  return (
    <div className="panel overflow-hidden border border-rule bg-surface shadow-sm">
      {/* Table Controls */}
      <div className="flex flex-wrap items-center justify-between border-b border-rule bg-paper/30 px-4 py-2.5 text-xs">
        <span className="font-semibold uppercase tracking-wider text-muted">
          {sorted.length} {sorted.length === 1 ? "Product" : "Products"} Analyzed
        </span>
        <div className="flex items-center gap-1.5">
          <span className="text-muted">Sort by:</span>
          {(
            [
              ["net", "Net Profit"],
              ["margin", "Margin %"],
              ["sell", "Retail Price"],
              ["supplier", "Supplier Cost"],
            ] as const
          ).map(([k, label]) => (
            <button
              key={k}
              onClick={() => handleSort(k)}
              className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
                sortKey === k
                  ? "bg-customs text-white"
                  : "bg-surface text-muted hover:text-ink border border-rule"
              }`}
            >
              {label} {sortKey === k ? (sortAsc ? "↑" : "↓") : ""}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[920px] text-sm">
          <thead>
            <tr className="border-b border-rule bg-paper/40 text-left text-xs font-semibold text-muted">
              <th className="px-4 py-3">Product</th>
              <th className="px-3 py-3 text-right">Retail</th>
              <th className="px-3 py-3 text-right">Supplier</th>
              <th className="px-3 py-3 text-right">Duty / Fees</th>
              <th className="px-4 py-3 text-right">Net Profit</th>
              <th className="px-4 py-3 text-left">Margin Meter</th>
              <th className="px-3 py-3 text-right">Max Supplier</th>
              <th className="px-3 py-3 text-center">Safety</th>
              <th className="px-4 py-3 text-center">Verdict</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rule/70">
            {sorted.map((c) => {
              const marginClamped = Math.max(0, Math.min(50, (c.margin || 0) * 100));
              const isProfitable = (c.net || 0) > 0;

              return (
                <tr key={c.id} className="transition-colors hover:bg-paper/40">
                  {/* Product Title & Image Preview */}
                  <td className="max-w-[320px] px-4 py-3.5">
                    <div className="flex items-start gap-3">
                      {c.image_url ? (
                        <img
                          src={c.image_url}
                          alt=""
                          className="h-10 w-10 shrink-0 rounded border border-rule bg-paper object-contain p-0.5"
                          loading="lazy"
                        />
                      ) : (
                        <div className="h-10 w-10 shrink-0 rounded border border-rule bg-paper flex items-center justify-center text-[10px] text-muted uppercase">
                          Item
                        </div>
                      )}
                      <div className="min-w-0">
                        <Link
                          href={`/opportunity/${c.id}`}
                          className="block truncate font-semibold text-ink hover:text-customs hover:underline"
                          title={c.title}
                        >
                          {c.title}
                        </Link>
                        <div className="mt-0.5 flex items-center gap-1.5 text-xs text-muted">
                          <span className="capitalize">{c.category}</span>
                          <span>/</span>
                          <span className="truncate">{c.why_today}</span>
                        </div>
                      </div>
                    </div>
                  </td>

                  {/* Retail Price */}
                  <td className="num px-3 py-3.5 text-right font-medium text-ink">
                    {money(c.sell)}
                  </td>

                  {/* Supplier Cost */}
                  <td className="num px-3 py-3.5 text-right text-muted">
                    {c.supplier_price !== null ? (
                      <div>
                        <span className="font-medium text-ink">{money(c.supplier_price)}</span>
                        {c.supplier_ship ? (
                          <span className="block text-[11px] text-muted">
                            +{money(c.supplier_ship)} ship
                          </span>
                        ) : null}
                      </div>
                    ) : (
                      "—"
                    )}
                  </td>

                  {/* Duty / Costs */}
                  <td className="num px-3 py-3.5 text-right text-xs text-muted">
                    <div>
                      <span>Duty: {c.duty !== null && c.duty !== undefined ? money(c.duty) : "—"}</span>
                      <span className="block text-[11px] text-muted/80">
                        Fees: {c.costs ? money(c.costs) : "—"}
                      </span>
                    </div>
                  </td>

                  {/* Net Profit */}
                  <td className="num px-4 py-3.5 text-right">
                    <span
                      className={`text-base font-extrabold ${
                        isProfitable ? "text-go" : "text-stop"
                      }`}
                    >
                      {c.action === "NO_MATCH" ? "—" : money(c.net)}
                    </span>
                    {c.action !== "NO_MATCH" && (
                      <span className="block text-xs font-medium text-muted">
                        {pct(c.margin)}
                      </span>
                    )}
                  </td>

                  {/* Profit Margin Meter Bar */}
                  <td className="px-4 py-3.5">
                    {c.action !== "NO_MATCH" && (
                      <div className="w-24">
                        <div className="flex justify-between text-[10px] text-muted">
                          <span>0%</span>
                          <span>50%+</span>
                        </div>
                        <div className="mt-0.5 h-1.5 w-full overflow-hidden rounded bg-rule/60">
                          <div
                            style={{ width: `${(marginClamped / 50) * 100}%` }}
                            className={`h-full rounded ${
                              c.margin >= 0.2
                                ? "bg-emerald-600"
                                : c.margin >= 0.1
                                ? "bg-amber-500"
                                : "bg-red-500"
                            }`}
                          />
                        </div>
                      </div>
                    )}
                  </td>

                  {/* Max Supplier Buy Price */}
                  <td className="num px-3 py-3.5 text-right font-medium">
                    {c.locked ? (
                      <Link href="/pricing" className="text-xs text-customs underline">
                        Pro
                      </Link>
                    ) : (
                      money(c.max_buy_price)
                    )}
                  </td>

                  {/* Safety Buffer */}
                  <td className="px-3 py-3.5 text-center">
                    {c.locked ? (
                      <span className="text-xs text-muted">Pro</span>
                    ) : (
                      <Safety level={c.safety} />
                    )}
                  </td>

                  {/* Action Stamp */}
                  <td className="px-4 py-3.5 text-center">
                    <Stamp action={c.action} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
