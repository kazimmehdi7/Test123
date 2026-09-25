"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { ErrorNote } from "@/components/Empty";

type Meta = { categories: { id: string; label: string }[]; channels: Record<string, string> };

export default function Onboarding() {
  const router = useRouter();
  const { user, loading, workspace, refresh } = useAuth();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [b, setB] = useState<any>({ mode: "dropship", market: "US", channel: "shopify", sourcing: "china", categories: ["kitchen", "pet", "home"],
                                    price_min: 10, price_max: 60, budget: 500, min_margin: 0.15, min_profit: 3 });
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { if (!loading && !user) router.replace("/login"); }, [loading, user, router]);
  useEffect(() => { api<Meta>("/meta").then(setMeta).catch(e => setErr(e.message)); }, []);
  useEffect(() => { if (workspace?.has_brief) setB((x: any) => ({ ...x, ...workspace.brief })); }, [workspace]);

  const maxCats = user?.plan === "free" ? 3 : 8;
  const toggle = (id: string) => setB((x: any) => ({
    ...x, categories: x.categories.includes(id) ? x.categories.filter((c: string) => c !== id)
      : x.categories.length >= maxCats ? x.categories : [...x.categories, id],
  }));

  async function save() {
    if (!workspace) return;
    try {
      await api(`/workspaces/${workspace.id}/brief`, { method: "PUT", body: b });
      await refresh();
      router.push("/feed");
    } catch (e: any) { setErr(e.message); }
  }

  const Choice = ({ k, v, label, note }: { k: string; v: string; label: string; note?: string }) => (
    <button type="button" onClick={() => setB({ ...b, [k]: v })}
            className={`border px-4 py-3 text-left text-sm ${b[k] === v ? "border-customs bg-[#EAF0F8]" : "border-rule bg-surface hover:border-muted"}`}>
      <span className="font-semibold">{label}</span>{note && <span className="mt-0.5 block text-xs text-muted">{note}</span>}
    </button>
  );

  return (
    <div className="mx-auto max-w-2xl px-5 py-12">
      <p className="text-xl font-extrabold tracking-tight">Scoute</p>
      <h1 className="mt-6 text-3xl font-bold">What are you looking for?</h1>
      <p className="mt-2 text-muted">We use this to filter your daily list. You can change it any time.</p>
      <div className="mt-8 space-y-8">
        <ErrorNote message={err} />
        <fieldset>
          <legend className="label">How you sell</legend>
          <div className="grid gap-2 sm:grid-cols-3">
            <Choice k="mode" v="dropship" label="Dropship" note="Buy from a supplier per order" />
            <Choice k="mode" v="resell" label="Resell" note="Buy low on one marketplace, sell on another" />
            <Choice k="mode" v="affiliate" label="Affiliate" note="Earn commission on sales" />
          </div>
        </fieldset>
        <div className="grid gap-6 sm:grid-cols-2">
          <fieldset>
            <legend className="label">Your customers are in</legend>
            <div className="grid grid-cols-2 gap-2"><Choice k="market" v="US" label="United States" /><Choice k="market" v="EU" label="Europe" /></div>
          </fieldset>
          <label className="block">
            <span className="label">Where you sell</span>
            <select className="field" value={b.channel} onChange={e => setB({ ...b, channel: e.target.value })}>
              {meta && Object.entries(meta.channels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
        </div>
        {b.mode === "dropship" && (
          <fieldset>
            <legend className="label">Default sourcing</legend>
            <div className="grid gap-2 sm:grid-cols-2">
              <Choice k="sourcing" v="china" label="Ships from China" note="Cheapest; you pay import duty" />
              <Choice k="sourcing" v="us_warehouse" label="US warehouse supplier" note="Costs more; duty already paid" />
            </div>
          </fieldset>
        )}
        <fieldset>
          <legend className="label">Categories <span className="font-normal text-muted">(up to {maxCats})</span></legend>
          <div className="flex flex-wrap gap-2">
            {meta?.categories.map(c => (
              <button key={c.id} type="button" onClick={() => toggle(c.id)} aria-pressed={b.categories.includes(c.id)}
                      className={`border px-3 py-1.5 text-sm ${b.categories.includes(c.id) ? "border-customs bg-customs text-white" : "border-rule bg-surface"}`}>
                {c.label}
              </button>
            ))}
          </div>
        </fieldset>
        <div className="grid gap-4 sm:grid-cols-4">
          <label><span className="label">Min price</span><input className="field num" type="number" value={b.price_min} onChange={e => setB({ ...b, price_min: +e.target.value })} /></label>
          <label><span className="label">Max price</span><input className="field num" type="number" value={b.price_max} onChange={e => setB({ ...b, price_max: +e.target.value })} /></label>
          <label><span className="label">Min profit / sale</span><input className="field num" type="number" value={b.min_profit} onChange={e => setB({ ...b, min_profit: +e.target.value })} /></label>
          <label><span className="label">Test budget</span><input className="field num" type="number" value={b.budget} onChange={e => setB({ ...b, budget: +e.target.value })} /></label>
        </div>
        <button className="btn-primary px-6 py-3" onClick={save} disabled={!b.categories.length}>Show my opportunities</button>
      </div>
    </div>
  );
}
