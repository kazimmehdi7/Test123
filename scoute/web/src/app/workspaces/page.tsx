"use client";

import Link from "next/link";
import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { ErrorNote, Locked } from "@/components/Empty";
import { api } from "@/lib/api";

export default function WorkspacesPage() {
  const { user, workspace, setWorkspace, refresh } = useAuth();
  const [f, setF] = useState({ name: "", client_name: "", logo_url: "" });
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const w = await api<{ id: string }>("/workspaces", {
        method: "POST",
        body: { ...f, name: f.name || f.client_name },
      });
      await refresh();
      setWorkspace(w.id);
      setF({ name: "", client_name: "", logo_url: "" });
      setErr(null);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: string) {
    await api(`/workspaces/${id}`, { method: "DELETE" }).catch((e) => setErr(e.message));
    refresh();
  }

  if (!user) return null;
  const canAdd = user.workspaces.length < user.limits.workspaces;

  return (
    <AppShell title="Client Workspaces & Agency Portfolios">
      <ErrorNote message={err} />

      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-2xl text-xs text-muted leading-relaxed">
          Manage isolated client workspaces. Each workspace maintains an independent sourcing brief, daily opportunity feed, monitored watchlist, and white-label client PDF report.
        </p>
        <span className="text-xs font-semibold text-ink">
          {user.workspaces.length} of {user.limits.workspaces} Workspaces Active
        </span>
      </div>

      {/* Workspace Cards Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 mb-8">
        {user.workspaces.map((w) => {
          const isCurrent = workspace?.id === w.id;

          return (
            <div
              key={w.id}
              className={`panel flex flex-col justify-between border p-5 transition-all duration-200 ${
                isCurrent ? "border-customs ring-1 ring-customs/30 bg-customs-tint/40" : "border-rule bg-surface hover:-translate-y-0.5 hover:border-rule-strong hover:shadow-md"
              }`}
            >
              <div>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    {w.logo_url ? (
                      <img
                        src={w.logo_url}
                        alt=""
                        className="h-9 w-9 rounded border border-rule object-contain p-0.5 bg-paper"
                      />
                    ) : (
                      <div className="flex h-9 w-9 items-center justify-center rounded border border-rule bg-paper text-xs font-bold text-customs uppercase">
                        {(w.client_name || w.name).slice(0, 2)}
                      </div>
                    )}
                    <div>
                      <h3 className="font-bold text-ink text-sm leading-snug">
                        {w.client_name || w.name}
                      </h3>
                      {w.is_default && (
                        <span className="text-[10px] font-semibold text-muted uppercase tracking-wider">
                          Primary Workspace
                        </span>
                      )}
                    </div>
                  </div>
                  {isCurrent && (
                    <span className="rounded bg-customs/10 px-2 py-0.5 text-[10px] font-bold text-customs">
                      Active
                    </span>
                  )}
                </div>

                <div className="mt-4 border-t border-rule/60 pt-3 text-xs text-muted space-y-1">
                  <p>
                    <strong className="text-ink font-semibold">Mode:</strong>{" "}
                    {w.has_brief ? w.brief.mode : "Default"}
                  </p>
                  <p className="truncate">
                    <strong className="text-ink font-semibold">Categories:</strong>{" "}
                    {w.has_brief && w.brief.categories?.length
                      ? w.brief.categories.join(", ")
                      : "All categories"}
                  </p>
                </div>
              </div>

              <div className="mt-5 border-t border-rule/60 pt-3 flex flex-wrap items-center justify-between gap-2 text-xs">
                {!isCurrent ? (
                  <button
                    className="btn-quiet text-xs font-medium py-1 px-3"
                    onClick={() => setWorkspace(w.id)}
                  >
                    Select Workspace
                  </button>
                ) : (
                  <Link href="/feed" className="btn-quiet text-xs font-medium py-1 px-3">
                    Open Feed
                  </Link>
                )}

                {user.limits.reports && (
                  <Link
                    className="btn-primary text-xs font-medium py-1 px-3"
                    href={`/report/${w.id}`}
                  >
                    Executive Report
                  </Link>
                )}

                {!w.is_default && (
                  <button
                    className="text-muted hover:text-stop underline text-xs ml-auto"
                    onClick={() => remove(w.id)}
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Add Workspace Form */}
      {!user.limits.reports ? (
        <Locked what="Multi-client agency workspaces and white-label reports" plan="Business" />
      ) : canAdd ? (
        <form
          onSubmit={create}
          className="panel max-w-xl p-6 shadow-sm"
        >
          <h2 className="text-sm font-bold text-ink">Create Client Workspace</h2>
          <p className="mt-1 text-xs text-muted leading-relaxed">
            Configure a dedicated sourcing portfolio for an agency client.
          </p>

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <label className="block sm:col-span-2">
              <span className="label text-xs">Client or Brand Name</span>
              <input
                className="field text-xs"
                required
                placeholder="e.g. Apex Ecommerce LLC"
                value={f.client_name}
                onChange={(e) => setF({ ...f, client_name: e.target.value })}
              />
            </label>

            <label className="block sm:col-span-2">
              <span className="label text-xs">Client Logo URL (Optional)</span>
              <input
                className="field text-xs"
                placeholder="https://example.com/logo.png"
                value={f.logo_url}
                onChange={(e) => setF({ ...f, logo_url: e.target.value })}
              />
            </label>

            <div className="sm:col-span-2 pt-2">
              <button className="btn-primary text-xs font-semibold px-5" disabled={saving}>
                {saving ? "Creating Workspace..." : "Create Workspace"}
              </button>
            </div>
          </div>
        </form>
      ) : (
        <div className="kpi-card p-4 text-xs text-muted max-w-xl shadow-sm">
          You have utilized all {user.limits.workspaces} client workspaces available on your Business plan.
        </div>
      )}
    </AppShell>
  );
}
