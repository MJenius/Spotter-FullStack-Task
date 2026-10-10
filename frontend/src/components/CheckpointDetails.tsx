import type { Checkpoint } from '../api/types';
import { RISK_BADGE_CLASSES, RISK_COLORS, formatMeasurement } from '../lib/risk';

function formatTimestamp(iso: string | null): string {
  if (!iso) return 'Unavailable';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
  });
}

export function CheckpointDetails({ checkpoint }: { checkpoint: Checkpoint }) {
  const { risk, weather } = checkpoint;
  const overallBadge = RISK_BADGE_CLASSES[risk.overall];

  return (
    <div className="w-64 max-w-[280px] space-y-2 p-1 text-slate-100">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-700 pb-1.5">
        <div>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            Checkpoint #{checkpoint.index}
          </span>
          <div className="text-xs font-medium text-slate-300">
            Mile {checkpoint.distance_miles.toFixed(1)}
            <span className="text-[10px] text-slate-500"> ({checkpoint.represented_miles.toFixed(1)} mi span)</span>
          </div>
        </div>
        <span
          className={`rounded border px-2 py-0.5 text-[11px] font-bold ${overallBadge}`}
          style={{ borderLeftColor: RISK_COLORS[risk.overall], borderLeftWidth: '3px' }}
        >
          {risk.overall}
        </span>
      </div>

      {/* ETAs and Forecast Horizon */}
      <div className="space-y-0.5 rounded bg-slate-800/80 p-1.5 text-[11px]">
        <div className="flex justify-between">
          <span className="text-slate-400">ETA:</span>
          <span className="font-semibold text-slate-200">{formatTimestamp(checkpoint.eta)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Forecast hour:</span>
          <span className="text-slate-300">{formatTimestamp(weather.forecast_time)}</span>
        </div>
        {!checkpoint.forecast_available && (
          <div className="mt-1 text-[10px] font-medium text-amber-400">
            ⚠️ Forecast unavailable for this checkpoint ETA.
          </div>
        )}
      </div>

      {/* Conditions Table */}
      <div className="rounded border border-slate-700/60 bg-slate-900/60 p-1.5 text-[11px]">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-slate-800 text-[10px] uppercase text-slate-400">
              <th className="pb-1 font-semibold">Hazard</th>
              <th className="pb-1 font-semibold">Reading</th>
              <th className="pb-1 text-right font-semibold">Risk</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            <tr>
              <td className="py-1 text-slate-400">Wind</td>
              <td className="py-1 font-mono text-slate-200">{formatMeasurement(weather.wind_mph, 'mph', 1)}</td>
              <td className="py-1 text-right font-semibold" style={{ color: RISK_COLORS[risk.wind] }}>
                {risk.wind}
              </td>
            </tr>
            <tr>
              <td className="py-1 text-slate-400">Rain</td>
              <td className="py-1 font-mono text-slate-200">{formatMeasurement(weather.rain_in_per_hr, 'in/hr', 2)}</td>
              <td className="py-1 text-right font-semibold" style={{ color: RISK_COLORS[risk.rain] }}>
                {risk.rain}
              </td>
            </tr>
            <tr>
              <td className="py-1 text-slate-400">Snow</td>
              <td className="py-1 font-mono text-slate-200">{formatMeasurement(weather.snow_in_per_hr, 'in/hr', 2)}</td>
              <td className="py-1 text-right font-semibold" style={{ color: RISK_COLORS[risk.snow] }}>
                {risk.snow}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Warnings & Explanations */}
      {checkpoint.reasons.length > 0 && (
        <div className="space-y-1 rounded bg-slate-800/60 p-1.5 text-[10px] text-slate-300">
          <span className="font-semibold uppercase tracking-wider text-slate-400">Risk Triggers:</span>
          {checkpoint.reasons.map((r, i) => (
            <p key={i} className="leading-snug text-slate-300">
              • {r}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
