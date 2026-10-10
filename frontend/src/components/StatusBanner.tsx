import type { ApiError } from '../api/client';
import type { RouteAnalysisResponse } from '../api/types';

interface Props {
  loading: boolean;
  error: ApiError | null;
  result: RouteAnalysisResponse | null;
  scenarioOffset?: number;
}

export function StatusBanner({ loading, error, result, scenarioOffset = 0 }: Props) {
  if (loading) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="flex items-center gap-2.5 rounded-lg border border-sky-700/80 bg-sky-950/70 px-4 py-2.5 text-sm text-sky-200 shadow"
      >
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-sky-300 border-t-transparent" />
        <span>
          {scenarioOffset > 0
            ? `Recalculating scenario (+${scenarioOffset}h shifted departure)…`
            : 'Analyzing routes, sampling geometry, and matching weather forecasts…'}
        </span>
      </div>
    );
  }

  if (error) {
    let help = '';
    if (error.code === 'ROUTING_NOT_CONFIGURED') {
      help = 'Backend requires GOOGLE_ROUTES_API_KEY to be configured in server environment.';
    } else if (error.code === 'UPSTREAM_TIMEOUT') {
      help = 'The routing or weather provider timed out. Try again in a moment.';
    } else if (error.code === 'UPSTREAM_RATE_LIMITED') {
      help = 'Provider rate limit encountered. Wait briefly before requesting again.';
    } else if (error.code === 'VALIDATION_ERROR') {
      help = 'Please check the entered origin, destination, load weight, and interval values.';
    }

    return (
      <div
        role="alert"
        aria-live="assertive"
        className="rounded-lg border border-red-800 bg-red-950/80 px-4 py-3 text-sm text-red-200 shadow"
      >
        <div className="flex items-center gap-2 font-bold">
          <span className="rounded bg-red-900/90 px-1.5 py-0.5 text-xs text-red-100">{error.code}</span>
          <span>{error.message}</span>
        </div>
        {help && <p className="mt-1 text-xs text-red-300/90">{help}</p>}
      </div>
    );
  }

  if (!result) {
    return (
      <div className="rounded-lg border border-slate-700/80 bg-slate-900/80 px-4 py-2.5 text-xs text-slate-300 shadow">
        Enter a trip to compare up to three routes by weather risk, load, and travel time.
      </div>
    );
  }

  if (result.routes.length === 0) {
    return (
      <div
        role="status"
        className="rounded-lg border border-amber-800/80 bg-amber-950/70 px-4 py-2.5 text-sm text-amber-200"
      >
        <strong>No routes found.</strong> The routing provider returned zero traversable driving routes for this origin
        and destination.
      </div>
    );
  }

  if (!result.warnings || result.warnings.length === 0) {
    return null;
  }

  return (
    <div className="space-y-1.5" role="region" aria-label="Route analysis notices">
      {result.warnings.map((w) => {
        const isWeatherNotice = w.code.includes('WEATHER') || w.code.includes('FORECAST');
        const isFewerRoutes = w.code === 'FEWER_THAN_THREE_ROUTES';

        return (
          <div
            key={w.code}
            className={`flex items-start gap-2 rounded-lg border px-3.5 py-2 text-xs leading-relaxed shadow-sm ${
              isWeatherNotice
                ? 'border-amber-700/80 bg-amber-950/70 text-amber-200'
                : isFewerRoutes
                  ? 'border-sky-800/80 bg-sky-950/60 text-sky-200'
                  : 'border-slate-700 bg-slate-900 text-slate-300'
            }`}
          >
            <span className="mt-0.5 text-sm">{isWeatherNotice ? '⚠️' : 'ℹ️'}</span>
            <div>
              <span className="font-semibold uppercase tracking-wider">{w.code}: </span>
              {w.message}
            </div>
          </div>
        );
      })}
    </div>
  );
}
