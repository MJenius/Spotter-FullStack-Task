import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, api } from './api/client';
import type { HealthResponse, RouteAnalysisRequest, RouteAnalysisResponse } from './api/types';
import { ForecastSlider } from './components/ForecastSlider';
import { RouteCards } from './components/RouteCards';
import { RouteMap } from './components/RouteMap';
import { StatusBanner } from './components/StatusBanner';
import { TripForm } from './components/TripForm';

type BaseRequest = Omit<RouteAnalysisRequest, 'forecast_offset_hours'>;
type Health = { state: 'checking' } | { state: 'ok'; data: HealthResponse } | { state: 'down'; message: string };

const SLIDER_DEBOUNCE_MS = 400;

export default function App() {
  const [health, setHealth] = useState<Health>({ state: 'checking' });
  const [baseRequest, setBaseRequest] = useState<BaseRequest | null>(null);
  const [offset, setOffset] = useState(0);
  const [result, setResult] = useState<RouteAnalysisResponse | null>(null);
  const [currentResultOffset, setCurrentResultOffset] = useState<number>(0);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const latestRequestedOffsetRef = useRef<number>(0);

  useEffect(() => {
    api
      .health()
      .then((data) => setHealth({ state: 'ok', data }))
      .catch((e: ApiError) => setHealth({ state: 'down', message: e.message }));
  }, []);

  const runAnalysis = useCallback(async (req: BaseRequest, hours: number) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    latestRequestedOffsetRef.current = hours;
    setLoading(true);
    setError(null);
    try {
      const res = await api.analyzeRoutes({ ...req, forecast_offset_hours: hours }, controller.signal);
      // Ensure stale response does not overwrite if another request was fired
      if (latestRequestedOffsetRef.current === hours) {
        setResult(res);
        setCurrentResultOffset(hours);
        setSelectedId((prev) =>
          res.routes.some((r) => r.id === prev) ? prev : (res.recommendation.route_id ?? res.routes[0]?.id ?? null),
        );
      }
    } catch (e) {
      if (controller.signal.aborted) return;
      // If recalculating a slider shift and it fails, don't clear old trip if it exists, but show error
      setError(e instanceof ApiError ? e : new ApiError('UNKNOWN', 'Unexpected error.', 0));
    } finally {
      if (!controller.signal.aborted && latestRequestedOffsetRef.current === hours) {
        setLoading(false);
      }
    }
  }, []);

  // Debounced re-analysis when the forecast slider moves (spec §8).
  useEffect(() => {
    if (!baseRequest || !result) return;
    const t = setTimeout(() => void runAnalysis(baseRequest, offset), SLIDER_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [baseRequest, offset, runAnalysis, result]);

  function handleSubmit(req: BaseRequest) {
    setBaseRequest(req);
    void runAnalysis(req, offset);
  }

  const routes = result?.routes ?? [];

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
      <header className="flex items-center justify-between border-b border-slate-800 px-6 py-3">
        <div>
          <h1 className="text-lg font-bold tracking-tight">
            <span className="text-sky-400">Storm</span>Route Dispatch
          </h1>
          <p className="text-xs text-slate-400">Weather- and load-aware truck route comparison</p>
        </div>
        <HealthBadge health={health} />
      </header>

      <main className="grid flex-1 gap-4 p-4 lg:grid-cols-[340px_1fr]">
        <aside className="space-y-4">
          <section className="rounded-lg border border-slate-700 bg-slate-900 p-4">
            <h2 className="mb-3 text-sm font-semibold text-slate-200">Trip details</h2>
            <TripForm onSubmit={handleSubmit} loading={loading} serverErrors={error?.details} />
          </section>
          <ForecastSlider value={offset} onChange={setOffset} disabled={!result} />
          <section>
            <h2 className="mb-2 text-sm font-semibold text-slate-200">Route comparison</h2>
            <RouteCards
              routes={routes}
              recommendation={result?.recommendation ?? null}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          </section>
        </aside>

        <section className="flex min-h-[480px] flex-col gap-3">
          <StatusBanner loading={loading} error={error} result={result} scenarioOffset={offset} />
          {result && currentResultOffset > 0 && !loading && (
            <div className="flex items-center justify-between rounded-md border border-sky-800/60 bg-sky-950/40 px-3 py-1.5 text-xs text-sky-200">
              <span>
                Viewing scenario shifted <strong>+{currentResultOffset} h</strong> from entered departure.
              </span>
              <span className="text-[11px] text-slate-400">
                Effective departure: {new Date(result.effective_departure_time).toLocaleString()}
              </span>
            </div>
          )}
          <div className="relative flex-1">
            <RouteMap routes={routes} selectedId={selectedId} />
          </div>
          <footer className="text-[11px] text-slate-500">
            Routing: Google Routes API · Weather data by{' '}
            <a className="underline" href="https://open-meteo.com/" target="_blank" rel="noreferrer">
              Open-Meteo.com
            </a>{' '}
            · Route geometry is provider-generated and not verified against truck restrictions.
          </footer>
        </section>
      </main>
    </div>
  );
}

function HealthBadge({ health }: { health: Health }) {
  if (health.state === 'checking') return <span className="text-xs text-slate-400">Checking backend…</span>;
  if (health.state === 'down')
    return (
      <span className="rounded-full bg-red-900/60 px-3 py-1 text-xs text-red-200" title={health.message}>
        Backend unreachable
      </span>
    );
  const configured = health.data.providers.routing_configured;
  return (
    <span
      className={`rounded-full px-3 py-1 text-xs ${configured ? 'bg-emerald-900/60 text-emerald-200' : 'bg-amber-900/60 text-amber-200'}`}
    >
      Backend online · routing {configured ? 'configured' : 'not configured'}
    </span>
  );
}
