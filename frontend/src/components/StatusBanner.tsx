import type { ApiError } from '../api/client';
import type { RouteAnalysisResponse } from '../api/types';

interface Props {
  loading: boolean;
  error: ApiError | null;
  result: RouteAnalysisResponse | null;
}

export function StatusBanner({ loading, error, result }: Props) {
  if (loading)
    return (
      <div
        role="status"
        className="flex items-center gap-2 rounded-lg border border-sky-800 bg-sky-950/60 px-4 py-2 text-sm text-sky-200"
      >
        <span className="h-3 w-3 animate-spin rounded-full border-2 border-sky-300 border-t-transparent" />
        Fetching routes and forecasts…
      </div>
    );
  if (error)
    return (
      <div role="alert" className="rounded-lg border border-red-800 bg-red-950/60 px-4 py-2 text-sm text-red-200">
        <strong className="mr-2">{error.code}</strong>
        {error.message}
      </div>
    );
  if (!result)
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-400">
        Enter a trip to compare up to three routes by weather risk, load, and travel time.
      </div>
    );
  const forecastWarnings = result.warnings.filter((w) => w.code.startsWith('FORECAST'));
  return (
    <div className="space-y-2">
      {result.warnings.map((w) => (
        <div
          key={w.code}
          className={`rounded-lg border px-4 py-2 text-sm ${
            forecastWarnings.includes(w)
              ? 'border-amber-700 bg-amber-950/60 text-amber-200'
              : 'border-slate-700 bg-slate-900 text-slate-300'
          }`}
        >
          {w.message}
        </div>
      ))}
    </div>
  );
}
