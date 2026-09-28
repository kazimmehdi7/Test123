"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { AuthCard } from "@/components/AuthCard";

function VerifyEmailBody() {
  const token = useSearchParams().get("token") || "";
  const [state, setState] = useState<"checking" | "ok" | "error">("checking");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (!token) { setState("error"); setMsg("This verification link is missing its token."); return; }
    api("/auth/verify-email", { method: "POST", body: { token } })
      .then(() => setState("ok"))
      .catch((e: any) => { setState("error"); setMsg(e.message); });
  }, [token]);

  if (state === "checking") return <p className="text-sm text-muted">Verifying…</p>;
  if (state === "ok") return <p className="text-sm">Your email is verified. <Link href="/feed" className="font-semibold text-customs underline">Go to your feed</Link>.</p>;
  return (
    <div className="space-y-2 text-sm">
      <p>{msg || "This link is invalid or has expired."}</p>
      <p>Log in and use &ldquo;Resend verification&rdquo; from your account settings to get a new one.</p>
    </div>
  );
}

export default function VerifyEmail() {
  return (
    <AuthCard title="Verify your email" footer={<Link href="/login" className="font-semibold text-customs underline">Back to login</Link>}>
      <Suspense fallback={null}>
        <VerifyEmailBody />
      </Suspense>
    </AuthCard>
  );
}
