import { RISK_COLORS, RISK_LEVELS } from '../lib/risk';

const RISK_DESCRIPTIONS: Record<string, string> = {
  Low: 'Benign wind, rain & snow',
  Moderate: 'Cautionary weather',
  High: 'Heavy precipitation / gusty',
  Severe: 'Dangerous winds / heavy snow',
  'No Travel': 'Unsafe for trucks; route blocked',
  Unknown: 'Missing forecast; unverified',
};

export function RiskLegend() {
  return (
    <div
      aria-label="Risk legend"
      className="max-w-[240px] rounded-lg border border-slate-700/80 bg-slate-900/95 p-2.5 text-xs text-slate-200 shadow-xl backdrop-blur-md"
    >
      <div className="mb-1.5 flex items-center justify-between border-b border-slate-800 pb-1">
        <span className="font-bold uppercase tracking-wider text-slate-300">Weather Risk</span>
        <span className="text-[10px] text-slate-500">Hazard tier</span>
      </div>
      <ul className="space-y-1">
        {RISK_LEVELS.map((r) => (
          <li key={r} className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <span
                className="inline-block h-2.5 w-4 rounded-sm shadow-sm"
                style={{ background: RISK_COLORS[r] }}
                aria-hidden="true"
              />
              <span className="font-medium text-slate-200">{r}</span>
            </div>
            <span className="text-[10px] text-slate-400">{RISK_DESCRIPTIONS[r]}</span>
          </li>
        ))}
      </ul>
      <div className="mt-2 border-t border-slate-800/80 pt-1.5 text-[9px] leading-tight text-slate-400">
        • Segments colored by checkpoint risk.
        <br />• Halos indicate weather corridor around checkpoints.
      </div>
    </div>
  );
}
