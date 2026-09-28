"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { ErrorNote } from "@/components/Empty";
import { api } from "@/lib/api";

const FIELDS: [string, string, string][] = [
  ["ad_cost_pct", "Ad cost per sale", "What you expect to spend on ads for each sale, as a share of the price."],
  ["target_profit_pct", "Profit you want to keep", "Scoute calls a product Source only when it clears this."],
  ["buffer_pct", "Uncertainty buffer", "Set aside for surprises: price changes, chargebacks, damaged items."],
  ["us_warehouse_premium", "US warehouse price premium", "How much more US-stocked suppliers usually charge than China-direct."],
];

export default function Settings() {
  const { user, refresh } = useAuth();
  const [s, setS] = useState<Record<string, any>>({});
  const [name, setName] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [resending, setResending] = useState(false);

  async function resendVerification() {
    setResending(true);
    try {
      const r = await api<{ ok: boolean; already_verified?: boolean; dev_verify_token?: string }>("/auth/resend-verification", { method: "POST" });
      if (r.already_verified) { await refresh(); setMsg("Your email is already verified."); }
      else if (r.dev_verify_token) setMsg(`Dev mode — no email sender configured. Verification link: /verify-email?token=${r.dev_verify_token}`);
      else setMsg("Verification email sent — check your inbox.");
      setErr(null);
    } catch (e: any) { setErr(e.message); } finally { setResending(false); }
  }

  useEffect(() => { if (user) { setS(user.settings); setName(user.name); } }, [user]);
  useEffect(() => { if (typeof window !== "undefined" && location.search.includes("upgraded")) setMsg("Your plan is active. Thanks for upgrading."); }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api("/me/settings", { method: "PATCH", body: { ...Object.fromEntries(FIELDS.map(([k]) => [k, Number(s[k])])), alert_email: !!s.alert_email, name } });
      await refresh(); setMsg("Settings saved. New numbers apply to products you open from now on."); setErr(null);
    } catch (e: any) { setErr(e.message); }
  }

  if (!user) return null;
  return (
    <AppShell title="Settings">
      <ErrorNote message={err} />
      {msg && <p className="mb-4 border-l-4 border-go bg-surface px-4 py-3 text-sm">{msg}</p>}
      <form onSubmit={save} className="max-w-2xl space-y-6">
        <section className="panel p-5">
          <h2 className="font-semibold">Your default costs</h2>
          <p className="mt-1 text-sm text-muted">These go into every profit calculation. You can still change them per product.</p>
          <div className="mt-5 space-y-5">
            {FIELDS.map(([k, label, hint]) => (
              <label key={k} className="block">
                <span className="label">{label}</span>
                <div className="flex items-center gap-2"><input className="field num w-28" type="number" step="0.5" min="0" max="200"
                  value={s[k] !== undefined ? +(s[k] * 100).toFixed(1) : ""} onChange={e => setS({ ...s, [k]: Number(e.target.value) / 100 })} /><span className="text-sm text-muted">%</span></div>
                <p className="hint">{hint}</p>
              </label>
            ))}
          </div>
        </section>
        <section className="panel space-y-4 p-5">
          <h2 className="font-semibold">Account</h2>
          <label className="block"><span className="label">Name</span><input className="field" value={name} onChange={e => setName(e.target.value)} /></label>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={!!s.alert_email} onChange={e => setS({ ...s, alert_email: e.target.checked })} /> Email me when a watched product's profit changes</label>
          <p className="text-sm text-muted">Plan: <strong className="text-ink">{user.plan}</strong>. <Link href="/pricing" className="text-customs underline">Change plan</Link></p>
          <p className="text-sm text-muted">
            Email: <strong className="text-ink">{user.email}</strong>{" "}
            {user.email_verified ? (
              <span className="text-go">Verified</span>
            ) : (
              <>
                <span className="text-stop">Not verified</span> —{" "}
                <button type="button" className="text-customs underline disabled:opacity-50" disabled={resending} onClick={resendVerification}>
                  {resending ? "Sending…" : "Resend verification email"}
                </button>
              </>
            )}
          </p>
        </section>
        <button className="btn-primary">Save settings</button>
      </form>
    </AppShell>
  );
}
