"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { ErrorNote } from "@/components/Empty";
import { Stamp, Safety } from "@/components/Stamp";
import { api } from "@/lib/api";
import { money, pct } from "@/lib/format";

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [r, setR] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      api(`/workspaces/${id}/report`)
        .then(setR)
        .catch((e) => setErr(e.message));
    }
  }, [id, user]);

  if (err) {
    return (
      <div className="mx-auto max-w-4xl p-8">
        <ErrorNote message={err} />
      </div>
    );
  }

  if (!r) {
    return (
      <div className="flex items-center justify-center py-24 text-sm text-muted">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-rule border-t-customs mr-2" />
        Generating executive client intelligence report...
      </div>
    );
  }

  const w = r.workspace;
  const opps = r.opportunities || [];
  const avgProfit =
    opps.length > 0
      ? opps.reduce((acc: number, o: any) => acc + (o.net || 0), 0) / opps.length
      : 0;
  const maxMargin =
    opps.length > 0
      ? Math.max(...opps.map((o: any) => o.margin || 0))
      : 0;

  return (
    <div className="mx-auto max-w-5xl bg-surface px-8 py-10 print:p-0">
      {/* Top Action Bar */}
      <div className="no-print mb-6 flex items-center justify-between border-b border-rule pb-4">
        <span className="text-xs text-muted">
          White-Label Executive Report &middot; Generated via Scoute Intelligence
        </span>
        <button
          className="btn-primary text-xs font-semibold px-4 py-2"
          onClick={() => window.print()}
        >
          Print / Export as PDF
        </button>
      </div>

      {/* Branded Header */}
      <header className="flex items-start justify-between border-b-2 border-ink pb-6">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-muted">
            Product Opportunity & Unit Economics Report
          </span>
          <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-ink">
            {w.client_name || w.name}
          </h1>
          <p className="mt-1.5 text-xs text-muted">
            Generated {new Date(r.generated_at + "Z").toLocaleDateString("en-US", { dateStyle: "long" })}
            {r.feed_date ? ` · Sourcing data as of ${r.feed_date}` : ""}
          </p>
        </div>
        {w.logo_url && (
          <img
            src={w.logo_url}
            alt=""
            className="h-12 max-w-[180px] object-contain"
          />
        )}
      </header>

      {r.demo && (
        <div className="mt-4 rounded border border-amber-300 bg-amber-50 px-4 py-2 text-xs font-medium text-amber-900">
          Demo Mode: Figures are based on verified market test samples.
        </div>
      )}

      {/* Executive Summary KPI Strip */}
      <section className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4 border-b border-rule pb-6">
        <div className="rounded border border-rule bg-paper/40 p-4">
          <span className="text-[10px] font-bold uppercase tracking-wider text-muted">
            Vetted Opportunities
          </span>
          <p className="num mt-1 text-2xl font-extrabold text-ink">{opps.length}</p>
        </div>
        <div className="rounded border border-rule bg-paper/40 p-4">
          <span className="text-[10px] font-bold uppercase tracking-wider text-muted">
            Average Net Keep / Unit
          </span>
          <p className="num mt-1 text-2xl font-extrabold text-go">{money(avgProfit)}</p>
        </div>
        <div className="rounded border border-rule bg-paper/40 p-4">
          <span className="text-[10px] font-bold uppercase tracking-wider text-muted">
            Peak Net Margin
          </span>
          <p className="num mt-1 text-2xl font-extrabold text-ink">{pct(maxMargin)}</p>
        </div>
        <div className="rounded border border-rule bg-paper/40 p-4">
          <span className="text-[10px] font-bold uppercase tracking-wider text-muted">
            2026 Tariff Version
          </span>
          <p className="num mt-1 text-sm font-bold text-customs truncate">{r.duty_as_of || "Active"}</p>
        </div>
      </section>

      {/* Primary Opportunities Table */}
      <section className="mt-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-ink">Market Opportunities</h2>
            <p className="text-xs text-muted">
              Unit economics calculated after wholesale product cost, freight, 2026 import tariffs, marketplace fees, ad spend, and returns.
            </p>
          </div>
        </div>

        <table className="mt-4 w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-rule text-left text-xs font-semibold text-muted bg-paper/30">
              <th className="py-2.5 px-3">Product Name</th>
              <th className="py-2.5 px-2 text-right">Retail</th>
              <th className="py-2.5 px-2 text-right">Supplier</th>
              <th className="py-2.5 px-2 text-right">Net Profit</th>
              <th className="py-2.5 px-2 text-right">Margin</th>
              <th className="py-2.5 px-2 text-right">Max Supplier</th>
              <th className="py-2.5 px-3 text-center">Verdict</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rule/70">
            {opps.map((o: any) => (
              <tr key={o.id} className="transition-colors hover:bg-paper/20">
                <td className="py-3 px-3 pr-4 max-w-[340px]">
                  <p className="font-semibold text-ink leading-snug">{o.title}</p>
                  <p className="text-[11px] text-muted mt-0.5">{o.why_today}</p>
                </td>
                <td className="num py-3 px-2 text-right font-medium">{money(o.sell)}</td>
                <td className="num py-3 px-2 text-right text-muted">
                  {o.supplier_price !== null && o.supplier_price !== undefined ? money(o.supplier_price) : "—"}
                </td>
                <td className="num py-3 px-2 text-right font-extrabold text-go">
                  {money(o.net)}
                </td>
                <td className="num py-3 px-2 text-right font-semibold text-ink">
                  {pct(o.margin)}
                </td>
                <td className="num py-3 px-2 text-right text-muted">
                  {money(o.max_buy_price)}
                </td>
                <td className="py-3 px-3 text-center">
                  <Stamp action={o.action} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Monitored Watchlist Portfolio */}
      {r.watchlist?.length > 0 && (
        <section className="mt-10 border-t border-rule pt-8">
          <h2 className="text-base font-bold text-ink">Portfolio Under Active Price Monitoring</h2>
          <p className="text-xs text-muted mt-0.5">
            Products undergoing automated daily price drift checks.
          </p>

          <table className="mt-4 w-full text-sm">
            <thead>
              <tr className="border-b border-rule text-left text-xs font-semibold text-muted bg-paper/30">
                <th className="py-2.5 px-3">Monitored Product</th>
                <th className="py-2.5 px-2 text-right">Current Net Profit</th>
                <th className="py-2.5 px-2 text-center">Safety</th>
                <th className="py-2.5 px-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule/70">
              {r.watchlist.map((x: any) => (
                <tr key={x.id}>
                  <td className="py-3 px-3 font-medium text-ink max-w-[380px]">{x.title}</td>
                  <td className="num py-3 px-2 text-right font-bold text-go">
                    {money(x.last?.net)} / unit
                  </td>
                  <td className="py-3 px-2 text-center">
                    <Safety level={x.last?.safety} />
                  </td>
                  <td className="py-3 px-3 text-center">
                    <Stamp action={x.last?.action} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {/* Footer / Compliance Disclosure */}
      <footer className="mt-12 border-t border-rule pt-5 text-[11px] text-muted leading-relaxed">
        <p>
          Disclosure: All duty rates and platform fees are estimates modeled under the 2026 US/EU Tariff Schedules. Final import duties may vary depending on official customs broker classification. Scoute Intelligence calculations are designed for decision support and risk mitigation.
        </p>
      </footer>
    </div>
  );
}
