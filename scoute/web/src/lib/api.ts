export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TOKEN = "scoute_token";
const WORKSPACE = "scoute_workspace";

export const auth = {
  get: () => (typeof window === "undefined" ? null : localStorage.getItem(TOKEN)),
  set: (t: string) => localStorage.setItem(TOKEN, t),
  clear: () => { localStorage.removeItem(TOKEN); localStorage.removeItem(WORKSPACE); },
  workspace: () => (typeof window === "undefined" ? null : localStorage.getItem(WORKSPACE)),
  setWorkspace: (id: string) => localStorage.setItem(WORKSPACE, id),
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) { super(message); this.status = status; }
}

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const t = auth.get();
  if (t) headers.Authorization = `Bearer ${t}`;
  let res: Response;
  try {
    res = await fetch(`${API}/api${path}`, {
      method: opts.method || "GET", headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
  } catch {
    throw new ApiError(0, `Can't reach the Scoute API at ${API}. Start it with: uvicorn app.main:app --port 8000`);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = typeof data.detail === "string" ? data.detail : `Request failed (${res.status})`;
    if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/auth")) {
      auth.clear();
      window.location.href = "/login";
    }
    throw new ApiError(res.status, msg);
  }
  return data as T;
}

export function withWs(path: string, ws: string | null) {
  if (!ws) return path;
  return path + (path.includes("?") ? "&" : "?") + `workspace_id=${ws}`;
}
