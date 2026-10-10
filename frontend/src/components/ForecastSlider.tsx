interface Props {
  value: number;
  onChange: (hours: number) => void;
  disabled?: boolean;
}

export function ForecastSlider({ value, onChange, disabled }: Props) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
      <div className="mb-2 flex items-baseline justify-between">
        <label htmlFor="forecast-offset" className="text-xs font-medium uppercase tracking-wide text-slate-400">
          Forecast scenario
        </label>
        <span className="text-sm font-semibold text-sky-300" aria-live="polite">
          {value === 0 ? 'Departure as entered' : `Departure shifted +${value} h (scenario)`}
        </span>
      </div>
      <input
        id="forecast-offset"
        type="range"
        min={0}
        max={48}
        step={1}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-sky-400 disabled:opacity-40"
      />
      <div className="mt-1 flex justify-between text-[10px] text-slate-500">
        <span>0 h</span>
        <span>12 h</span>
        <span>24 h</span>
        <span>36 h</span>
        <span>48 h</span>
      </div>
      {disabled && <p className="mt-2 text-xs text-slate-500">Run an analysis to explore shifted departures.</p>}
    </div>
  );
}
