"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "./AuthProvider";
import { DemoBanner } from "./DemoBanner";
import { api, withWs } from "@/lib/api";

const NAV = [
  { href: "/feed", label: "Today's opportunities" },
  { href: "/search", label: "Check a product" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/workspaces", label: "Clients" },
  { href: "/settings", label: "Settings" },
];

export function AppShell({ children, title, actions }: { children: React.ReactNode; title: string; actions?: React.ReactNode }) {
  const { user, loading, workspace, setWorkspace, logout } = useAuth();
  const path = usePathname();
  const router = useRouter();
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);

  useEffect(() => { if (!loading && !user) router.replace("/login"); }, [loading, user, router]);
  useEffect(() => {
    if (!user || !workspace) return;
    api<any[]>(withWs("/alerts", workspace.id)).then(a => setUnread(a.filter(x => !x.read).length)).catch(() => {});
  }, [user, workspace, path]);
  useEffect(() => {
    const clear = () => setUnread(0);
    window.addEventListener("scoute:alerts-read", clear);
    return () => window.removeEventListener("scoute:alerts-read", clear);
  }, []);

  if (loading || !user) return <div className="p-10 text-sm text-muted">Loading…</div>;

  return (
    <div className="min-h-screen">
      <DemoBanner show={user.demo} />
      <div className="flex">
        <aside className={`no-print fixed inset-y-0 left-0 z-30 w-60 border-r border-rule bg-surface p-5 transition-transform md:sticky md:top-0 md:h-screen md:overflow-y-auto md:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
          <Link href="/feed" className="block text-xl font-extrabold tracking-tight">Scoute</Link>
          {user.workspaces.length > 1 && (
            <label className="mt-6 block">
              <span className="text-xs text-muted">Workspace</span>
              <select className="field mt-1" value={workspace?.id} onChange={e => setWorkspace(e.target.value)}>
                {user.workspaces.map(w => <option key={w.id} value={w.id}>{w.client_name || w.name}</option>)}
              </select>
            </label>
          )}
          <nav className="mt-6 space-y-0.5">
            {NAV.map(n => {
              const active = path.startsWith(n.href);
              return (
                <Link key={n.href} href={n.href} onClick={() => setOpen(false)}
                      className={`flex items-center justify-between border-l-2 px-3 py-2 text-sm ${active ? "border-customs bg-paper font-semibold" : "border-transparent text-muted hover:text-ink"}`}>
                  {n.label}
                  {n.href === "/watchlist" && unread > 0 && <span className="rounded-sm bg-stop px-1.5 text-xs font-bold text-white">{unread}</span>}
                </Link>
              );
            })}
          </nav>
          <div className="mt-8 border-t border-rule pt-4 text-xs text-muted">
            <p className="truncate">{user.email}</p>
            <p className="mt-1">{user.plan.charAt(0).toUpperCase() + user.plan.slice(1)} plan · <Link href="/pricing" className="text-customs underline">Change</Link></p>
            <button onClick={logout} className="mt-3 underline">Log out</button>
          </div>
        </aside>
        <main className="min-w-0 flex-1">
          <header className="no-print flex items-center gap-3 border-b border-rule bg-surface px-5 py-4 md:px-8">
            <button className="btn-quiet px-2 py-1 md:hidden" onClick={() => setOpen(!open)} aria-label="Menu">☰</button>
            <h1 className="flex-1 text-lg font-bold">{title}</h1>
            {actions}
          </header>
          <div className="px-5 py-6 md:px-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
