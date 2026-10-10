import { useState, type FormEvent } from 'react';
import type { CheckpointInterval, RouteAnalysisRequest } from '../api/types';
import { toOffsetIso } from '../lib/dateUtils';

interface Props {
  onSubmit: (req: Omit<RouteAnalysisRequest, 'forecast_offset_hours'>) => void;
  loading: boolean;
  serverErrors?: Record<string, string[]>;
}

type Errors = Partial<Record<string, string>>;

function defaultDeparture(): string {
  const d = new Date(Date.now() + 60 * 60 * 1000);
  d.setMinutes(0, 0, 0);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:00`;
}

const inputCls =
  'w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-sky-400 focus:outline-none focus:ring-1 focus:ring-sky-400';

export function TripForm({ onSubmit, loading, serverErrors }: Props) {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [departure, setDeparture] = useState(defaultDeparture);
  const [load, setLoad] = useState('35000');
  const [interval, setInterval] = useState<CheckpointInterval>(25);
  const [errors, setErrors] = useState<Errors>({});

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const next: Errors = {};
    if (!origin.trim()) next.origin = 'Origin is required.';
    if (!destination.trim()) next.destination = 'Destination is required.';
    if (origin.trim() && origin.trim().toLowerCase() === destination.trim().toLowerCase())
      next.destination = 'Destination must differ from origin.';
    if (!departure || Number.isNaN(new Date(departure).getTime())) next.departure_time = 'Enter a valid departure.';
    const loadNum = Number(load);
    if (!Number.isFinite(loadNum) || loadNum <= 0 || loadNum > 200000)
      next.load_weight_lbs = 'Enter a load between 1 and 200,000 lb.';
    setErrors(next);
    if (Object.keys(next).length) return;
    onSubmit({
      origin: origin.trim(),
      destination: destination.trim(),
      departure_time: toOffsetIso(departure),
      load_weight_lbs: loadNum,
      checkpoint_interval_miles: interval,
    });
  }

  const err = (k: string) => errors[k] ?? serverErrors?.[k]?.[0];

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4" aria-label="Trip details">
      {(
        [
          ['origin', 'Origin', origin, setOrigin, 'e.g. Chicago, IL'],
          ['destination', 'Destination', destination, setDestination, 'e.g. Denver, CO'],
        ] as const
      ).map(([key, label, value, set, ph]) => (
        <div key={key}>
          <label htmlFor={key} className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">
            {label}
          </label>
          <input
            id={key}
            className={inputCls}
            value={value}
            placeholder={ph}
            onChange={(e) => set(e.target.value)}
            aria-invalid={!!err(key)}
          />
          {err(key) && <p className="mt-1 text-xs text-red-400">{err(key)}</p>}
        </div>
      ))}
      <div>
        <label htmlFor="departure" className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">
          Departure (local time)
        </label>
        <input
          id="departure"
          type="datetime-local"
          className={inputCls}
          value={departure}
          onChange={(e) => setDeparture(e.target.value)}
        />
        {err('departure_time') && <p className="mt-1 text-xs text-red-400">{err('departure_time')}</p>}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="load" className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">
            Load (lb)
          </label>
          <input
            id="load"
            type="number"
            min={1}
            step={100}
            className={inputCls}
            value={load}
            onChange={(e) => setLoad(e.target.value)}
            aria-invalid={!!err('load_weight_lbs')}
          />
        </div>
        <div>
          <label htmlFor="interval" className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">
            Sample every
          </label>
          <select
            id="interval"
            className={inputCls}
            value={interval}
            onChange={(e) => setInterval(Number(e.target.value) as CheckpointInterval)}
          >
            <option value={10}>10 miles</option>
            <option value={25}>25 miles</option>
            <option value={50}>50 miles</option>
          </select>
        </div>
      </div>
      {err('load_weight_lbs') && <p className="-mt-2 text-xs text-red-400">{err('load_weight_lbs')}</p>}
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-md bg-sky-500 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:cursor-wait disabled:opacity-60"
      >
        {loading ? 'Analyzing routes…' : 'Analyze routes'}
      </button>
    </form>
  );
}
