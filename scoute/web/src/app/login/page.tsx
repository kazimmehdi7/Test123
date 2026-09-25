"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, auth } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { ErrorNote } from "@/components/Empty";
import { AuthCard } from "@/components/AuthCard";

export default function Login() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      const r = await api<{ token: string }>("/auth/login", { method: "POST", body: { email, password } });
      auth.set(r.token);
      await refresh();
      router.push("/feed");
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }

  return (
    <AuthCard title="Log in to Scoute" footer={<>New here? <Link href="/signup" className="font-semibold text-customs underline">Create an account</Link></>}>
      <form onSubmit={submit} className="space-y-4">
        <ErrorNote message={err} />
        <div><label className="label" htmlFor="e">Email</label><input id="e" className="field" type="email" required value={email} onChange={e => setEmail(e.target.value)} /></div>
        <div><label className="label" htmlFor="p">Password</label><input id="p" className="field" type="password" required value={password} onChange={e => setPassword(e.target.value)} /></div>
        <button className="btn-primary w-full" disabled={busy}>{busy ? "Logging in…" : "Log in"}</button>
      </form>
    </AuthCard>
  );
}
