import type { AnalyzedRoute, Recommendation } from '../api/types';
import { formatDuration } from '../lib/risk';

interface Props {
  routes: AnalyzedRoute[];
  recommendation: Recommendation | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function RouteCards({ routes, recommendation, selectedId, onSelect }: Props) {
  if (!routes.length) {
    return (
      <div className="rounded-lg border border-dashed border-slate-700 p-6 text-center text-sm text-slate-400">
        Route comparisons will appear here after an analysis.
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {recommendation?.status === 'NO_SAFE_ROUTE' && (
        <div role="alert" className="rounded-lg border border-purple-500 bg-purple-950/60 p-3 text-sm text-purple-100">
          No safe route found. {recommendation.explanation}
        </div>
      )}
      {routes.map((r) => {
        const recommended = recommendation?.route_id === r.id;
        return (
          <button
            key={r.id}
            type="button"
            onClick={() => onSelect(r.id)}
            className={`w-full rounded-lg border p-3 text-left transition ${
              selectedId === r.id
                ? 'border-sky-400 bg-slate-800'
                : 'border-slate-700 bg-slate-900 hover:border-slate-500'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-100">{r.description || r.label}</span>
              {recommended && (
                <span className="rounded bg-emerald-500 px-2 py-0.5 text-xs font-bold text-slate-950">Recommended</span>
              )}
              {!r.eligible && (
                <span className="rounded bg-purple-600 px-2 py-0.5 text-xs font-bold text-white">Unsafe</span>
              )}
            </div>
            <dl className="mt-2 grid grid-cols-4 gap-2 text-xs text-slate-300">
              <div>
                <dt className="text-slate-500">Distance</dt>
                <dd>{r.distance_miles.toFixed(0)} mi</dd>
              </div>
              <div>
                <dt className="text-slate-500">Time</dt>
                <dd>{formatDuration(r.duration_seconds)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Severe</dt>
                <dd>{r.metrics.severe_miles.toFixed(1)} mi</dd>
              </div>
              <div>
                <dt className="text-slate-500">High</dt>
                <dd>{r.metrics.high_miles.toFixed(1)} mi</dd>
              </div>
            </dl>
            {r.weather_incomplete && (
              <p className="mt-2 text-xs text-amber-300">
                Forecast unavailable for {r.metrics.unknown_miles.toFixed(0)} mi — not fully verified.
              </p>
            )}
            {recommended && recommendation?.explanation && (
              <p className="mt-2 text-xs text-emerald-300">{recommendation.explanation}</p>
            )}
          </button>
        );
      })}
    </div>
  );
}
