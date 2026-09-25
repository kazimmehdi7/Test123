export function DemoBanner({ show }: { show?: boolean }) {
  if (!show) return null;
  return (
    <div className="border-b border-hold/40 bg-[#FBF3E4] px-4 py-2 text-sm text-[#6B4A12]">
      <strong className="font-semibold">Demo data.</strong> These products and prices are samples so you can try every feature.
      Set <code className="rounded bg-white/70 px-1">SCOUTE_DEMO=false</code> in <code className="rounded bg-white/70 px-1">engine/.env</code> to use live Amazon and AliExpress data.
    </div>
  );
}
