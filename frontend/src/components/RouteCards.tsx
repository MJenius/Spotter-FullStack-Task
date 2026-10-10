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

  const isNoSafeRoute = recommendation?.status === 'NO_SAFE_ROUTE';

  return (
    <div className="space-y-3" role="region" aria-label="Route comparison options">
      {isNoSafeRoute && (
        <div
          role="alert"
          className="rounded-lg border border-purple-500/80 bg-purple-950/70 p-3 text-xs leading-relaxed text-purple-200 shadow-md"
        >
          <div className="mb-1 flex items-center gap-1.5 font-bold uppercase tracking-wider text-purple-300">
            <span>🚫 No Safe Route Available</span>
          </div>
          <p>{recommendation.explanation}</p>
        </div>
      )}

      {routes.map((r, index) => {
        const isRecommended = recommendation?.status === 'RECOMMENDED' && recommendation.route_id === r.id;
        const isSelected = selectedId === r.id;

        return (
          <button
            key={r.id}
            type="button"
            onClick={() => onSelect(r.id)}
            aria-pressed={isSelected}
            className={`w-full rounded-lg border p-3.5 text-left transition focus:outline-none focus:ring-2 focus:ring-sky-400 ${
              isSelected
                ? 'border-sky-400 bg-slate-800 shadow-lg ring-1 ring-sky-400/50'
                : 'border-slate-700/80 bg-slate-900/90 hover:border-slate-500 hover:bg-slate-850'
            }`}
          >
            {/* Header: Title and Badges */}
            <div className="flex flex-wrap items-center justify-between gap-1.5 border-b border-slate-750 pb-2">
              <div className="flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-700 text-[10px] font-bold text-slate-200">
                  {index + 1}
                </span>
                <span className="text-sm font-bold text-slate-100">{r.description || r.label}</span>
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                {isRecommended && (
                  <span className="inline-flex items-center gap-1 rounded bg-emerald-500 px-2 py-0.5 text-[11px] font-extrabold text-slate-950 shadow-sm">
                    ★ Recommended
                  </span>
                )}
                {!r.eligible ? (
                  <span className="rounded border border-purple-500/60 bg-purple-900/80 px-2 py-0.5 text-[11px] font-bold text-purple-200">
                    Unsafe (No Travel)
                  </span>
                ) : (
                  <span className="rounded border border-emerald-700/50 bg-emerald-950/40 px-1.5 py-0.5 text-[10px] font-medium text-emerald-400">
                    Eligible
                  </span>
                )}
              </div>
            </div>

            {/* Core Distance and Travel Time */}
            <div className="mt-2.5 flex items-baseline justify-between text-xs text-slate-300">
              <div>
                <span className="font-semibold text-white">{r.distance_miles.toFixed(1)} mi</span>
                <span className="mx-1.5 text-slate-600">·</span>
                <span className="font-semibold text-slate-200">{formatDuration(r.duration_seconds)}</span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400">Avg Risk: </span>
                <span className="font-mono font-semibold text-slate-200">
                  {r.metrics.average_risk != null ? `${r.metrics.average_risk.toFixed(2)}/3.00` : 'N/A'}
                </span>
              </div>
            </div>

            {/* Risk Distribution Breakdown */}
            <dl className="mt-2.5 grid grid-cols-4 gap-1 rounded bg-slate-950/50 p-2 text-center text-[10px]">
              <div className="rounded bg-slate-900/60 p-1">
                <dt className="text-red-400 font-medium">Severe</dt>
                <dd className="mt-0.5 font-bold font-mono text-slate-100">{r.metrics.severe_miles.toFixed(1)} mi</dd>
              </div>
              <div className="rounded bg-slate-900/60 p-1">
                <dt className="text-orange-400 font-medium">High</dt>
                <dd className="mt-0.5 font-bold font-mono text-slate-100">{r.metrics.high_miles.toFixed(1)} mi</dd>
              </div>
              <div className="rounded bg-slate-900/60 p-1">
                <dt className="text-yellow-400 font-medium">Moderate</dt>
                <dd className="mt-0.5 font-bold font-mono text-slate-100">{r.metrics.moderate_miles.toFixed(1)} mi</dd>
              </div>
              <div className="rounded bg-slate-900/60 p-1">
                <dt className="text-emerald-400 font-medium">Low</dt>
                <dd className="mt-0.5 font-bold font-mono text-slate-100">{r.metrics.low_miles.toFixed(1)} mi</dd>
              </div>
            </dl>

            {/* Incomplete Weather or No Travel Notices */}
            {r.metrics.no_travel_miles > 0 && (
              <div className="mt-2 text-[11px] font-medium text-purple-300">
                ⚠️ Contains {r.metrics.no_travel_miles.toFixed(1)} mi of No Travel conditions.
              </div>
            )}
            {r.weather_incomplete && (
              <div className="mt-1.5 flex items-center gap-1 text-[11px] font-medium text-amber-300">
                <span>⚠️ Missing weather forecast for {r.metrics.unknown_miles.toFixed(1)} mi (unverified).</span>
              </div>
            )}

            {/* Recommendation basis or Unsafe Reasons */}
            {isRecommended && recommendation?.explanation && (
              <div className="mt-2 rounded bg-emerald-950/50 border border-emerald-800/40 p-2 text-[11px] text-emerald-200">
                <span className="font-semibold uppercase tracking-wider text-emerald-400">Why recommended:</span>{' '}
                {recommendation.explanation}
              </div>
            )}
            {!r.eligible && r.unsafe_reasons.length > 0 && (
              <div className="mt-2 rounded bg-purple-950/40 border border-purple-800/40 p-2 text-[11px] text-purple-200">
                <span className="font-semibold uppercase tracking-wider text-purple-400">Hazard reason:</span>{' '}
                {r.unsafe_reasons[0]}
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}
