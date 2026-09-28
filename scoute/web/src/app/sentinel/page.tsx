"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { Empty, ErrorNote, Locked } from "@/components/Empty";
import { api, withWs } from "@/lib/api";
import { money, pct } from "@/lib/format";

const THREAT_STYLES: Record<string, { badge: string; border: string; bg: string; text: string }> = {
  CRITICAL: { badge: "bg-stop text-white", border: "border-stop/60", bg: "bg-stop-tint/50", text: "text-stop" },
  WARNING: { badge: "bg-hold text-white", border: "border-hold/60", bg: "bg-hold-tint/50", text: "text-hold" },
  STABLE: { badge: "bg-customs text-white", border: "border-customs/50", bg: "bg-customs-tint/60", text: "text-customs" },
  THRIVING: { badge: "bg-go text-white", border: "border-go/50", bg: "bg-go-tint/60", text: "text-go" },
};

export default function SentinelPage() {
  const { user, workspace } = useAuth();
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [scanningId, setScanningId] = useState<string | null>(null);
  const [scanningAll, setScanningAll] = useState(false);

  const load = useCallback(() => {
    if (!workspace) return;
    api<any>(withWs("/sentinel", workspace.id))
      .then((d) => {
        setData(d);
        setErr(null);
      })
      .catch((e) => setErr(e.message));
  }, [workspace]);

  useEffect(() => {
    load();
  }, [load]);

  async function triggerScan(id: string) {
    setScanningId(id);
    try {
      await api(`/sentinel/${id}/scan`, { method: "POST" });
      load();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setScanningId(null);
    }
  }

  async function triggerScanAll() {
    if (!data?.items?.length) return;
    setScanningAll(true);
    try {
      for (const item of data.items) {
        await api(`/sentinel/${item.id}/scan`, { method: "POST" });
      }
      load();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setScanningAll(false);
    }
  }

  async function removeItem(id: string) {
    try {
      await api(`/sentinel/${id}`, { method: "DELETE" });
      load();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  const items = data?.items || [];
  const kpis = data?.kpis || {
    monitored_skus: 0,
    protected_retail_value: 0,
    critical_threats: 0,
    warning_threats: 0,
    avg_saturation_score: 0,
  };

  return (
    <AppShell
      title="Autonomous Margin Sentinel & Saturation Radar"
      actions={
        items.length > 0 ? (
          <button
            className="btn-primary text-xs font-semibold px-4"
            disabled={scanningAll}
            onClick={triggerScanAll}
          >
            {scanningAll ? "Scanning Market Saturation..." : "Scan All Portfolios"}
          </button>
        ) : null
      }
    >
      <ErrorNote message={err} />

      {/* Hero Overview */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
        <p className="max-w-2xl leading-relaxed">
          The Sentinel re-checks your unit economics automatically once a day (and instantly on demand) and alerts
          you when a product's margin turns critical. Competitor and ad-saturation counts are a modelled estimate,
          not a live feed from Meta/TikTok or competing stores — treat them as a directional signal.
        </p>
        <span className="font-semibold text-ink">
          Daily Automated Scan
        </span>
      </div>

      {!data ? (
        <div className="flex items-center gap-3 py-16 text-sm text-muted">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-rule border-t-customs" />
          Initializing autonomous threat radar...
        </div>
      ) : items.length === 0 ? (
        <Empty
          title="No Products Connected to Sentinel"
          body="Deploy the Sentinel on your live store products or candidates. We will automatically alert you before competitor price cuts or ad saturation compress your margins."
          href="/feed"
          cta="Select Sourcing Candidates"
        />
      ) : (
        <div className="space-y-6">
          {/* Executive KPI Strip */}
          <div className="stagger grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="kpi-card" style={{ "--tile-accent": "var(--customs)" } as React.CSSProperties}>
              <span className="text-[10px] font-bold uppercase tracking-wider text-muted">
                Monitored Active SKUs
              </span>
              <p className="num mt-1 text-2xl font-extrabold text-ink">{kpis.monitored_skus}</p>
              <p className="text-[11px] text-muted">Protected catalog portfolio</p>
            </div>

            <div className="kpi-card" style={{ "--tile-accent": kpis.critical_threats > 0 ? "var(--accent-warm)" : "var(--success)" } as React.CSSProperties}>
              <span className="text-[10px] font-bold uppercase tracking-wider text-muted">
                Critical Margin Threats
              </span>
              <p
                className={`num mt-1 text-2xl font-extrabold ${
                  kpis.critical_threats > 0 ? "text-stop" : "text-go"
                }`}
              >
                {kpis.critical_threats}
              </p>
              <p className="text-[11px] text-muted">Immediate action recommended</p>
            </div>

            <div className="kpi-card" style={{ "--tile-accent": "var(--hold)" } as React.CSSProperties}>
              <span className="text-[10px] font-bold uppercase tracking-wider text-muted">
                Avg Market Saturation
              </span>
              <p className="num mt-1 text-2xl font-extrabold text-ink">
                {kpis.avg_saturation_score}
                <span className="text-xs font-normal text-muted"> / 100</span>
              </p>
              <p className="text-[11px] text-muted">Competitor ad campaign pressure</p>
            </div>

            <div className="kpi-card" style={{ "--tile-accent": "var(--rule-strong)" } as React.CSSProperties}>
              <span className="text-[10px] font-bold uppercase tracking-wider text-muted">
                Protected Portfolio Value
              </span>
              <p className="num mt-1 text-2xl font-extrabold text-ink">
                {money(kpis.protected_retail_value)}
              </p>
              <p className="text-[11px] text-muted">Total retail turnover</p>
            </div>
          </div>

          {/* Product Threat Sentinel Matrix */}
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs font-semibold text-muted uppercase tracking-wider">
              <span>Monitored SKU Threat Breakdown</span>
              <span>Sorted by threat severity</span>
            </div>

            {items.map((item: any) => {
              const threat = THREAT_STYLES[item.threat_level] || THREAT_STYLES.STABLE;
              const h = item.health || {};
              const sat = h.saturation || {};
              const isScanning = scanningId === item.id;
              const headroom = h.cpa_headroom !== undefined ? h.cpa_headroom : (item.target_cpa - item.current_cpa);

              return (
                <div
                  key={item.id}
                  className={`panel overflow-hidden border ${threat.border} bg-surface shadow-sm transition-shadow hover:shadow-md`}
                >
                  {/* Card Header */}
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-rule bg-paper/30 px-5 py-3 text-xs">
                    <div className="flex items-center gap-2.5">
                      <span className={`rounded px-2.5 py-0.5 text-xs font-extrabold uppercase tracking-wider ${threat.badge}`}>
                        {item.threat_level}
                      </span>
                      <span className="font-bold text-ink">{item.sku}</span>
                      <span className="text-muted">/</span>
                      <span className="text-muted truncate max-w-md">{item.title}</span>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="text-muted">
                        Last scan: {item.last_scanned_at ? new Date(item.last_scanned_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "Recent"}
                      </span>
                      <button
                        onClick={() => triggerScan(item.id)}
                        disabled={isScanning}
                        className="btn-quiet text-xs py-1 px-2.5"
                      >
                        {isScanning ? "Scanning..." : "Rescan Threat"}
                      </button>
                    </div>
                  </div>

                  {/* Card Content Grid */}
                  <div className="grid gap-6 p-5 md:grid-cols-[1.4fr_1fr]">
                    {/* Left: Financial Health & Headroom Metrics */}
                    <div className="space-y-4">
                      <div className="grid grid-cols-3 gap-3 text-xs">
                        <div className="rounded border border-rule/70 bg-paper/40 p-3">
                          <span className="text-muted font-medium">Retail Price</span>
                          <p className="num text-base font-bold text-ink mt-0.5">{money(item.retail_price)}</p>
                          <span className="text-[10px] text-muted">Supplier: {money(item.supplier_cost)}</span>
                        </div>

                        <div className="rounded border border-rule/70 bg-paper/40 p-3">
                          <span className="text-muted font-medium">Max Allowable CPA</span>
                          <p className="num text-base font-bold text-ink mt-0.5">{money(h.max_allowable_cpa || item.target_cpa)}</p>
                          <span className="text-[10px] text-muted">Ad acquisition ceiling</span>
                        </div>

                        <div className="rounded border border-rule/70 bg-paper/40 p-3">
                          <span className="text-muted font-medium">Ad CPA Headroom</span>
                          <p className={`num text-base font-extrabold mt-0.5 ${headroom >= 0 ? "text-go" : "text-stop"}`}>
                            {headroom >= 0 ? "+" : ""}{money(headroom)}
                          </p>
                          <span className="text-[10px] text-muted">Per conversion margin</span>
                        </div>
                      </div>

                      {/* Saturation Radar Meter */}
                      <div className="rounded border border-rule/70 bg-paper/20 p-4">
                        <div className="flex items-center justify-between text-xs">
                          <div>
                            <span className="font-bold text-ink">Competitor Saturation Radar: </span>
                            <span className="font-semibold text-customs">{sat.label || "Market Scan"}</span>
                          </div>
                          <span className="num font-extrabold text-ink">{sat.score || item.saturation_score} / 100</span>
                        </div>

                        <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-rule/50">
                          <div
                            style={{ width: `${sat.score || item.saturation_score}%` }}
                            className={`h-full rounded-full transition-[width] duration-300 ${
                              (sat.score || item.saturation_score) >= 75
                                ? "bg-stop"
                                : (sat.score || item.saturation_score) >= 45
                                ? "bg-hold"
                                : "bg-go"
                            }`}
                          />
                        </div>

                        <div className="mt-2 flex items-center justify-between text-[11px] text-muted">
                          <span>{item.competitor_count} Competing Stores Tracked</span>
                          <span>{item.active_ad_count} Active Ad Creatives Live</span>
                        </div>
                      </div>

                      {/* Reasons Callout */}
                      {h.reasons?.length > 0 && (
                        <div className="space-y-1 text-xs">
                          <span className="font-bold text-ink">Sentinel Threat Diagnosis:</span>
                          <ul className="space-y-1 text-muted">
                            {h.reasons.map((r: string, idx: number) => (
                              <li key={idx} className="flex items-start gap-1.5">
                                <span className="text-customs font-bold">&bull;</span>
                                <span>{r}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>

                    {/* Right: Tactical Action Recommendations */}
                    <div className="flex flex-col justify-between border-t border-rule/60 pt-4 md:border-t-0 md:border-l md:pl-5 md:pt-0">
                      <div>
                        <span className="text-xs font-bold uppercase tracking-wider text-ink">
                          Tactical Defense Strategy
                        </span>
                        <div className="mt-2.5 space-y-2">
                          {(item.recommendations || []).map((rec: string, i: number) => (
                            <div
                              key={i}
                              className="rounded border border-rule/80 bg-paper/50 p-3 text-xs leading-relaxed text-ink"
                            >
                              <strong className="text-customs font-semibold">Step {i + 1}:</strong> {rec}
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="mt-4 flex items-center justify-between border-t border-rule/60 pt-3 text-xs">
                        <Link
                          href={`/opportunity/${item.opportunity_id}`}
                          className="font-semibold text-customs hover:underline"
                        >
                          Open Full Unit Economics Ledger &rarr;
                        </Link>
                        <button
                          onClick={() => removeItem(item.id)}
                          className="text-muted hover:text-stop underline"
                        >
                          Stop Tracking
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </AppShell>
  );
}
