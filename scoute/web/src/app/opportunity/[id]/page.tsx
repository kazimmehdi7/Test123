"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { ErrorNote, Locked } from "@/components/Empty";
import { Safety, Stamp } from "@/components/Stamp";
import { api, withWs } from "@/lib/api";
import { actionMeaning, ago, money, pct } from "@/lib/format";

const EDITABLE: Record<string, { label: string; kind: "money" | "pct" }> = {
  sell: { label: "Selling price", kind: "money" }, supplier: { label: "Supplier price", kind: "money" },
  ship: { label: "Shipping to customer", kind: "money" }, duty_rate: { label: "Import duty rate", kind: "pct" },
  broker: { label: "Customs / postal fee", kind: "money" }, ad_pct: { label: "Ad cost per sale", kind: "pct" },
  return_rate: { label: "Return rate", kind: "pct" }, target_pct: { label: "Profit you want to keep", kind: "pct" },
};

export default function OpportunityPage() {
  const { id } = useParams<{ id: string }>();
  const { user, workspace } = useAuth();
  const [o, setO] = useState<any>(null);
  const [calc, setCalc] = useState<any>(null);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => { api(`/opportunities/${id}`).then(setO).catch(e => setErr(e.message)); }, [id]);

  const view = calc ? { ...o, profit: calc.profit, failure: calc.failure, verdict: calc.verdict, action: calc.verdict.action, inputs: calc.inputs } : o;

  async function recalc() {
    const overrides: Record<string, number> = {};
    for (const [k, v] of Object.entries(edits)) {
      if (v === "") continue;
      overrides[k] = EDITABLE[k]?.kind === "pct" ? parseFloat(v) / 100 : parseFloat(v);
    }
    try { setCalc(await api(`/opportunities/${id}/recalc`, { method: "POST", body: { overrides } })); setErr(null); }
    catch (e: any) { setErr(e.message); }
  }
  async function watch() {
    try {
      const overrides = calc ? calc.inputs : {};
      const r = await api(withWs("/watchlist", null), { method: "POST", body: { opportunity_id: id, workspace_id: workspace?.id, overrides } });
      setNote(r.already ? "Already on your watchlist." : "Added to your watchlist. We'll alert you when the profit changes.");
    } catch (e: any) { setErr(e.message); }
  }

  if (!o) return <AppShell title="Opportunity"><ErrorNote message={err} />{!err && <p className="text-sm text-muted">Loading…</p>}</AppShell>;
  const p = view.profit, f = view.failure, sell = o.sell, sup = o.supplier;

  return (
    <AppShell title="Opportunity" actions={<Link href="/feed" className="btn-quiet">Back to list</Link>}>
      <ErrorNote message={err} />
      {note && <p className="mb-4 border-l-4 border-go bg-surface px-4 py-3 text-sm">{note}</p>}

      <section className="panel mb-6 grid gap-6 p-6 md:grid-cols-[1fr_auto]">
        <div>
          <p className="text-sm capitalize text-muted">{o.category === "default" ? "Search" : o.category} <span className="normal-case">· {o.why_today}</span></p>
          <h2 className="mt-1 max-w-3xl text-2xl font-bold leading-snug">{sell.title}</h2>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">{actionMeaning[view.action]}</p>
          <ul className="mt-4 space-y-1.5 text-sm">
            {(view.verdict?.reasons || []).map((r: string) => <li key={r} className="border-l-2 border-rule pl-3">{r}</li>)}
          </ul>
          {o.assumptions?.length > 0 && (
            <div className="mt-4 border-l-4 border-hold bg-[#FBF3E4] px-4 py-3 text-sm">
              <p className="font-semibold text-[#6B4A12]">What we had to assume</p>
              <ul className="mt-1 space-y-1 text-[#6B4A12]">{o.assumptions.map((a: string) => <li key={a}>{a}</li>)}</ul>
            </div>
          )}
          <div className="no-print mt-5 flex flex-wrap gap-2">
            {p && <button className="btn-primary" onClick={watch}>Watch this</button>}
            {sup?.url && <a className="btn-quiet" href={sup.url} target="_blank" rel="noreferrer">Open supplier</a>}
            <a className="btn-quiet" href={sell.affiliate_url || sell.url} target="_blank" rel="noreferrer">Open on {sell.source === "amazon" ? "Amazon" : sell.source}</a>
          </div>
        </div>
        <div className="flex flex-col items-start gap-4 md:items-end">
          <Stamp action={view.action} size="lg" land />
          {p && <div className="md:text-right"><p className="text-xs text-muted">You keep per sale</p>
            <p className={`num text-3xl font-extrabold ${p.net > 0 ? "text-go" : "text-stop"}`}>{money(p.net)}</p>
            <p className="num text-sm text-muted">{pct(p.margin)} of the selling price</p></div>}
        </div>
      </section>

      {!p ? (
        <NoMatch o={o} canEdit={!!user?.limits.full_detail} edits={edits} setEdits={setEdits} recalc={recalc} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1.15fr_1fr]">
          <section className="panel">
            <h3 className="border-b border-rule px-5 py-3 font-semibold">The math, per unit</h3>
            {o.locked ? <div className="p-5"><Row label="Selling price" v={p.sell} /><Row label="You keep" v={p.net} bold /><div className="mt-4"><Locked what="The full cost breakdown" /></div></div> : (
              <>
                <table className="w-full text-sm"><tbody>
                  {p.lines.map((l: any) => <tr key={l.key} className="border-b border-rule/70">
                    <td className="px-5 py-2 text-muted">{l.label}{l.key === "duty" && view.duty && <span className="block text-xs">{view.duty.label}{view.duty.hts !== "—" ? ` · HTS ${view.duty.hts}` : ""}{view.duty.high ? ` · ${pct(view.duty.low)}–${pct(view.duty.high)}` : ""}</span>}</td>
                    <td className={`num px-5 py-2 text-right ${l.amount > 0 ? "font-semibold" : ""}`}>{money(l.amount)}</td></tr>)}
                  <tr><td className="px-5 py-3 font-bold">You keep per sale</td><td className={`num px-5 py-3 text-right text-lg font-extrabold ${p.net > 0 ? "text-go" : "text-stop"}`}>{money(p.net)}</td></tr>
                </tbody></table>
                <div className="grid grid-cols-2 border-t border-rule text-sm">
                  <div className="border-r border-rule px-5 py-4"><p className="text-xs text-muted">Pay the supplier at most</p><p className="num text-xl font-bold">{money(p.max_buy_price)}</p><p className="text-xs text-muted">to keep your {money(p.target)} target</p></div>
                  <div className="px-5 py-4"><p className="text-xs text-muted">Spend on ads per sale at most</p><p className="num text-xl font-bold">{money(p.max_ad_per_sale)}</p><p className="text-xs text-muted">before you miss your target</p></div>
                </div>
                {o.profit_alt && !calc && (
                  <div className="border-t border-rule px-5 py-4 text-sm">
                    <p className="font-semibold">{o.profit_alt.sourcing === "us_warehouse" ? "With a US warehouse supplier instead" : "Shipping from China instead"}</p>
                    <p className="mt-1 text-muted">You'd keep <span className={`num font-semibold ${o.profit_alt.net > 0 ? "text-go" : "text-stop"}`}>{money(o.profit_alt.net)}</span> per sale
                      ({o.profit_alt.sourcing === "us_warehouse" ? "no import duty, about 30% higher supplier price — edit in Settings" : "includes import duty"}).</p>
                  </div>
                )}
                {user?.limits.full_detail && (
                  <details className="no-print border-t border-rule px-5 py-4 text-sm">
                    <summary className="cursor-pointer font-semibold text-customs">Use your own numbers</summary>
                    <div className="mt-4 grid grid-cols-2 gap-3">
                      {Object.entries(EDITABLE).map(([k, m]) => (
                        <label key={k}><span className="text-xs text-muted">{m.label} {m.kind === "pct" ? "(%)" : "($)"}</span>
                          <input className="field num mt-1" inputMode="decimal"
                                 placeholder={view.inputs ? (m.kind === "pct" ? (view.inputs[k] * 100).toFixed(1) : String(view.inputs[k])) : ""}
                                 value={edits[k] ?? ""} onChange={e => setEdits({ ...edits, [k]: e.target.value })} /></label>
                      ))}
                    </div>
                    <div className="mt-4 flex gap-2"><button className="btn-primary" onClick={recalc}>Recalculate</button>
                      {calc && <button className="btn-quiet" onClick={() => { setCalc(null); setEdits({}); }}>Reset</button>}</div>
                  </details>
                )}
              </>
            )}
          </section>

          <div className="space-y-6">
            <section className="panel">
              <div className="flex items-center justify-between border-b border-rule px-5 py-3"><h3 className="font-semibold">What would stop it making money</h3>{f && <Safety level={f.safety} />}</div>
              {!f ? <div className="p-5"><Locked what="The failure map" /></div> : (
                <>
                  <table className="w-full text-sm"><tbody>
                    {f.points.map((pt: any) => (
                      <tr key={pt.key} className="border-b border-rule/70">
                        <td className="px-5 py-2.5">{pt.label} {pt.direction === "down" ? "falls below" : "rises above"}</td>
                        <td className="num px-3 py-2.5 text-right font-semibold">{pt.break_point === null ? "never" : pt.kind === "money" ? money(pt.break_point) : pt.kind === "pct_of_sell" ? money(pt.break_point * p.sell) : pct(pt.break_point, 1)}</td>
                        <td className="num px-5 py-2.5 text-right text-xs text-muted">{pt.distance === null || pt.break_point === null ? "" : pt.kind === "pct" ? `+${((pt.break_point - pt.current) * 100).toFixed(0)} pts` : `${pct(pt.distance)} away`}</td>
                      </tr>))}
                  </tbody></table>
                  {f.biggest_risks.length > 0 && <div className="px-5 py-4 text-sm"><p className="font-semibold">Biggest risks</p>
                    <ul className="mt-2 space-y-1 text-muted">{f.biggest_risks.map((r: any) => <li key={r.label}>{r.label} 10% worse → profit falls {pct(r.drop)}</li>)}</ul></div>}
                </>
              )}
            </section>

            <section className="panel text-sm">
              <h3 className="border-b border-rule px-5 py-3 font-semibold">Supplier</h3>
              {sup ? <div className="space-y-1 px-5 py-4">
                <p className="font-medium">{sup.title}</p>
                <p className="text-muted">{money(sup.price)}{sup.shipping_cost === 0 ? " · free shipping" : sup.shipping_cost ? ` + ${money(sup.shipping_cost)} shipping` : ""}
                  {sup.sold_count ? ` · ${sup.sold_count.toLocaleString()} sold` : ""}{sup.rating ? ` · ${sup.rating}★` : ""}{sup.shipping_days ? ` · ${sup.shipping_days}` : ""}</p>
                <p className="text-xs text-muted">Match confidence {pct(o.match_confidence)}. Check the listing is the same product before ordering.</p>
              </div> : <p className="px-5 py-4 text-muted">No supplier matched.</p>}
            </section>

            {o.mode === "affiliate" || o.risk?.modes?.length === 1 ? (
              <section className="panel px-5 py-4 text-sm"><p className="font-semibold">As an affiliate</p>
                <p className="mt-1 text-muted">About {money(o.affiliate?.per_sale)} commission per sale at an estimated {pct(o.affiliate?.rate, 1)} rate.</p></section>
            ) : null}
            {o.risk?.reason && <section className="border-l-4 border-hold bg-surface px-5 py-4 text-sm">{o.risk.reason}</section>}

            {o.launch && (
              <section className="panel px-5 py-4 text-sm"><h3 className="font-semibold">Launch notes</h3>
                <p className="mt-2 text-xs text-muted">Keywords</p><p>{o.launch.keywords.join(", ")}</p>
                {o.launch.angles.length > 0 && <><p className="mt-3 text-xs text-muted">Ad angles</p><ul className="list-disc pl-5">{o.launch.angles.map((a: string) => <li key={a}>{a}</li>)}</ul></>}
              </section>
            )}

            <section className="panel px-5 py-4 text-xs text-muted">
              <p className="mb-2 text-sm font-semibold text-ink">Where these numbers come from</p>
              <ul className="space-y-1">{o.evidence?.map((e: any) => <li key={e.what}>{e.what}: {e.url ? <a className="underline" href={e.url} target="_blank" rel="noreferrer">{e.source}</a> : e.source}{e.fetched_at ? `, checked ${ago(e.fetched_at)}` : ""}{e.demo ? " (demo)" : ""}</li>)}</ul>
              <p className="mt-2">Data confidence {pct(o.confidence)}. Duty table as of {o.duty_version}. Duty is an estimate; confirm with a customs broker.</p>
            </section>
          </div>
        </div>
      )}
    </AppShell>
  );
}

