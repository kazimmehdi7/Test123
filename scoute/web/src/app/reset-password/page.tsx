"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { api, auth } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { ErrorNote } from "@/components/Empty";
import { AuthCard } from "@/components/AuthCard";

function ResetPasswordForm() {
  const router = useRouter();
  const { refresh } = useAuth();
  const token = useSearchParams().get("token") || "";
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      const r = await api<{ token: string }>("/auth/reset-password", { method: "POST", body: { token, password } });
      auth.set(r.token);
      await refresh();
      router.push("/feed");
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }

  if (!token) {
    return (
      <div className="text-sm">
        This reset link is missing its token. Request a new one from{" "}
        <Link href="/forgot-password" className="font-semibold text-customs underline">the reset page</Link>.
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <ErrorNote message={err} />
      <div>
        <label className="label" htmlFor="p">New password</label>
        <input id="p" className="field" type="password" required minLength={8} value={password} onChange={e => setPassword(e.target.value)} />
      </div>
      <button className="btn-primary w-full" disabled={busy}>{busy ? "Saving…" : "Set new password"}</button>
      <p className="text-xs text-muted">This signs you out everywhere else — any other logged-in device will need to log in again.</p>
    </form>
  );
}

export default function ResetPassword() {
  return (
    <AuthCard title="Set a new password" footer={<>Remembered it? <Link href="/login" className="font-semibold text-customs underline">Log in</Link></>}>
      <Suspense fallback={null}>
        <ResetPasswordForm />
      </Suspense>
    </AuthCard>
  );
}
