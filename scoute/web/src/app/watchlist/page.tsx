"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { Empty, ErrorNote, Locked } from "@/components/Empty";
import { Safety, Stamp } from "@/components/Stamp";
import { api, withWs } from "@/lib/api";
import { ago, money, pct } from "@/lib/format";

const ALERT_COLORS: Record<string, { border: string; bg: string; text: string }> = {
  destroyed: { border: "border-stop", bg: "bg-red-50/70", text: "text-red-950" },
  weakened: { border: "border-amber-500", bg: "bg-amber-50/70", text: "text-amber-950" },
  improved: { border: "border-go", bg: "bg-emerald-50/70", text: "text-emerald-950" },
  tariff: { border: "border-customs", bg: "bg-blue-50/70", text: "text-blue-950" },
  supplier: { border: "border-amber-500", bg: "bg-amber-50/70", text: "text-amber-950" },
};

function Sparkline({ points }: { points: { date: string; net: number }[] }) {
  if (!points || points.length < 2) {
    return <span className="text-[11px] font-medium text-muted">Baseline Set</span>;
  }

  const values = points.map((p) => p.net);
  const minVal = Math.min(...values, 0);
  const maxVal = Math.max(...values, 1);
  const width = 110;
  const height = 32;

  const coords = values.map((val, idx) => {
    const x = (idx / (values.length - 1)) * (width - 8) + 4;
    const y = height - ((val - minVal) / (maxVal - minVal || 1)) * (height - 8) - 4;
    return { x, y, val };
  });

  const polylineStr = coords.map((c) => `${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
  const firstVal = values[0];
  const lastVal = values[values.length - 1];
  const isUp = lastVal >= firstVal;
  const strokeColor = isUp ? "#1F7A4D" : "#B42318";
  const zeroY = height - ((0 - minVal) / (maxVal - minVal || 1)) * (height - 8) - 4;

  return (
    <div className="flex flex-col items-end">
      <svg
        width={width}
        height={height}
        className="overflow-visible"
        role="img"
        aria-label="Profit trend over time"
      >
        {/* Zero baseline */}
        <line
          x1="2"
          x2={width - 2}
          y1={zeroY}
          y2={zeroY}
          stroke="#D5DCE1"
          strokeWidth="1"
          strokeDasharray="2 2"
        />
        {/* Trend line */}
        <polyline
          points={polylineStr}
          fill="none"
          stroke={strokeColor}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Current point */}
        <circle
          cx={coords[coords.length - 1].x}
          cy={coords[coords.length - 1].y}
          r="2.5"
          fill={strokeColor}
        />
      </svg>
      <span className={`text-[10px] font-bold num mt-0.5 ${isUp ? "text-go" : "text-stop"}`}>
        {lastVal >= firstVal ? "+" : ""}
        {money(lastVal - firstVal)} drift
      </span>
    </div>
  );
}

export default function WatchlistPage() {
  const { user, workspace } = useAuth();
  const [items, setItems] = useState<any[] | null>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  const load = useCallback(() => {
    if (!workspace) return;
    Promise.all([
      api<any[]>(withWs("/watchlist", workspace.id)),
      api<any[]>(withWs("/alerts", workspace.id)),
    ])
      .then(([w, a]) => {
        setItems(w);
        setAlerts(a);
        if (a.some((x) => !x.read)) {
          api(withWs("/alerts/read", workspace.id), { method: "POST" }).then(() =>
            window.dispatchEvent(new Event("scoute:alerts-read")),
          );
        }
      })
      .catch((e) => setErr(e.message));
  }, [workspace]);

  useEffect(() => {
    load();
  }, [load]);

  async function remove(id: string) {
    await api(`/watchlist/${id}`, { method: "DELETE" }).catch((e) => setErr(e.message));
    load();
  }

  async function checkNow() {
    setChecking(true);
    await api("/admin/run/watch", { method: "POST" }).catch(() => {});
    setTimeout(() => {
      load();
      setChecking(false);
    }, 2500);
  }

  const unreadAlerts = alerts.filter((a) => !a.read).length;

  return (
    <AppShell
      title="Watchlist & Price Drift Monitor"
      actions={
        user?.limits.watch_items ? (
          <button
            className="btn-quiet text-xs font-semibold"
            disabled={checking}
            onClick={checkNow}
          >
            {checking ? "Checking Prices..." : "Check Prices Now"}
          </button>
        ) : null
      }
    >
      <ErrorNote message={err} />

      {user && !user.limits.watch_items ? (
        <Locked what="Product Watchlist and automated price drift alerts" />
      ) : !items ? (
        <div className="flex items-center gap-3 py-16 text-sm text-muted">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-rule border-t-customs" />
          Loading monitored product portfolio...
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
          {/* Main Monitored List */}
          <section className="space-y-4">
            <div className="flex items-center justify-between text-xs text-muted">
              <span>
                Daily price re-check active. {items.length} of {user?.limits.watch_items} slots utilized.
              </span>
              <span className="font-semibold text-ink">
                Auto-Alerts: {user?.settings?.alert_email ? "Email + Dashboard" : "Dashboard Only"}
              </span>
            </div>

            {items.length === 0 ? (
              <Empty
                title="No Products Monitored"
                body="Open any product opportunity from the feed or search, and select 'Add to Watchlist'. You will receive real-time notifications if wholesale prices or margins shift."
                href="/feed"
                cta="Explore Opportunities"
              />
            ) : (
              <div className="panel divide-y divide-rule border border-rule bg-surface shadow-sm">
                {items.map((w) => (
                  <div
                    key={w.id}
                    className="flex flex-wrap items-center justify-between gap-4 p-4 transition-colors hover:bg-paper/30 animate-slide-up"
                  >
                    <div className="min-w-0 flex-1">
                      <Link
                        href={`/opportunity/${w.opportunity_id}`}
                        className="font-bold text-ink hover:text-customs hover:underline text-sm leading-snug block truncate"
                      >
                        {w.title}
                      </Link>
                      <div className="mt-1 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs text-muted">
                        <span>Retail: {money(w.last?.sell)}</span>
                        <span>/</span>
                        <span>Supplier: {money(w.last?.supplier)}</span>
                        <span>/</span>
                        <span>Max Buy: {money(w.last?.max_buy_price)}</span>
                        <span>/</span>
                        <span>Checked {ago(w.last_checked)}</span>
                      </div>
                    </div>

                    {/* Sparkline & Metrics */}
                    <div className="flex items-center gap-4">
                      <Sparkline points={w.history || []} />

                      <div className="w-20 text-right">
                        <p
                          className={`num text-base font-extrabold ${
                            (w.last?.net || 0) > 0 ? "text-go" : "text-stop"
                          }`}
                        >
                          {money(w.last?.net)}
                        </p>
                        <div className="mt-0.5 flex justify-end">
                          <Safety level={w.last?.safety} />
                        </div>
                      </div>

                      <Stamp action={w.last?.action} />

                      <button
                        onClick={() => remove(w.id)}
                        className="text-xs text-muted hover:text-stop underline ml-1"
                        title="Remove from watchlist"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Alerts Feed */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-bold text-ink">Margin & Tariff Alerts</h2>
              {unreadAlerts > 0 && (
                <span className="rounded bg-stop px-2 py-0.5 text-xs font-bold text-white">
                  {unreadAlerts} New
                </span>
              )}
            </div>

            {alerts.length === 0 ? (
              <div className="panel p-6 border border-rule bg-surface text-center shadow-sm">
                <p className="text-xs font-semibold text-ink">Zero Active Alerts</p>
                <p className="mt-1 text-xs text-muted leading-relaxed">
                  When a product&apos;s net profit rises or falls by $\ge 25\%$, or when a 2026 tariff rate updates, automated alerts will appear here.
                </p>
              </div>
            ) : (
              <div className="space-y-2.5">
                {alerts.map((a) => {
                  const styling = ALERT_COLORS[a.kind] || {
                    border: "border-rule",
                    bg: "bg-surface",
                    text: "text-ink",
                  };

                  return (
                    <div
                      key={a.id}
                      className={`rounded border-l-4 border ${styling.border} ${styling.bg} p-4 shadow-sm`}
                    >
                      <div className="flex items-start justify-between">
                        <p className={`text-xs font-bold ${styling.text}`}>{a.title}</p>
                        <span className="text-[10px] text-muted">{ago(a.created_at)}</span>
                      </div>
                      <p className="mt-1 text-xs text-ink/90 leading-relaxed">{a.body}</p>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      )}
    </AppShell>
  );
}
