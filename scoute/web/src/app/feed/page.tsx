"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { Empty, ErrorNote } from "@/components/Empty";
import { Card, OpportunityTable } from "@/components/OpportunityTable";
import { api, withWs } from "@/lib/api";
import { money, pct } from "@/lib/format";

type Feed = {
  items: Card[];
  date: string | null;
  brief: any;
  total: number;
  free_limit: number;
  building: boolean;
};

export default function FeedPage() {
  const { user, workspace } = useAuth();
  const [feed, setFeed] = useState<Feed | null>(null);
  const [filter, setFilter] = useState<"all" | "source" | "wait" | "high_safety">("all");
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!workspace) return;
    api<Feed>(withWs("/feed", workspace.id))
      .then((f) => {
        setFeed(f);
        setErr(null);
      })
      .catch((e) => setErr(e.message));
  }, [workspace]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!feed || (feed.date && !feed.building)) return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [feed, load]);

  const allItems = feed?.items || [];
  const sourceItems = allItems.filter((i) => i.action.startsWith("SOURCE"));
  const waitItems = allItems.filter((i) => i.action === "WAIT");
  const highSafetyItems = allItems.filter((i) => i.safety === "HIGH");

  const items = allItems.filter((i) => {
    if (filter === "source") return i.action.startsWith("SOURCE");
    if (filter === "wait") return i.action === "WAIT";
    if (filter === "high_safety") return i.safety === "HIGH";
    return true;
  });

  const avgProfit =
    sourceItems.length > 0
      ? sourceItems.reduce((acc, i) => acc + (i.net || 0), 0) / sourceItems.length
      : 0;
  const maxMargin =
    allItems.length > 0
      ? Math.max(...allItems.map((i) => i.margin || 0))
      : 0;

  return (
    <AppShell
      title="Daily Opportunities"
      actions={
        <div className="flex items-center gap-2">
          <Link href="/search" className="btn-quiet text-xs font-medium">
            Search Custom Product
          </Link>
          <Link href="/onboarding" className="btn-quiet text-xs font-medium">
            Edit Sourcing Brief
          </Link>
        </div>
      }
    >
      <ErrorNote message={err} />

      {feed && workspace && !workspace.has_brief && (
        <div className="mb-5 flex items-center justify-between rounded-md border border-customs/30 bg-paper/60 px-4 py-3 text-xs text-ink">
          <span>
            Displaying default category feed. Customize your category filters, margins, and selling channels in your briefing.
          </span>
          <Link href="/onboarding" className="font-semibold text-customs hover:underline">
            Configure Brief
          </Link>
        </div>
      )}

      {!feed ? (
        <div className="flex items-center gap-3 py-16 text-sm text-muted">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-rule border-t-customs" />
          Loading today&apos;s product opportunities...
        </div>
      ) : !feed.date ? (
        <Empty
          title="Daily Feed Generation in Progress"
          body="Scoute is analyzing marketplace Movers & Shakers, resolving wholesale suppliers, and stress-testing unit margins. This page refreshes automatically."
        />
      ) : (
        <>
          {/* Executive KPI Summary Strip */}
          <div className="stagger mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="kpi-card" style={{ "--tile-accent": "var(--customs)" } as React.CSSProperties}>
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted">
                Candidates Passed
              </span>
              <p className="num mt-1 text-2xl font-extrabold text-ink">{feed.total}</p>
              <p className="text-[11px] text-muted">
                {new Date(feed.date).toLocaleDateString("en-US", { month: "short", day: "numeric" })} Daily Scan
              </p>
            </div>

            <div className="kpi-card" style={{ "--tile-accent": "var(--success)" } as React.CSSProperties}>
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted">
                Ready to Source
              </span>
              <p className="num mt-1 text-2xl font-extrabold text-go">{sourceItems.length}</p>
              <p className="text-[11px] text-muted">High confidence & profit</p>
            </div>

            <div className="kpi-card" style={{ "--tile-accent": "var(--rule-strong)" } as React.CSSProperties}>
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted">
                Avg Sourcing Profit
              </span>
              <p className="num mt-1 text-2xl font-extrabold text-ink">{money(avgProfit)}</p>
              <p className="text-[11px] text-muted">Per unit net keep</p>
            </div>

            <div className="kpi-card" style={{ "--tile-accent": "var(--accent-warm)" } as React.CSSProperties}>
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted">
                Peak Net Margin
              </span>
              <p className="num mt-1 text-2xl font-extrabold text-ink">{pct(maxMargin)}</p>
              <p className="text-[11px] text-muted">After all tariffs & ads</p>
            </div>
          </div>

          {/* Filter Pills */}
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-1.5" role="tablist">
              {(
                [
                  ["all", `All Opportunities (${allItems.length})`],
                  ["source", `Ready to Source (${sourceItems.length})`],
                  ["wait", `High Momentum / Watch (${waitItems.length})`],
                  ["high_safety", `High Safety Buffer (${highSafetyItems.length})`],
                ] as const
              ).map(([k, label]) => (
                <button
                  key={k}
                  role="tab"
                  aria-selected={filter === k}
                  onClick={() => setFilter(k)}
                  className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition-all duration-150 ${
                    filter === k
                      ? "border-transparent bg-grad-customs text-white shadow-sm"
                      : "border-rule bg-surface text-muted hover:border-rule-strong hover:text-ink"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            <span className="text-xs text-muted">
              Unit economics updated for 2026 tariff & import regulations
            </span>
          </div>

          {/* Results Table */}
          {items.length ? (
            <OpportunityTable items={items} />
          ) : (
            <Empty
              title="No Products Match Active Filter"
              body="Switch filter pills or adjust your target margin criteria in settings."
              href="/onboarding"
              cta="Adjust Filter Parameters"
            />
          )}

          {/* Free Tier Notice */}
          {user?.plan === "free" && feed.total > feed.free_limit && (
            <div className="mt-5 rounded border border-rule bg-paper/50 p-4 text-xs text-muted flex items-center justify-between">
              <span>
                Free accounts preview the top {feed.free_limit} products with complete unit economics breakdown.
              </span>
              <Link href="/pricing" className="font-semibold text-customs hover:underline">
                Upgrade to Pro Plan
              </Link>
            </div>
          )}
        </>
      )}
    </AppShell>
  );
}