function Row({ label, v, bold }: { label: string; v: number; bold?: boolean }) {
  return <div className="flex justify-between border-b border-rule/70 py-2 text-sm"><span className="text-muted">{label}</span><span className={`num ${bold ? "font-bold" : ""}`}>{money(v)}</span></div>;
}

function NoMatch({ o, canEdit, edits, setEdits, recalc }: any) {
  return (
    <section className="panel max-w-xl p-5 text-sm">
      <h3 className="font-semibold">Add your supplier's price</h3>
      <p className="mt-1 text-muted">We couldn't match a supplier with enough confidence{o.sell.price ? "" : ", and the selling price wasn't available"}. Enter your numbers to see the real profit.</p>
      {canEdit ? (
        <div className="mt-4 grid grid-cols-2 gap-3">
          {!o.sell.price && <label><span className="text-xs text-muted">Selling price ($)</span><input className="field num mt-1" value={edits.sell ?? ""} onChange={e => setEdits({ ...edits, sell: e.target.value })} /></label>}
          <label><span className="text-xs text-muted">Supplier price ($)</span><input className="field num mt-1" value={edits.supplier ?? ""} onChange={e => setEdits({ ...edits, supplier: e.target.value })} /></label>
          <label><span className="text-xs text-muted">Shipping ($)</span><input className="field num mt-1" value={edits.ship ?? ""} onChange={e => setEdits({ ...edits, ship: e.target.value })} /></label>
          <div className="col-span-2"><button className="btn-primary" onClick={recalc}>Calculate profit</button></div>
        </div>
      ) : <div className="mt-4"><Locked what="Entering your own numbers" /></div>}
    </section>
  );
}
