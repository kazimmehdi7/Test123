"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { ErrorNote, Locked } from "@/components/Empty";
import { Safety, Stamp } from "@/components/Stamp";
import { api, withWs } from "@/lib/api";
import { actionMeaning, ago, money, pct } from "@/lib/format";

const EDITABLE: Record<string, { label: string; kind: "money" | "pct"; step: string; min: number; max: number }> = {
  sell: { label: "Selling price", kind: "money", step: "0.50", min: 1, max: 500 },
  supplier: { label: "Supplier price", kind: "money", step: "0.25", min: 0.1, max: 200 },
  ship: { label: "Shipping to customer", kind: "money", step: "0.25", min: 0, max: 50 },
  duty_rate: { label: "Import duty rate", kind: "pct", step: "0.5", min: 0, max: 100 },
  broker: { label: "Customs / postal fee", kind: "money", step: "0.50", min: 0, max: 20 },
  ad_pct: { label: "Ad cost per sale", kind: "pct", step: "1", min: 0, max: 60 },
  return_rate: { label: "Return rate", kind: "pct", step: "0.5", min: 0, max: 30 },
  target_pct: { label: "Target profit margin", kind: "pct", step: "1", min: 0, max: 50 },
};

export default function OpportunityPage() {
  const { id } = useParams<{ id: string }>();
  const { user, workspace } = useAuth();
  const [o, setO] = useState<any>(null);
  const [calc, setCalc] = useState<any>(null);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"math" | "simulate" | "launch">("math");

  useEffect(() => {
    api(`/opportunities/${id}`).then(setO).catch((e) => setErr(e.message));
  }, [id]);

  const view = calc
    ? {
        ...o,
        profit: calc.profit,
        failure: calc.failure,
        verdict: calc.verdict,
        action: calc.verdict.action,
        inputs: calc.inputs,
      }
    : o;

  async function recalc(customEdits?: Record<string, string>) {
    const activeEdits = customEdits || edits;
    const overrides: Record<string, number> = {};
    for (const [k, v] of Object.entries(activeEdits)) {
      if (v === "") continue;
      overrides[k] = EDITABLE[k]?.kind === "pct" ? parseFloat(v) / 100 : parseFloat(v);
    }
    try {
      setCalc(await api(`/opportunities/${id}/recalc`, { method: "POST", body: { overrides } }));
      setErr(null);
    } catch (e: any) {
      setErr(e.message);
    }
  }

  function handleSliderChange(key: string, value: string) {
    const updated = { ...edits, [key]: value };
    setEdits(updated);
    recalc(updated);
  }

  async function watch() {
    try {
      const overrides = calc ? calc.inputs : {};
      const r = await api(withWs("/watchlist", null), {
        method: "POST",
        body: { opportunity_id: id, workspace_id: workspace?.id, overrides },
      });
      setNote(
        r.already
          ? "Already on your watchlist."
          : "Added to your watchlist. Margin drift alerts enabled.",
      );
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function deploySentinel() {
    try {
      const overrides = calc ? calc.inputs : {};
      const r = await api(withWs("/sentinel", null), {
        method: "POST",
        body: { opportunity_id: id, workspace_id: workspace?.id, overrides },
      });
      setNote(
        r.already
          ? "Already monitored in Margin Sentinel."
          : "Deployed to Autonomous Margin Sentinel. Competitor saturation and threat monitoring active.",
      );
    } catch (e: any) {
      setErr(e.message);
    }
  }

  function copyText(text: string, key: string) {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  }

  if (!o) {
    return (
      <AppShell title="Opportunity Analysis">
        <ErrorNote message={err} />
        {!err && (
          <div className="flex items-center gap-3 py-16 text-sm text-muted">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-rule border-t-customs" />
            Loading unit economics and supplier data...
          </div>
        )}
      </AppShell>
    );
  }

  const p = view.profit;
  const f = view.failure;
  const sell = o.sell;
  const sup = o.supplier;

  const sellPrice = p?.sell || 1;
  const landedPct = Math.max(0, Math.min(100, ((p?.landed || 0) / sellPrice) * 100));
  const feesPct = Math.max(0, Math.min(100, ((p?.fees || 0) / sellPrice) * 100));
  const adsPct = Math.max(0, Math.min(100, ((p?.ads || 0) / sellPrice) * 100));
  const bufferReturnsPct = Math.max(0, Math.min(100, (((p?.returns || 0) + (p?.buffer || 0)) / sellPrice) * 100));
  const netPct = Math.max(0, Math.min(100, ((p?.net || 0) / sellPrice) * 100));

  return (
    <AppShell
      title="Product Opportunity"
      actions={
        <div className="flex items-center gap-2">
          <Link href="/feed" className="btn-quiet text-xs font-medium">
            Back to Feed
          </Link>
          {p && (
            <>
              <button className="btn-quiet text-xs font-medium" onClick={watch}>
                Add to Watchlist
              </button>
              <button className="btn-primary text-xs font-semibold" onClick={deploySentinel}>
                Deploy Margin Sentinel
              </button>
            </>
          )}
        </div>
      }
    >
      <ErrorNote message={err} />

      {note && (
        <div className="mb-5 flex items-center justify-between rounded-md border border-go/30 bg-go/5 px-4 py-2.5 text-xs text-go">
          <span className="font-medium">{note}</span>
          <button onClick={() => setNote(null)} className="text-xs underline opacity-80 hover:opacity-100">
            Dismiss
          </button>
        </div>
      )}

      {/* Hero Card */}
      <section className="panel mb-6 overflow-hidden p-6 shadow-sm">
        <div className="grid gap-6 md:grid-cols-[1fr_auto]">
          <div>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="rounded bg-paper px-2 py-0.5 font-semibold uppercase tracking-wider text-muted">
                {o.category === "default" ? "Search Result" : o.category}
              </span>
              <span className="text-muted">/</span>
              <span className="font-medium text-ink/80">{o.why_today}</span>
              {o.is_demo && (
                <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">
                  Demo Data
                </span>
              )}
            </div>

            <h2 className="mt-2 text-2xl font-bold tracking-tight text-ink md:text-3xl">
              {sell.title}
            </h2>

            <p className="mt-2 text-sm leading-relaxed text-muted">
              {actionMeaning[view.action]}
            </p>

            {/* Verdict Reasons */}
            <div className="mt-4 flex flex-wrap gap-2">
              {(view.verdict?.reasons || []).map((r: string) => (
                <span
                  key={r}
                  className="inline-flex items-center gap-1.5 rounded border border-rule bg-paper/60 px-2.5 py-1 text-xs font-medium text-ink"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-customs" />
                  {r}
                </span>
              ))}
            </div>

            {/* Assumptions */}
            {o.assumptions?.length > 0 && (
              <div className="mt-4 rounded border border-amber-200 bg-amber-50/70 p-3.5 text-xs text-amber-950">
                <p className="font-bold uppercase tracking-wider text-amber-950">Active Assumptions</p>
                <ul className="mt-1.5 space-y-1 text-amber-900">
                  {o.assumptions.map((a: string) => (
                    <li key={a} className="flex items-start gap-1.5">
                      <span>-</span>
                      <span>{a}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Outbound Links */}
            <div className="no-print mt-5 flex flex-wrap items-center gap-2 pt-2">
              {sup?.url && (
                <a
                  className="btn-quiet text-xs font-medium"
                  href={sup.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Inspect Supplier
                </a>
              )}
              <a
                className="btn-quiet text-xs font-medium"
                href={sell.affiliate_url || sell.url}
                target="_blank"
                rel="noreferrer"
              >
                View on {sell.source === "amazon" ? "Amazon" : sell.source}
              </a>
            </div>
          </div>

          {/* Verdict Stamp & Net Profit Metric */}
          <div className="flex flex-col items-start gap-4 border-t border-rule pt-4 md:items-end md:border-t-0 md:pt-0">
            <Stamp action={view.action} size="lg" land />
            {p && (
              <div className="rounded border border-rule bg-paper/50 p-4 text-left md:text-right">
                <span className="text-[11px] font-bold uppercase tracking-wider text-muted">
                  Net Profit / Unit
                </span>
                <p
                  className={`num mt-0.5 text-3xl font-extrabold tracking-tight ${
                    p.net > 0 ? "text-go" : "text-stop"
                  }`}
                >
                  {money(p.net)}
                </p>
                <div className="mt-1 flex items-center gap-2 text-xs font-medium text-muted md:justify-end">
                  <span className="rounded bg-surface px-1.5 py-0.5 shadow-sm">{pct(p.margin)} Margin</span>
                  <span>/</span>
                  <span>Target {money(p.target)}</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Cost Distribution Bar */}
        {p && (
          <div className="mt-6 border-t border-rule pt-5">
            <div className="flex items-center justify-between text-xs text-muted">
              <span className="font-semibold uppercase tracking-wider text-ink">Price Allocation Waterfall</span>
              <span className="num font-bold text-ink">{money(p.sell)} Retail</span>
            </div>

            <div className="mt-2 flex h-3.5 w-full overflow-hidden rounded bg-rule/50 p-0.5">
              <div
                style={{ width: `${landedPct}%` }}
                title={`Landed Cost: ${money(p.landed)} (${landedPct.toFixed(1)}%)`}
                className="h-full bg-blue-600 transition-all duration-300 first:rounded-l"
              />
              <div
                style={{ width: `${feesPct}%` }}
                title={`Platform Fees: ${money(p.fees)} (${feesPct.toFixed(1)}%)`}
                className="h-full bg-sky-500 transition-all duration-300"
              />
              <div
                style={{ width: `${adsPct}%` }}
                title={`Ad Cost: ${money(p.ads)} (${adsPct.toFixed(1)}%)`}
                className="h-full bg-amber-500 transition-all duration-300"
              />
              <div
                style={{ width: `${bufferReturnsPct}%` }}
                title={`Returns & Buffer: ${money(p.returns + p.buffer)} (${bufferReturnsPct.toFixed(1)}%)`}
                className="h-full bg-purple-500 transition-all duration-300"
              />
              <div
                style={{ width: `${netPct}%` }}
                title={`Net Profit: ${money(p.net)} (${netPct.toFixed(1)}%)`}
                className={`h-full ${p.net > 0 ? "bg-emerald-600" : "bg-red-600"} transition-all duration-300 last:rounded-r`}
              />
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs">
              <span className="flex items-center gap-1.5 text-muted">
                <span className="h-2 w-2 rounded-sm bg-blue-600" />
                <span>Landed Cost ({money(p.landed)})</span>
              </span>
              <span className="flex items-center gap-1.5 text-muted">
                <span className="h-2 w-2 rounded-sm bg-sky-500" />
                <span>Platform Fees ({money(p.fees)})</span>
              </span>
              <span className="flex items-center gap-1.5 text-muted">
                <span className="h-2 w-2 rounded-sm bg-amber-500" />
                <span>Ad Spend ({money(p.ads)})</span>
              </span>
              <span className="flex items-center gap-1.5 text-muted">
                <span className="h-2 w-2 rounded-sm bg-purple-500" />
                <span>Returns & Buffer ({money(p.returns + p.buffer)})</span>
              </span>
              <span className="flex items-center gap-1.5 font-bold text-ink">
                <span className={`h-2 w-2 rounded-sm ${p.net > 0 ? "bg-emerald-600" : "bg-red-600"}`} />
                <span>Net Margin ({money(p.net)})</span>
              </span>
            </div>
          </div>
        )}
      </section>

      {!p ? (
        <NoMatch o={o} canEdit={!!user?.limits.full_detail} edits={edits} setEdits={setEdits} recalc={recalc} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1.15fr_1fr]">
          {/* Left Column: Cost Waterfall & Live Simulator */}
          <div className="space-y-6">
            <section className="panel overflow-hidden shadow-sm">
              <div className="flex border-b border-rule bg-paper/40 text-xs font-semibold">
                <button
                  onClick={() => setActiveTab("math")}
                  className={`flex-1 px-4 py-3 transition-colors ${
                    activeTab === "math"
                      ? "border-b-2 border-customs bg-surface text-customs"
                      : "text-muted hover:text-ink"
                  }`}
                >
                  Unit Cost Waterfall
                </button>
                {user?.limits.full_detail && (
                  <button
                    onClick={() => setActiveTab("simulate")}
                    className={`flex-1 px-4 py-3 transition-colors ${
                      activeTab === "simulate"
                        ? "border-b-2 border-customs bg-surface text-customs"
                        : "text-muted hover:text-ink"
                    }`}
                  >
                    Sensitivity Simulator
                  </button>
                )}
                {o.launch && (
                  <button
                    onClick={() => setActiveTab("launch")}
                    className={`flex-1 px-4 py-3 transition-colors ${
                      activeTab === "launch"
                        ? "border-b-2 border-customs bg-surface text-customs"
                        : "text-muted hover:text-ink"
                    }`}
                  >
                    Launch Angles
                  </button>
                )}
              </div>

              {/* Tab 1: Unit Cost Waterfall */}
              {activeTab === "math" && (
                <div>
                  {o.locked ? (
                    <div className="p-6">
                      <Row label="Selling price" v={p.sell} />
                      <Row label="Net Profit" v={p.net} bold />
                      <div className="mt-4">
                        <Locked what="The complete unit economics breakdown" />
                      </div>
                    </div>
                  ) : (
                    <>
                      <table className="w-full text-sm">
                        <tbody>
                          {p.lines.map((l: any) => (
                            <tr key={l.key} className="border-b border-rule/60 transition hover:bg-paper/30">
                              <td className="px-5 py-3 text-muted">
                                <span className="font-medium text-ink">{l.label}</span>
                                {l.key === "duty" && view.duty && (
                                  <span className="mt-0.5 block text-xs text-muted">
                                    {view.duty.label}
                                    {view.duty.hts !== "—" ? ` / HTS ${view.duty.hts}` : ""}
                                    {view.duty.high ? ` / ${pct(view.duty.low)}–${pct(view.duty.high)}` : ""}
                                  </span>
                                )}
                              </td>
                              <td
                                className={`num px-5 py-3 text-right ${
                                  l.amount > 0 ? "font-bold text-ink" : "text-muted"
                                }`}
                              >
                                {money(l.amount)}
                              </td>
                            </tr>
                          ))}
                          <tr className="bg-paper/60 font-bold">
                            <td className="px-5 py-3.5 text-ink">Net Profit / Unit</td>
                            <td
                              className={`num px-5 py-3.5 text-right text-lg font-extrabold ${
                                p.net > 0 ? "text-go" : "text-stop"
                              }`}
                            >
                              {money(p.net)}
                            </td>
                          </tr>
                        </tbody>
                      </table>

                      <div className="grid grid-cols-2 border-t border-rule bg-paper/20 text-sm">
                        <div className="border-r border-rule p-5">
                          <p className="text-[11px] font-bold uppercase tracking-wider text-muted">
                            Max Supplier Price
                          </p>
                          <p className="num mt-1 text-xl font-extrabold text-ink">{money(p.max_buy_price)}</p>
                          <p className="mt-0.5 text-xs text-muted">to preserve {money(p.target)} target</p>
                        </div>
                        <div className="p-5">
                          <p className="text-[11px] font-bold uppercase tracking-wider text-muted">
                            Max Ad Cost / Sale
                          </p>
                          <p className="num mt-1 text-xl font-extrabold text-ink">{money(p.max_ad_per_sale)}</p>
                          <p className="mt-0.5 text-xs text-muted">before missing profit goal</p>
                        </div>
                      </div>

                      {o.profit_alt && (
                        <div className="border-t border-rule bg-surface p-5 text-sm">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-ink">
                              {o.profit_alt.sourcing === "us_warehouse"
                                ? "US Domestic Warehouse Sourcing"
                                : "Direct China Sourcing"}
                            </span>
                            <span
                              className={`num font-bold ${
                                o.profit_alt.net > 0 ? "text-go" : "text-stop"
                              }`}
                            >
                              {money(o.profit_alt.net)} net/unit
                            </span>
                          </div>
                          <p className="mt-1 text-xs text-muted">
                            {o.profit_alt.sourcing === "us_warehouse"
                              ? "Zero import tariffs, estimated 30% higher supplier price with 2-4 day domestic delivery."
                              : "Lower manufacturing cost subject to 2026 import tariffs and postal fees."}
                          </p>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* Tab 2: Live Sensitivity Simulator */}
              {activeTab === "simulate" && user?.limits.full_detail && (
                <div className="p-5 text-sm">
                  <div className="flex items-center justify-between pb-3">
                    <p className="text-xs text-muted">
                      Adjust parameters to simulate margin sensitivity in real time:
                    </p>
                    {calc && (
                      <button
                        onClick={() => {
                          setCalc(null);
                          setEdits({});
                        }}
                        className="text-xs font-semibold text-customs hover:underline"
                      >
                        Reset Defaults
                      </button>
                    )}
                  </div>

                  <div className="space-y-4">
                    {Object.entries(EDITABLE).map(([k, m]) => {
                      const curVal =
                        edits[k] !== undefined
                          ? parseFloat(edits[k]) || 0
                          : view.inputs
                          ? m.kind === "pct"
                            ? Math.round(view.inputs[k] * 100)
                            : view.inputs[k]
                          : 0;

                      return (
                        <div key={k} className="rounded border border-rule/70 bg-paper/30 p-3.5">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-semibold text-ink">{m.label}</span>
                            <span className="num font-bold text-customs">
                              {m.kind === "pct" ? `${curVal}%` : money(curVal)}
                            </span>
                          </div>
                          <div className="mt-2 flex items-center gap-3">
                            <input
                              type="range"
                              min={m.min}
                              max={m.max}
                              step={m.step}
                              value={curVal}
                              onChange={(e) => handleSliderChange(k, e.target.value)}
                              className="h-1.5 w-full cursor-pointer appearance-none rounded bg-rule accent-customs"
                            />
                            <input
                              type="number"
                              step={m.step}
                              value={curVal}
                              onChange={(e) => handleSliderChange(k, e.target.value)}
                              className="field num h-7 w-20 px-2 py-0 text-right text-xs"
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Tab 3: Launch Angles */}
              {activeTab === "launch" && o.launch && (
                <div className="p-5 text-sm">
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-wider text-muted">Primary Keywords</span>
                      <button
                        onClick={() => copyText(o.launch.keywords.join(", "), "keywords")}
                        className="text-xs font-semibold text-customs hover:underline"
                      >
                        {copiedKey === "keywords" ? "Copied" : "Copy Keywords"}
                      </button>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {o.launch.keywords.map((kw: string) => (
                        <span key={kw} className="rounded bg-paper px-2.5 py-1 text-xs font-medium text-ink">
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>

                  {o.launch.angles?.length > 0 && (
                    <div className="mt-5 border-t border-rule pt-4">
                      <span className="text-xs font-bold uppercase tracking-wider text-muted">Ad Angles</span>
                      <div className="mt-2 space-y-2">
                        {o.launch.angles.map((angle: string, i: number) => (
                          <div
                            key={i}
                            className="flex items-center justify-between rounded border border-rule/70 bg-paper/40 p-3 text-xs"
                          >
                            <span className="font-medium text-ink">{angle}</span>
                            <button
                              onClick={() => copyText(angle, `angle-${i}`)}
                              className="ml-2 font-semibold text-customs hover:underline shrink-0"
                            >
                              {copiedKey === `angle-${i}` ? "Copied" : "Copy"}
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </section>
          </div>

          {/* Right Column: Failure Map & Matched Supplier */}
          <div className="space-y-6">
            <section className="panel overflow-hidden shadow-sm">
              <div className="flex items-center justify-between border-b border-rule bg-paper/40 px-5 py-3">
                <div>
                  <h3 className="text-sm font-bold text-ink">Failure Map</h3>
                  <p className="text-[11px] text-muted">Zero-profit break points</p>
                </div>
                {f && <Safety level={f.safety} />}
              </div>

              {!f ? (
                <div className="p-5">
                  <Locked what="The failure map sensitivity analysis" />
                </div>
              ) : (
                <div className="p-5 text-sm space-y-4">
                  {f.points.map((pt: any) => {
                    const isSafe = pt.distance === null || pt.distance >= 0.25;
                    const isWarning = pt.distance !== null && pt.distance >= 0.10 && pt.distance < 0.25;
                    const isDanger = pt.distance !== null && pt.distance < 0.10;

                    return (
                      <div key={pt.key} className="rounded border border-rule/60 bg-paper/20 p-3">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-ink">
                            {pt.label} {pt.direction === "down" ? "falls below" : "rises above"}
                          </span>
                          <span className="num font-bold text-ink">
                            {pt.break_point === null
                              ? "Never"
                              : pt.kind === "money"
                              ? money(pt.break_point)
                              : pt.kind === "pct_of_sell"
                              ? money(pt.break_point * p.sell)
                              : pct(pt.break_point, 1)}
                          </span>
                        </div>

                        {pt.distance !== null && pt.break_point !== null && (
                          <div className="mt-2">
                            <div className="flex justify-between text-[11px] text-muted">
                              <span>Buffer to zero profit</span>
                              <span className={`font-bold ${isDanger ? "text-stop" : isWarning ? "text-amber-600" : "text-go"}`}>
                                {pct(pt.distance)} margin
                              </span>
                            </div>
                            <div className="mt-1 h-1.5 w-full overflow-hidden rounded bg-rule/50">
                              <div
                                style={{ width: `${Math.min(100, Math.max(8, pt.distance * 100))}%` }}
                                className={`h-full rounded ${
                                  isDanger ? "bg-red-500" : isWarning ? "bg-amber-500" : "bg-emerald-500"
                                }`}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {f.biggest_risks?.length > 0 && (
                    <div className="rounded border border-red-200 bg-red-50/50 p-3.5 text-xs text-red-950">
                      <p className="font-bold uppercase tracking-wider">Top Vulnerabilities</p>
                      <ul className="mt-1.5 space-y-1 text-red-900">
                        {f.biggest_risks.map((r: any) => (
                          <li key={r.label} className="flex items-center justify-between">
                            <span>{r.label} (10% worse)</span>
                            <span className="font-bold text-red-700">Profit drops {pct(r.drop)}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </section>

            <section className="panel overflow-hidden p-5 text-sm shadow-sm">
              <div className="flex items-center justify-between border-b border-rule/60 pb-3">
                <h3 className="font-bold text-ink">Matched Supplier Candidate</h3>
                <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs font-bold text-emerald-800">
                  {pct(o.match_confidence)} Match Score
                </span>
              </div>

              {sup ? (
                <div className="mt-3 space-y-2">
                  <p className="font-semibold text-ink leading-snug">{sup.title}</p>
                  <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted">
                    <span className="font-bold text-ink">{money(sup.price)}</span>
                    <span>/</span>
                    <span>
                      {sup.shipping_cost === 0
                        ? "Free shipping"
                        : sup.shipping_cost
                        ? `+${money(sup.shipping_cost)} shipping`
                        : "Shipping est. $4.00"}
                    </span>
                    {sup.sold_count && (
                      <>
                        <span>/</span>
                        <span>{sup.sold_count.toLocaleString()} sold</span>
                      </>
                    )}
                    {sup.rating && (
                      <>
                        <span>/</span>
                        <span className="text-amber-700 font-semibold">{sup.rating} Rating</span>
                      </>
                    )}
                  </div>
                  {sup.url && (
                    <div className="pt-2">
                      <a
                        href={sup.url}
                        target="_blank"
                        rel="noreferrer"
                        className="btn-quiet w-full text-center text-xs font-semibold"
                      >
                        Open Supplier on AliExpress
                      </a>
                    </div>
                  )}
                </div>
              ) : (
                <p className="mt-3 text-xs text-muted">No wholesale supplier matched.</p>
              )}
            </section>
          </div>
        </div>
      )}
    </AppShell>
  );
}

function Row({ label, v, bold }: { label: string; v: number; bold?: boolean }) {
  return (
    <div className="flex justify-between border-b border-rule/60 py-2.5 text-sm">
      <span className="text-muted">{label}</span>
      <span className={`num ${bold ? "font-bold text-ink text-base" : ""}`}>{money(v)}</span>
    </div>
  );
}

function NoMatch({ o, canEdit, edits, setEdits, recalc }: any) {
  return (
    <section className="panel max-w-xl p-6 text-sm shadow-sm">
      <h3 className="font-bold text-ink text-base">Enter Your Supplier Price</h3>
      <p className="mt-1 text-xs text-muted leading-relaxed">
        We could not match an automated supplier listing with sufficient confidence. Enter your supplier quote
        to calculate real profit, import duties, and margin sensitivity:
      </p>
      {canEdit ? (
        <div className="mt-4 grid grid-cols-2 gap-3">
          {!o.sell.price && (
            <label className="block">
              <span className="text-xs font-medium text-muted">Selling price ($)</span>
              <input
                className="field num mt-1"
                placeholder="29.99"
                value={edits.sell ?? ""}
                onChange={(e) => setEdits({ ...edits, sell: e.target.value })}
              />
            </label>
          )}
          <label className="block">
            <span className="text-xs font-medium text-muted">Supplier cost ($)</span>
            <input
              className="field num mt-1"
              placeholder="6.50"
              value={edits.supplier ?? ""}
              onChange={(e) => setEdits({ ...edits, supplier: e.target.value })}
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-muted">Shipping ($)</span>
            <input
              className="field num mt-1"
              placeholder="3.50"
              value={edits.ship ?? ""}
              onChange={(e) => setEdits({ ...edits, ship: e.target.value })}
            />
          </label>
          <div className="col-span-2 pt-2">
            <button className="btn-primary w-full text-xs font-semibold" onClick={recalc}>
              Calculate True Net Profit
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-4">
          <Locked what="Entering your custom supplier figures" />
        </div>
      )}
    </section>
  );
}