import Link from "next/link";

const EXAMPLE = [
  ["Selling price on Amazon", 19.99],
  ["Supplier price (AliExpress)", -3.2],
  ["Shipping to customer", -2.1],
  ["Import duty, China origin (estimate)", -1.6],
  ["Customs / postal fee", -1.0],
  ["Platform fees", -0.88],
  ["Ad cost per sale", -4.0],
  ["Returns allowance", -1.4],
] as const;

export default function Landing() {
  const net = EXAMPLE.reduce((s, [, v]) => s + v, 0) - 1.0; // incl. 5% buffer
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <span className="text-xl font-extrabold tracking-tight">Scoute</span>
        <nav className="flex items-center gap-5 text-sm">
          <Link href="/pricing" className="text-muted hover:text-ink">Pricing</Link>
          <Link href="/login" className="text-muted hover:text-ink">Log in</Link>
          <Link href="/signup" className="btn-primary">Start free</Link>
        </nav>
      </header>

      <section className="mx-auto grid max-w-6xl gap-12 px-6 pb-20 pt-10 md:grid-cols-[1.1fr_1fr] md:pt-16">
        <div>
          <h1 className="text-balance text-4xl font-extrabold leading-[1.08] md:text-[3.4rem]">
            Know if a product will make money before you spend a dollar on it.
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted">
            Every morning Scoute lists products that still earn after 2026 tariffs, platform fees, ads and returns.
            For each one you get the most you can pay your supplier, what would stop it making money, and an alert the day that changes.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/signup" className="btn-primary px-6 py-3 text-base">See today's opportunities</Link>
            <Link href="#how" className="btn-quiet px-6 py-3 text-base">How it works</Link>
          </div>
          <p className="mt-4 text-sm text-muted">Free plan: 3 opportunities a day and 5 product checks. No card needed.</p>
        </div>

        {/* Hero: the thing itself — one product's real math, as a manifest */}
        <figure className="panel self-start">
          <div className="flex items-start justify-between gap-4 border-b border-rule px-5 py-4">
            <div>
              <p className="font-semibold">Silicone baking mat, 2-pack</p>
              <p className="text-xs text-muted">Kitchen · sales rank 61 → 14 in 24 hours</p>
            </div>
            <span className="stamp stamp-lg stamp-land text-go">Source</span>
          </div>
          <table className="w-full text-sm">
            <tbody>
              {EXAMPLE.map(([label, v]) => (
                <tr key={label} className="border-b border-rule/70">
                  <td className="px-5 py-2 text-muted">{label}</td>
                  <td className={`num px-5 py-2 text-right ${v > 0 ? "font-semibold" : ""}`}>{v > 0 ? `$${v.toFixed(2)}` : `−$${Math.abs(v).toFixed(2)}`}</td>
                </tr>
              ))}
              <tr>
                <td className="px-5 py-3 font-bold">You keep per sale</td>
                <td className="num px-5 py-3 text-right text-lg font-extrabold text-go">${net.toFixed(2)}</td>
              </tr>
            </tbody>
          </table>
          <div className="grid grid-cols-2 border-t border-rule text-sm">
            <div className="border-r border-rule px-5 py-3"><p className="text-xs text-muted">Pay the supplier at most</p><p className="num font-bold">$5.10</p></div>
            <div className="px-5 py-3"><p className="text-xs text-muted">Stops making money if price falls below</p><p className="num font-bold">$15.40</p></div>
          </div>
          <figcaption className="border-t border-rule px-5 py-2 text-xs text-muted">Example figures.</figcaption>
        </figure>
      </section>

      <section id="how" className="border-y border-rule bg-surface">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <h2 className="text-2xl font-bold">How it works</h2>
          <ol className="mt-8 grid gap-8 md:grid-cols-4">
            {[
              ["Tell us what you sell", "Dropship, resell or affiliate. Your market, price range and categories."],
              ["Get today's list", "Products climbing Amazon's sales ranks, matched to suppliers, with every cost counted."],
              ["Check the room", "See the most you can pay, the highest ad cost you can afford, and what breaks the deal."],
              ["Watch it", "When a price, supplier cost or tariff moves your profit, we tell you — before you reorder."],
            ].map(([h, b], i) => (
              <li key={h}>
                <span className="num text-sm font-bold text-customs">Step {i + 1}</span>
                <p className="mt-2 font-semibold">{h}</p>
                <p className="mt-1 text-sm leading-relaxed text-muted">{b}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-16">
        <h2 className="text-2xl font-bold">Every verdict comes with its reasons</h2>
        <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Source", "text-go", "Clears your profit target with room to spare."],
            ["Source small", "text-go", "Good numbers, but verify the supplier before a big order."],
            ["Wait", "text-hold", "Not enough profit today, demand is rising. We'll watch it."],
            ["Skip", "text-stop", "Loses money once duty, fees and ads are counted."],
          ].map(([a, c, t]) => (
            <div key={a} className="border-t-2 border-ink pt-4">
              <span className={`stamp text-sm ${c}`}>{a}</span>
              <p className="mt-3 text-sm leading-relaxed text-muted">{t}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-rule">
        <div className="mx-auto flex max-w-6xl flex-wrap justify-between gap-4 px-6 py-8 text-sm text-muted">
          <span>Scoute</span>
          <span>Duty figures are estimates. Confirm with a customs broker before importing.</span>
        </div>
      </footer>
    </div>
  );
}
