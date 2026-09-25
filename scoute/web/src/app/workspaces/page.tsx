"use client";
import Link from "next/link";
import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { ErrorNote, Locked } from "@/components/Empty";
import { api } from "@/lib/api";

export default function Workspaces() {
  const { user, workspace, setWorkspace, refresh } = useAuth();
  const [f, setF] = useState({ name: "", client_name: "", logo_url: "" });
  const [err, setErr] = useState<string | null>(null);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    try {
      const w = await api("/workspaces", { method: "POST", body: { ...f, name: f.name || f.client_name } });
      await refresh(); setWorkspace(w.id); setF({ name: "", client_name: "", logo_url: "" });
    } catch (e: any) { setErr(e.message); }
  }
  async function remove(id: string) { await api(`/workspaces/${id}`, { method: "DELETE" }).catch(e => setErr(e.message)); refresh(); }

  if (!user) return null;
  const canAdd = user.workspaces.length < user.limits.workspaces;
  return (
    <AppShell title="Clients">
      <ErrorNote message={err} />
      <p className="mb-4 max-w-2xl text-sm text-muted">Each client gets their own brief, daily list, watchlist and a branded report you can send them.</p>
      <div className="panel mb-6 divide-y divide-rule">
        {user.workspaces.map(w => (
          <div key={w.id} className="flex flex-wrap items-center gap-3 px-4 py-3 text-sm">
            <div className="flex-1"><p className="font-semibold">{w.client_name || w.name}</p>
              <p className="text-xs text-muted">{w.has_brief ? `${w.brief.mode} · ${(w.brief.categories || []).join(", ")}` : "No brief yet"}{w.is_default ? " · your main workspace" : ""}</p></div>
            {workspace?.id === w.id ? <span className="text-xs font-semibold text-customs">Current</span> :
              <button className="btn-quiet py-1" onClick={() => setWorkspace(w.id)}>Switch to</button>}
            {user.limits.reports && <Link className="btn-quiet py-1" href={`/report/${w.id}`}>Client report</Link>}
            {!w.is_default && <button className="text-xs text-muted underline" onClick={() => remove(w.id)}>Delete</button>}
          </div>
        ))}
      </div>
      {!user.limits.reports ? <Locked what="Client workspaces and branded reports" plan="Business" /> : canAdd ? (
        <form onSubmit={create} className="panel grid max-w-2xl gap-3 p-5 sm:grid-cols-2">
          <h2 className="font-semibold sm:col-span-2">Add a client</h2>
          <label><span className="label">Client name</span><input className="field" required value={f.client_name} onChange={e => setF({ ...f, client_name: e.target.value })} /></label>
          <label><span className="label">Logo URL <span className="font-normal text-muted">(optional)</span></span><input className="field" value={f.logo_url} onChange={e => setF({ ...f, logo_url: e.target.value })} /></label>
          <div className="sm:col-span-2"><button className="btn-primary">Add client</button></div>
        </form>
      ) : <p className="text-sm text-muted">You've used all {user.limits.workspaces} workspaces on your plan.</p>}
    </AppShell>
  );
}
