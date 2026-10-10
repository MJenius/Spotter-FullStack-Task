import { RISK_COLORS, RISK_LEVELS } from '../lib/risk';

export function RiskLegend() {
  return (
    <div
      aria-label="Risk legend"
      className="rounded-lg border border-slate-700 bg-slate-900/90 px-3 py-2 text-xs text-slate-200 shadow-lg backdrop-blur"
    >
      <p className="mb-1 font-semibold uppercase tracking-wide text-slate-400">Weather risk</p>
      <ul className="space-y-1">
        {RISK_LEVELS.map((r) => (
          <li key={r} className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-5 rounded-sm" style={{ background: RISK_COLORS[r] }} />
            {r}
          </li>
        ))}
      </ul>
    </div>
  );
}
