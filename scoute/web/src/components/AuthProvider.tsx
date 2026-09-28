"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, auth } from "@/lib/api";

export type Workspace = { id: string; name: string; client_name: string; logo_url: string; is_default: boolean; brief: any; has_brief: boolean };
export type User = {
  id: string; email: string; name: string; plan: "free" | "pro" | "business"; email_verified: boolean;
  limits: { searches_per_day: number; feed_items: number; watch_items: number; sentinel_items: number; workspaces: number; full_detail: boolean; reports: boolean };
  settings: Record<string, any>; workspaces: Workspace[]; demo: boolean; billing_enabled: boolean;
};

type Ctx = {
  user: User | null; loading: boolean; workspace: Workspace | null;
  setWorkspace: (id: string) => void; refresh: () => Promise<User | null>; logout: () => void;
};
const AuthCtx = createContext<Ctx>({} as Ctx);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [wsId, setWsId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!auth.get()) { setUser(null); setLoading(false); return null; }
    try {
      const u = await api<User>("/me");
      setUser(u);
      const saved = auth.workspace();
      setWsId(u.workspaces.some(w => w.id === saved) ? saved : u.workspaces.find(w => w.is_default)?.id || null);
      return u;
    } catch { setUser(null); return null; } finally { setLoading(false); }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const workspace = user?.workspaces.find(w => w.id === wsId) || user?.workspaces[0] || null;
  return (
    <AuthCtx.Provider value={{
      user, loading, workspace, refresh,
      setWorkspace: (id) => { auth.setWorkspace(id); setWsId(id); },
      logout: () => { auth.clear(); setUser(null); window.location.href = "/"; },
    }}>{children}</AuthCtx.Provider>
  );
}
