"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { Empty, ErrorNote, Locked } from "@/components/Empty";
import { Safety, Stamp } from "@/components/Stamp";
import { api, withWs } from "@/lib/api";
import { ago, money } from "@/lib/format";

const KIND: Record<string, string> = { destroyed: "border-stop", weakened: "border-hold", improved: "border-go", tariff: "border-customs", supplier: "border-hold" };

function Spark({ points }: { points: { net: number }[] }) {
  if (points.length < 2) return <span className="text-xs text-muted">New</span>;
  const v = points.map(p => p.net), min = Math.min(...v, 0), max = Math.max(...v), w = 90, h = 26;
  const xy = v.map((n, i) => `${(i / (v.length - 1)) * w},${h - ((n - min) / (max - min || 1)) * h}`).join(" ");
  const zero = h - ((0 - min) / (max - min || 1)) * h;
  return (
    <svg width={w} height={h} role="img" aria-label="Profit per sale over time">
      <line x1="0" x2={w} y1={zero} y2={zero} stroke="#D5DCE1" />
      <polyline points={xy} fill="none" stroke={v[v.length - 1] >= v[0] ? "#1F7A4D" : "#B42318"} strokeWidth="1.8" />
    </svg>
  );
}

export default function Watchlist() {
  const { user, workspace } = useAuth();
  const [items, setItems] = useState<any[] | null>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!workspace) return;
    Promise.all([api<any[]>(withWs("/watchlist", workspace.id)), api<any[]>(withWs("/alerts", workspace.id))])
      .then(([w, a]) => { setItems(w); setAlerts(a); if (a.some(x => !x.read)) api(withWs("/alerts/read", workspace.id), { method: "POST" }).then(() => window.dispatchEvent(new Event("scoute:alerts-read"))); })
      .catch(e => setErr(e.message));
  }, [workspace]);
  useEffect(() => { load(); }, [load]);

  async function remove(id: string) { await api(`/watchlist/${id}`, { method: "DELETE" }).catch(e => setErr(e.message)); load(); }
  async function checkNow() { await api("/admin/run/watch", { method: "POST" }).catch(() => {}); setTimeout(load, 2500); }

  return (
    <AppShell title="Watchlist" actions={user?.limits.watch_items ? <button className="btn-quiet" onClick={checkNow}>Check now</button> : null}>
      <ErrorNote message={err} />
      {user && !user.limits.watch_items ? <Locked what="Watching products and getting alerts" /> : !items ? <p className="text-sm text-muted">Loading…</p> : (
        <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
          <section>
            <p className="mb-3 text-sm text-muted">We recalculate each product every morning and alert you when its profit changes. {items.length} of {user?.limits.watch_items} used.</p>
            {items.length === 0 ? <Empty title="Nothing watched yet" body="Open any opportunity and choose Watch this. You'll hear from us when the numbers move." href="/feed" cta="Find a product" /> : (
              <div className="panel divide-y divide-rule">
                {items.map(w => (
                  <div key={w.id} className="flex flex-wrap items-center gap-4 px-4 py-3">
                    <div className="min-w-0 flex-1">
                      <Link href={`/opportunity/${w.opportunity_id}`} className="font-semibold hover:underline">{w.title}</Link>
                      <p className="text-xs text-muted">Sells {money(w.last?.sell)} · supplier {money(w.last?.supplier)} · pay at most {money(w.last?.max_buy_price)} · checked {ago(w.last_checked)}</p>
                    </div>
                    <Spark points={w.history || []} />
                    <div className="w-20 text-right"><p className={`num font-bold ${w.last?.net > 0 ? "text-go" : "text-stop"}`}>{money(w.last?.net)}</p><Safety level={w.last?.safety} /></div>
                    <Stamp action={w.last?.action} />
                    <button onClick={() => remove(w.id)} className="text-xs text-muted underline">Remove</button>
                  </div>
                ))}
              </div>
            )}
          </section>
          <section>
            <h2 className="mb-3 font-semibold">Alerts</h2>
            {alerts.length === 0 ? <p className="text-sm text-muted">No alerts yet. When a product's profit rises or falls by a quarter or more, it shows up here{user?.settings?.alert_email ? " and in your inbox" : ""}.</p> : (
              <ul className="space-y-2">{alerts.map(a => (
                <li key={a.id} className={`border-l-4 bg-surface px-4 py-3 text-sm ${KIND[a.kind] || "border-rule"}`}>
                  <p className="font-semibold">{a.title}</p><p className="mt-1 text-muted">{a.body}</p><p className="mt-1 text-xs text-muted">{ago(a.created_at)}</p>
                </li>))}</ul>
            )}
          </section>
        </div>
      )}
    </AppShell>
  );
}
