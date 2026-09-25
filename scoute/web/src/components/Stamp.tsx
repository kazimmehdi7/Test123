import { actionColor, actionLabel } from "@/lib/format";

export function Stamp({ action, size = "sm", land = false }: { action: string; size?: "sm" | "lg"; land?: boolean }) {
  return (
    <span className={`stamp ${size === "lg" ? "stamp-lg" : "text-[0.7rem]"} ${land ? "stamp-land" : ""} ${actionColor[action] || "text-muted"}`}
          aria-label={`Verdict: ${actionLabel[action] || action}`}>
      {actionLabel[action] || action}
    </span>
  );
}

export function Safety({ level }: { level?: string }) {
  if (!level) return <span className="text-muted">—</span>;
  const c = level === "HIGH" ? "text-go" : level === "MEDIUM" ? "text-hold" : "text-stop";
  const bars = level === "HIGH" ? 3 : level === "MEDIUM" ? 2 : 1;
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-semibold ${c}`} title={`Margin of safety: ${level.toLowerCase()}`}>
      <span className="inline-flex gap-[2px]" aria-hidden>
        {[1, 2, 3].map(i => <span key={i} className={`h-3 w-1 ${i <= bars ? "bg-current" : "bg-rule"}`} />)}
      </span>
      {level.charAt(0) + level.slice(1).toLowerCase()}
    </span>
  );
}
