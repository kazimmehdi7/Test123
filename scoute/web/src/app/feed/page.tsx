"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { Empty, ErrorNote } from "@/components/Empty";
import { Card, OpportunityTable } from "@/components/OpportunityTable";
import { api, withWs } from "@/lib/api";

type Feed = { items: Card[]; date: string | null; brief: any; total: number; free_limit: number; building: boolean };

export default function FeedPage() {
  const { user, workspace } = useAuth();
  const [feed, setFeed] = useState<Feed | null>(null);
  const [filter, setFilter] = useState("all");
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!workspace) return;
    api<Feed>(withWs("/feed", workspace.id)).then(f => { setFeed(f); setErr(null); }).catch(e => setErr(e.message));
  }, [workspace]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!feed || (feed.date && !feed.building)) return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [feed, load]);

  const items = (feed?.items || []).filter(i => filter === "all" || (filter === "source" ? i.action.startsWith("SOURCE") : i.action === "WAIT"));
  const counts = { source: feed?.items.filter(i => i.action.startsWith("SOURCE")).length || 0, wait: feed?.items.filter(i => i.action === "WAIT").length || 0 };

  return (
    <AppShell title="Today's opportunities" actions={<Link href="/onboarding" className="btn-quiet">Edit what I'm looking for</Link>}>
      <ErrorNote message={err} />
      {feed && workspace && !workspace.has_brief && (
        <p className="mb-4 border-l-4 border-customs bg-surface px-4 py-3 text-sm">
          Showing the default list. <Link href="/onboarding" className="font-semibold text-customs underline">Tell us what you sell</Link> to filter it for you.
        </p>
      )}
      {!feed ? <p className="text-sm text-muted">Loading today's list…</p> : !feed.date ? (
        <Empty title="Today's list is being built" body="Scoute is scanning best-seller movements and matching suppliers. This page refreshes on its own." />
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-sm text-muted">
                {feed.total} products passed your filters on {new Date(feed.date).toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}.
                Every figure is per unit sold, after all costs.
              </p>
            </div>
            <div className="flex gap-1 text-sm" role="tablist">
              {[["all", `All ${feed.items.length}`], ["source", `Ready to source ${counts.source}`], ["wait", `Worth watching ${counts.wait}`]].map(([k, l]) => (
                <button key={k} role="tab" aria-selected={filter === k} onClick={() => setFilter(k)}
                        className={`border px-3 py-1.5 ${filter === k ? "border-ink bg-ink text-white" : "border-rule bg-surface"}`}>{l}</button>
              ))}
            </div>
          </div>
          {items.length ? <OpportunityTable items={items} /> : (
            <Empty title="Nothing matches right now" body="Try a wider price range or a lower minimum profit." href="/onboarding" cta="Change filters" />
          )}
          {user?.plan === "free" && feed.total > feed.free_limit && (
            <p className="mt-4 text-sm text-muted">
              The free plan shows the full math for the top {feed.free_limit}. <Link href="/pricing" className="font-semibold text-customs underline">Upgrade to Pro</Link> for every product, editable numbers and alerts.
            </p>
          )}
        </>
      )}
    </AppShell>
  );
}
