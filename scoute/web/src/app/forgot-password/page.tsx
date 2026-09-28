"use client";
import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import { ErrorNote } from "@/components/Empty";
import { AuthCard } from "@/components/AuthCard";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [devToken, setDevToken] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      const r = await api<{ ok: boolean; dev_reset_token?: string }>("/auth/forgot-password", { method: "POST", body: { email } });
      setSent(true);
      if (r.dev_reset_token) setDevToken(r.dev_reset_token);
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }

  return (
    <AuthCard title="Reset your password" footer={<>Remembered it? <Link href="/login" className="font-semibold text-customs underline">Log in</Link></>}>
      {sent ? (
        <div className="space-y-3 text-sm">
          <p>If an account exists for <strong>{email}</strong>, a reset link is on its way. Check your inbox — the link expires in 1 hour.</p>
          {devToken && (
            <div className="rounded border border-rule bg-paper/50 p-3 text-xs">
              <p className="mb-1 font-semibold text-muted">Dev mode — no email sender configured, so here's the link:</p>
              <Link href={`/reset-password?token=${devToken}`} className="break-all text-customs underline">
                /reset-password?token={devToken}
              </Link>
            </div>
          )}
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <ErrorNote message={err} />
          <div><label className="label" htmlFor="e">Email</label><input id="e" className="field" type="email" required value={email} onChange={e => setEmail(e.target.value)} /></div>
          <button className="btn-primary w-full" disabled={busy}>{busy ? "Sending…" : "Send reset link"}</button>
        </form>
      )}
    </AuthCard>
  );
}
