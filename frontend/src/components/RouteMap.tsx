import { Fragment } from 'react';
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer } from 'react-leaflet';
import type { AnalyzedRoute } from '../api/types';
import { config } from '../config';
import { RISK_COLORS } from '../lib/risk';
import { CheckpointDetails } from './CheckpointDetails';
import { RiskLegend } from './RiskLegend';

interface Props {
  routes: AnalyzedRoute[];
  selectedId: string | null;
}

const US_CENTER: [number, number] = [39.5, -98.35];

/**
 * Map is driven solely by normalised API data. The corridor intensity overlay is rendered as
 * risk-coloured translucent circles at checkpoints (swap for leaflet.heat in milestone 5 if preferred).
 */
export function RouteMap({ routes, selectedId }: Props) {
  const ordered = [...routes].sort((a, b) => Number(a.id === selectedId) - Number(b.id === selectedId));
  return (
    <div className="relative h-full min-h-[420px] w-full overflow-hidden rounded-lg border border-slate-700">
      <MapContainer center={US_CENTER} zoom={4} className="h-full w-full" scrollWheelZoom>
        <TileLayer url={config.tileUrl} attribution={config.tileAttribution} />
        {ordered.map((route) => {
          const selected = route.id === selectedId;
          return (
            <Fragment key={route.id}>
              {route.segments.map((s, i) => (
                <Polyline
                  key={`${route.id}-seg-${i}`}
                  positions={s.coordinates}
                  pathOptions={{ color: RISK_COLORS[s.risk], weight: selected ? 7 : 4, opacity: selected ? 1 : 0.45 }}
                />
              ))}
              {selected &&
                route.checkpoints.map((c) => (
                  <CircleMarker
                    key={`${route.id}-heat-${c.index}`}
                    center={[c.lat, c.lon]}
                    radius={22}
                    pathOptions={{ stroke: false, fillColor: RISK_COLORS[c.risk.overall], fillOpacity: 0.18 }}
                  />
                ))}
              {selected &&
                route.checkpoints.map((c) => (
                  <CircleMarker
                    key={`${route.id}-cp-${c.index}`}
                    center={[c.lat, c.lon]}
                    radius={6}
                    pathOptions={{
                      color: '#0f172a',
                      weight: 2,
                      fillColor: RISK_COLORS[c.risk.overall],
                      fillOpacity: 1,
                    }}
                  >
                    <Popup>
                      <CheckpointDetails checkpoint={c} />
                    </Popup>
                  </CircleMarker>
                ))}
            </Fragment>
          );
        })}
      </MapContainer>
      <div className="pointer-events-none absolute bottom-6 left-3 z-[1000]">
        <RiskLegend />
      </div>
    </div>
  );
}
