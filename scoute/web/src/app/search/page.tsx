"use client";
import { useEffect, useRef, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { Empty, ErrorNote } from "@/components/Empty";
import { Card, OpportunityTable } from "@/components/OpportunityTable";
import { api } from "@/lib/api";

export default function SearchPage() {
  const { user, workspace } = useAuth();
  const [q, setQ] = useState("");
  const [mode, setMode] = useState("dropship");
  const [job, setJob] = useState<{ status: string; progress: string; error: string; items: Card[]; query: string } | null>(null);
  const [left, setLeft] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => { if (workspace?.brief?.mode) setMode(workspace.brief.mode); }, [workspace]);
  useEffect(() => () => { if (timer.current) clearInterval(timer.current); }, []);

  async function run(e: React.FormEvent) {
    e.preventDefault();
    if (q.trim().length < 2) return;
    setErr(null); setJob({ status: "queued", progress: "Starting", error: "", items: [], query: q });
    try {
      const r = await api<{ job_id: string; remaining_today: number }>("/search", { method: "POST", body: { query: q, mode } });
      setLeft(r.remaining_today);
      if (timer.current) clearInterval(timer.current);
      timer.current = setInterval(async () => {
        try {
          const s = await api(`/search/${r.job_id}`);
          setJob(s);
          if (s.status === "done" || s.status === "failed") { clearInterval(timer.current!); timer.current = null; }
        } catch (e: any) { setErr(e.message); clearInterval(timer.current!); }
      }, 1500);
    } catch (e: any) { setErr(e.message); setJob(null); }
  }

  const busy = job && (job.status === "queued" || job.status === "running");
  return (
    <AppShell title="Check a product">
      <form onSubmit={run} className="panel flex flex-col gap-3 p-4 sm:flex-row">
        <label className="sr-only" htmlFor="q">Product</label>
        <input id="q" className="field flex-1 text-base" placeholder="Try: dog harness, silicone baking mat, desk mat" value={q} onChange={e => setQ(e.target.value)} />
        <select className="field sm:w-40" value={mode} onChange={e => setMode(e.target.value)} aria-label="Selling mode">
          <option value="dropship">Dropship</option><option value="resell">Resell</option><option value="affiliate">Affiliate</option>
        </select>
        <button className="btn-primary" disabled={!!busy}>{busy ? "Checking…" : "Check profit"}</button>
      </form>
      <p className="mt-2 text-xs text-muted">
        We look up the product on Amazon, find matching suppliers, and count every cost. {left !== null && `${left} checks left today on your ${user?.plan} plan.`}
      </p>
      <div className="mt-6">
        <ErrorNote message={err || (job?.status === "failed" ? `The search stopped: ${job.error}` : null)} />
        {busy && <div className="panel px-5 py-8 text-center text-sm"><p className="font-semibold">{job!.progress}…</p><p className="mt-1 text-muted">Supplier lookups take a few seconds each.</p></div>}
        {job?.status === "done" && (job.items.length ? <OpportunityTable items={job.items} /> :
          <Empty title="No products found" body="Try a shorter, more general product name." />)}
        {!job && <Empty title="Check any product's real profit" body="Type a product. You'll get the same verdict, cost breakdown and break points as the daily list." />}
      </div>
    </AppShell>
  );
}
