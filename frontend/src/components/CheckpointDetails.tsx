import type { Checkpoint } from '../api/types';
import { RISK_COLORS } from '../lib/risk';

const fmt = (v: number | null, unit: string, digits = 2) => (v == null ? '—' : `${v.toFixed(digits)} ${unit}`);

export function CheckpointDetails({ checkpoint }: { checkpoint: Checkpoint }) {
  const { risk, weather } = checkpoint;
  return (
    <div className="min-w-48 space-y-1 text-xs">
      <div className="flex items-center gap-2">
        <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: RISK_COLORS[risk.overall] }} />
        <strong>{risk.overall}</strong>
        <span className="text-slate-500">at mile {checkpoint.distance_miles.toFixed(1)}</span>
      </div>
      <p>ETA: {new Date(checkpoint.eta).toLocaleString()}</p>
      {!checkpoint.forecast_available && <p className="text-amber-600">Forecast unavailable for this time.</p>}
      <table>
        <tbody>
          <tr>
            <td className="pr-2">Wind</td>
            <td>{fmt(weather.wind_mph, 'mph', 1)}</td>
            <td className="pl-2">{risk.wind}</td>
          </tr>
          <tr>
            <td className="pr-2">Rain</td>
            <td>{fmt(weather.rain_in_per_hr, 'in/hr')}</td>
            <td className="pl-2">{risk.rain}</td>
          </tr>
          <tr>
            <td className="pr-2">Snow</td>
            <td>{fmt(weather.snow_in_per_hr, 'in/hr')}</td>
            <td className="pl-2">{risk.snow}</td>
          </tr>
        </tbody>
      </table>
      {checkpoint.reasons.map((r) => (
        <p key={r} className="text-slate-600">
          • {r}
        </p>
      ))}
    </div>
  );
}
