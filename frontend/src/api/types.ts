/** Typed contract for /api/v1/route-analysis/ — mirrors docs/PROJECT_SPEC.md §9. */

export type RiskLevel = 'Low' | 'Moderate' | 'High' | 'Severe' | 'No Travel' | 'Unknown';
export type CheckpointInterval = 10 | 25 | 50;
export type LatLngTuple = [number, number];

export interface RouteAnalysisRequest {
  origin: string;
  destination: string;
  /** ISO-8601 with explicit UTC offset. */
  departure_time: string;
  load_weight_lbs: number;
  checkpoint_interval_miles: CheckpointInterval;
  forecast_offset_hours: number;
}

export interface CheckpointWeather {
  wind_mph: number | null;
  rain_in_per_hr: number | null;
  snow_in_per_hr: number | null;
  forecast_time: string | null;
}

export interface Checkpoint {
  index: number;
  lat: number;
  lon: number;
  distance_miles: number;
  interval_start_miles: number;
  interval_end_miles: number;
  represented_miles: number;
  eta: string;
  weather: CheckpointWeather;
  forecast_available: boolean;
  risk: { wind: RiskLevel; rain: RiskLevel; snow: RiskLevel; overall: RiskLevel };
  reasons: string[];
}

export interface RouteSegment {
  start_miles: number;
  end_miles: number;
  risk: RiskLevel;
  coordinates: LatLngTuple[];
}

export interface RouteMetrics {
  severe_miles: number;
  high_miles: number;
  moderate_miles: number;
  low_miles: number;
  no_travel_miles: number;
  unknown_miles: number;
  average_risk: number | null;
  duration_seconds: number;
}

export interface AnalyzedRoute {
  id: string;
  label: string;
  description: string;
  distance_miles: number;
  duration_seconds: number;
  polyline: LatLngTuple[];
  checkpoints: Checkpoint[];
  segments: RouteSegment[];
  metrics: RouteMetrics;
  eligible: boolean;
  weather_incomplete: boolean;
  unsafe_reasons: string[];
}

export type RecommendationStatus = 'RECOMMENDED' | 'NO_SAFE_ROUTE' | 'NO_ROUTES';

export interface Recommendation {
  status: RecommendationStatus;
  route_id: string | null;
  deciding_criterion: string | null;
  explanation: string;
}

export interface ApiWarning {
  code: string;
  message: string;
}

export interface RouteAnalysisResponse {
  request: RouteAnalysisRequest;
  effective_departure_time: string;
  routes: AnalyzedRoute[];
  recommendation: Recommendation;
  warnings: ApiWarning[];
  attribution: { routing: string; weather: string };
}

export interface HealthResponse {
  status: 'ok';
  service: string;
  version: string;
  providers: { routing_configured: boolean; weather_base_url: string };
}

export interface ApiErrorBody {
  error: { code: string; message: string; details?: Record<string, string[]> };
}
