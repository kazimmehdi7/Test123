"use client";

import { useEffect, useRef, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { Empty, ErrorNote } from "@/components/Empty";
import { Card, OpportunityTable } from "@/components/OpportunityTable";
import { api } from "@/lib/api";

const PRESETS = [
  "Silicone Baking Mat",
  "No-Pull Dog Harness",
  "Insulated Tumbler 32oz",
  "Memory Foam Travel Pillow",
  "Resistance Exercise Bands",
];

export default function SearchPage() {
  const { user, workspace } = useAuth();
  const [q, setQ] = useState("");
  const [mode, setMode] = useState("dropship");
  const [job, setJob] = useState<{
    status: string;
    progress: string;
    error: string;
    items: Card[];
    query: string;
  } | null>(null);
  const [left, setLeft] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (workspace?.brief?.mode) setMode(workspace.brief.mode);
  }, [workspace]);

  useEffect(() => {
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, []);

  async function executeSearch(queryToRun: string, searchMode = mode) {
    if (queryToRun.trim().length < 2) return;
    setErr(null);
    setJob({
      status: "queued",
      progress: "Initializing marketplace scan",
      error: "",
      items: [],
      query: queryToRun,
    });

    try {
      const r = await api<{ job_id: string; remaining_today: number }>("/search", {
        method: "POST",
        body: { query: queryToRun, mode: searchMode },
      });
      setLeft(r.remaining_today);
      if (timer.current) clearInterval(timer.current);

      timer.current = setInterval(async () => {
        try {
          const s = await api<any>(`/search/${r.job_id}`);
          setJob(s);
          if (s.status === "done" || s.status === "failed") {
            clearInterval(timer.current!);
            timer.current = null;
          }
        } catch (e: any) {
          setErr(e.message);
          clearInterval(timer.current!);
        }
      }, 1500);
    } catch (e: any) {
      setErr(e.message);
      setJob(null);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    executeSearch(q);
  }

  const busy = job && (job.status === "queued" || job.status === "running");

  return (
    <AppShell title="Product Search & Sourcing Check">
      {/* Search Bar Panel */}
      <div className="kpi-card p-5 shadow-sm" style={{ "--tile-accent": "var(--customs)" } as React.CSSProperties}>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
          <label className="sr-only" htmlFor="q">
            Product Keyword
          </label>
          <input
            id="q"
            className="field flex-1 text-sm"
            placeholder="Enter product title or keywords (e.g. Silicone Baking Mat, Dog Harness)..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <select
            className="field sm:w-44 text-xs font-medium"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            aria-label="Selling Mode"
          >
            <option value="dropship">Dropship (Direct China)</option>
            <option value="resell">Resell (Domestic Supplier)</option>
            <option value="affiliate">Affiliate Commission</option>
          </select>
          <button className="btn-primary text-xs font-semibold px-5" disabled={!!busy}>
            {busy ? "Analyzing..." : "Check Unit Economics"}
          </button>
        </form>

        {/* Quick Suggestion Chips */}
        <div className="mt-3.5 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-muted font-medium">Quick Suggestions:</span>
          {PRESETS.map((preset) => (
            <button
              key={preset}
              type="button"
              onClick={() => {
                setQ(preset);
                executeSearch(preset);
              }}
              className="rounded-full border border-rule bg-surface-sunken px-2.5 py-1 text-ink/80 transition-all duration-150 hover:border-customs hover:bg-customs-tint hover:text-customs"
            >
              {preset}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-2.5 flex items-center justify-between text-xs text-muted">
        <span>
          Scrapes marketplace listings, resolves matching AliExpress/eBay wholesale candidates, and computes net profit margins.
        </span>
        {left !== null && (
          <span className="font-semibold text-ink">
            {left} searches remaining today ({user?.plan} plan)
          </span>
        )}
      </div>

      {/* Results Container */}
      <div className="mt-6">
        <ErrorNote
          message={
            err ||
            (job?.status === "failed" ? `Search terminated: ${job.error}` : null)
          }
        />

        {busy && (
          <div className="kpi-card p-10 text-center shadow-sm">
            <div className="mx-auto mb-3 h-6 w-6 animate-spin rounded-full border-2 border-rule border-t-customs" />
            <p className="text-sm font-bold text-ink">{job?.progress}...</p>
            <p className="mt-1 text-xs text-muted">
              Running price extraction, supplier matching, and 2026 tariff calculation.
            </p>
          </div>
        )}

        {job?.status === "done" &&
          (job.items.length ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-muted">
                <span>
                  Showing results for query: <strong className="text-ink">{job.query}</strong>
                </span>
                <span>Sorted by recommendation verdict & net profit</span>
              </div>
              <OpportunityTable items={job.items} />
            </div>
          ) : (
            <Empty
              title="No Wholesale Matches Found"
              body="Try searching a simpler core product noun (e.g. 'baking mat' instead of long-tail brand names)."
            />
          ))}

        {!job && (
          <Empty
            title="Inspect Any Marketplace Product"
            body="Enter a product name to see real-time landed costs, platform fees, tariff estimates, and zero-profit break points."
          />
        )}
      </div>
    </AppShell>
  );
}
