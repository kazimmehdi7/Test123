"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, auth } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { ErrorNote } from "@/components/Empty";
import { AuthCard } from "@/components/AuthCard";

export default function Signup() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [f, setF] = useState({ name: "", email: "", password: "" });
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (f.password.length < 8) return setErr("Use at least 8 characters for your password");
    setBusy(true); setErr(null);
    try {
      const r = await api<{ token: string }>("/auth/register", { method: "POST", body: f });
      auth.set(r.token);
      await refresh();
      router.push("/onboarding");
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }

  return (
    <AuthCard title="Create your account" footer={<>Already have one? <Link href="/login" className="font-semibold text-customs underline">Log in</Link></>}>
      <form onSubmit={submit} className="space-y-4">
        <ErrorNote message={err} />
        <div><label className="label" htmlFor="n">Name</label><input id="n" className="field" value={f.name} onChange={e => setF({ ...f, name: e.target.value })} /></div>
        <div><label className="label" htmlFor="e">Email</label><input id="e" className="field" type="email" required value={f.email} onChange={e => setF({ ...f, email: e.target.value })} /></div>
        <div>
          <label className="label" htmlFor="p">Password</label>
          <input id="p" className="field" type="password" required value={f.password} onChange={e => setF({ ...f, password: e.target.value })} />
          <p className="hint">At least 8 characters.</p>
        </div>
        <button className="btn-primary w-full" disabled={busy}>{busy ? "Creating account…" : "Create account"}</button>
      </form>
    </AuthCard>
  );
}
