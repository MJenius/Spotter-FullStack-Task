import { Fragment, useEffect } from 'react';
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, Tooltip, useMap } from 'react-leaflet';
import type { LatLngBoundsExpression } from 'leaflet';
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
 * Automatically fits map viewport to encompass all route alternatives when the route set changes.
 */
function MapBoundsController({ routes }: { routes: AnalyzedRoute[] }) {
  const map = useMap();

  useEffect(() => {
    // Invalidate map size so Leaflet recalculates tile grid dimensions on mount and resize
    map.invalidateSize();
    const handleResize = () => {
      map.invalidateSize();
    };
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [map]);

  useEffect(() => {
    map.invalidateSize();
    if (!routes.length) return;

    let minLat = 90;
    let maxLat = -90;
    let minLon = 180;
    let maxLon = -180;
    let hasCoords = false;

    for (const r of routes) {
      for (const [lat, lon] of r.polyline) {
        if (lat < minLat) minLat = lat;
        if (lat > maxLat) maxLat = lat;
        if (lon < minLon) minLon = lon;
        if (lon > maxLon) maxLon = lon;
        hasCoords = true;
      }
    }

    if (hasCoords) {
      const bounds: LatLngBoundsExpression = [
        [minLat, minLon],
        [maxLat, maxLon],
      ];
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 12, animate: true });
    }
  }, [map, routes]);

  return null;
}

export function RouteMap({ routes, selectedId }: Props) {
  // Sort so unselected routes render underneath, selected route on top
  const ordered = [...routes].sort((a, b) => Number(a.id === selectedId) - Number(b.id === selectedId));
  const activeRoute = routes.find((r) => r.id === selectedId) ?? routes[0];

  const originCoord = activeRoute?.polyline[0];
  const destCoord = activeRoute?.polyline[activeRoute.polyline.length - 1];

  return (
    <div className="relative h-full min-h-[440px] w-full overflow-hidden rounded-lg border border-slate-700 bg-slate-950 shadow-inner">
      <MapContainer center={US_CENTER} zoom={4} className="h-full w-full" scrollWheelZoom>
        <TileLayer url={config.tileUrl} attribution={config.tileAttribution} />
        <MapBoundsController routes={routes} />

        {ordered.map((route) => {
          const isSelected = route.id === selectedId;

          return (
            <Fragment key={route.id}>
              {/* Route Segments */}
              {route.segments.map((s, i) => (
                <Polyline
                  key={`${route.id}-seg-${i}`}
                  positions={s.coordinates}
                  pathOptions={{
                    color: RISK_COLORS[s.risk],
                    weight: isSelected ? 6 : 3,
                    opacity: isSelected ? 0.95 : 0.35,
                    lineJoin: 'round',
                    lineCap: 'round',
                  }}
                >
                  <Tooltip sticky>
                    <span className="text-xs font-semibold">
                      {route.description || route.label} · {s.risk} Risk ({s.start_miles.toFixed(0)}–
                      {s.end_miles.toFixed(0)} mi)
                    </span>
                  </Tooltip>
                </Polyline>
              ))}

              {/* Corridor weather-risk circles (selected route only) */}
              {isSelected &&
                route.checkpoints.map((c) => (
                  <CircleMarker
                    key={`${route.id}-corridor-${c.index}`}
                    center={[c.lat, c.lon]}
                    radius={18}
                    pathOptions={{
                      stroke: false,
                      fillColor: RISK_COLORS[c.risk.overall],
                      fillOpacity: c.risk.overall === 'Unknown' ? 0.12 : 0.22,
                    }}
                  />
                ))}

              {/* Checkpoint markers with risk coloring & popups (selected route only) */}
              {isSelected &&
                route.checkpoints.map((c) => (
                  <CircleMarker
                    key={`${route.id}-cp-${c.index}`}
                    center={[c.lat, c.lon]}
                    radius={5.5}
                    pathOptions={{
                      color: '#0f172a',
                      weight: 2,
                      fillColor: RISK_COLORS[c.risk.overall],
                      fillOpacity: 1,
                    }}
                  >
                    <Popup maxWidth={300} minWidth={240} className="custom-leaflet-popup">
                      <CheckpointDetails checkpoint={c} />
                    </Popup>
                  </CircleMarker>
                ))}
            </Fragment>
          );
        })}

        {/* Origin Marker */}
        {originCoord && (
          <CircleMarker
            center={originCoord}
            radius={8}
            pathOptions={{
              color: '#ffffff',
              weight: 2.5,
              fillColor: '#38bdf8',
              fillOpacity: 1,
            }}
          >
            <Tooltip permanent direction="top" offset={[0, -10]}>
              <span className="font-bold text-xs text-sky-950">Origin</span>
            </Tooltip>
          </CircleMarker>
        )}

        {/* Destination Marker */}
        {destCoord && (
          <CircleMarker
            center={destCoord}
            radius={8}
            pathOptions={{
              color: '#ffffff',
              weight: 2.5,
              fillColor: '#10b981',
              fillOpacity: 1,
            }}
          >
            <Tooltip permanent direction="top" offset={[0, -10]}>
              <span className="font-bold text-xs text-emerald-950">Destination</span>
            </Tooltip>
          </CircleMarker>
        )}
      </MapContainer>

      {/* Floating Legend */}
      <div className="pointer-events-none absolute bottom-4 left-4 z-[1000]">
        <div className="pointer-events-auto">
          <RiskLegend />
        </div>
      </div>
    </div>
  );
}
