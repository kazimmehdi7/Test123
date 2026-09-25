export const money = (n: number | null | undefined, signed = false) => {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  const s = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(Math.abs(n));
  if (signed) return (n < 0 ? "−" : "+") + s;
  return n < 0 ? `−${s}` : s;
};
export const pct = (n: number | null | undefined, digits = 0) =>
  n === null || n === undefined ? "—" : `${(n * 100).toFixed(digits)}%`;
export const ago = (iso?: string | number | null) => {
  if (!iso) return "—";
  const t = typeof iso === "number" ? iso * 1000 : new Date(iso + (String(iso).endsWith("Z") ? "" : "Z")).getTime();
  const m = Math.round((Date.now() - t) / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m} min ago`;
  if (m < 60 * 24) return `${Math.round(m / 60)} h ago`;
  return `${Math.round(m / 1440)} days ago`;
};
export const actionLabel: Record<string, string> = {
  SOURCE: "Source", SOURCE_SMALL: "Source small", WAIT: "Wait", SKIP: "Skip", NO_MATCH: "Add supplier",
};
export const actionColor: Record<string, string> = {
  SOURCE: "text-go", SOURCE_SMALL: "text-go", WAIT: "text-hold", SKIP: "text-stop", NO_MATCH: "text-muted",
};
export const actionMeaning: Record<string, string> = {
  SOURCE: "Profit clears your target with room to spare, and the data is solid. Order a sample and test.",
  SOURCE_SMALL: "Profit looks good, but the supplier match or data isn't certain. Verify the supplier, then test small.",
  WAIT: "Not enough profit today, but demand is climbing. Watch it and act when the numbers move.",
  SKIP: "Loses money or has too little room after every cost.",
  NO_MATCH: "We couldn't find a reliable supplier. Add your supplier's price to see the real profit.",
};
