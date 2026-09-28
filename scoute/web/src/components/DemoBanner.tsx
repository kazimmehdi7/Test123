export function DemoBanner({ show }: { show?: boolean }) {
  if (!show) return null;
  return (
    <div className="no-print flex items-center gap-2 border-b border-hold/30 bg-hold-tint px-4 py-2 text-sm text-[#6B4A12]">
      <span className="badge-hold shrink-0">Demo</span>
      <span>
        These products and prices are samples so you can try every feature.
        Set <code className="rounded bg-white/70 px-1 py-0.5">SCOUTE_DEMO=false</code> in{" "}
        <code className="rounded bg-white/70 px-1 py-0.5">engine/.env</code> to use live Amazon and AliExpress data.
      </span>
    </div>
  );
}
