import type { RiskLevel } from '../api/types';

/** Presentation only (colours/labels). Classification rules live in the backend — see spec §5. */
export const RISK_LEVELS: RiskLevel[] = ['Low', 'Moderate', 'High', 'Severe', 'No Travel', 'Unknown'];

export const RISK_COLORS: Record<RiskLevel, string> = {
  Low: '#22c55e',
  Moderate: '#eab308',
  High: '#f97316',
  Severe: '#dc2626',
  'No Travel': '#7e22ce',
  Unknown: '#94a3b8',
};

export const RISK_BADGE_CLASSES: Record<RiskLevel, string> = {
  Low: 'bg-emerald-950/80 text-emerald-300 border-emerald-700/60',
  Moderate: 'bg-yellow-950/80 text-yellow-300 border-yellow-700/60',
  High: 'bg-orange-950/80 text-orange-300 border-orange-700/60',
  Severe: 'bg-red-950/80 text-red-300 border-red-700/60',
  'No Travel': 'bg-purple-950/80 text-purple-300 border-purple-700/60',
  Unknown: 'bg-slate-800 text-slate-300 border-slate-600/60',
};

export function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return h > 0 ? `${h} h ${m} min` : `${m} min`;
}

export function formatMeasurement(v: number | null, unit: string, digits = 1): string {
  if (v == null || !Number.isFinite(v)) return 'Unavailable';
  return `${v.toFixed(digits)} ${unit}`;
}
