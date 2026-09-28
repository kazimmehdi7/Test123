"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "./AuthProvider";
import { DemoBanner } from "./DemoBanner";
import { api, withWs } from "@/lib/api";

const NAV = [
  { href: "/feed", label: "Daily Opportunities" },
  { href: "/sentinel", label: "Margin Sentinel" },
  { href: "/search", label: "Check a Product" },
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

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center gap-3 text-sm text-muted">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-rule border-t-customs" />
        Loading…
      </div>
    );
  }

  const initial = (user.name || user.email).charAt(0).toUpperCase();

  return (
    <div className="min-h-screen">
      <DemoBanner show={user.demo} />
      <div className="flex">
        {open && <div className="no-print fixed inset-0 z-20 bg-ink/30 backdrop-blur-[1px] md:hidden" onClick={() => setOpen(false)} aria-hidden />}
        <aside className={`no-print fixed inset-y-0 left-0 z-30 flex w-64 flex-col border-r border-rule bg-surface transition-transform duration-200 ease-out md:sticky md:top-0 md:h-screen md:translate-x-0 ${open ? "translate-x-0 shadow-lg" : "-translate-x-full"}`}>
          <div className="flex items-center gap-2 border-b border-rule px-5 py-5">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-grad-customs text-sm font-extrabold text-white shadow-sm">S</span>
            <Link href="/feed" className="text-lg font-extrabold tracking-tight">Scoute</Link>
          </div>

          {user.workspaces.length > 1 && (
            <div className="border-b border-rule px-4 py-3">
              <label className="block">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-muted">Workspace</span>
                <select className="field mt-1 text-sm" value={workspace?.id} onChange={e => setWorkspace(e.target.value)}>
                  {user.workspaces.map(w => <option key={w.id} value={w.id}>{w.client_name || w.name}</option>)}
                </select>
              </label>
            </div>
          )}

          <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-4">
            {NAV.map(n => {
              const active = path.startsWith(n.href);
              return (
                <Link key={n.href} href={n.href} onClick={() => setOpen(false)} className={active ? "nav-item-active" : "nav-item"}>
                  <span>{n.label}</span>
                  {n.href === "/watchlist" && unread > 0 && (
                    <span className="flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-stop px-1 text-[11px] font-bold text-white">{unread}</span>
                  )}
                </Link>
              );
            })}
          </nav>

          <div className="border-t border-rule p-4">
            <div className="flex items-center gap-2.5 rounded-md bg-surface-sunken p-2.5">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-customs-tint text-sm font-bold text-customs">{initial}</span>
              <div className="min-w-0 flex-1 text-xs">
                <p className="truncate font-semibold text-ink">{user.email}</p>
                <p className="mt-0.5 text-muted">
                  <span className="badge-customs px-1.5 py-0">{user.plan}</span>{" "}
                  <Link href="/pricing" className="font-medium text-customs hover:underline">Change</Link>
                </p>
              </div>
            </div>
            <button onClick={logout} className="mt-2 w-full rounded-md px-2.5 py-1.5 text-left text-xs font-medium text-muted transition-colors hover:bg-surface-sunken hover:text-stop">
              Log out
            </button>
          </div>
        </aside>
        <main className="min-w-0 flex-1">
          <header className="no-print sticky top-0 z-10 flex items-center gap-3 border-b border-rule bg-surface/85 px-5 py-4 backdrop-blur-md md:px-8">
            <button className="btn-quiet px-2 py-1.5 md:hidden" onClick={() => setOpen(!open)} aria-label="Menu">☰</button>
            <h1 className="flex-1 text-lg font-bold tracking-tight">{title}</h1>
            {actions}
          </header>
          <div className="animate-fade-in px-5 py-6 md:px-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
