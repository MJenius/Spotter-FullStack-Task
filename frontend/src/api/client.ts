import { config } from '../config';
import type { ApiErrorBody, HealthResponse, RouteAnalysisRequest, RouteAnalysisResponse } from './types';

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
    public readonly details?: Record<string, string[]>,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${config.apiBaseUrl}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError('NETWORK_ERROR', 'Cannot reach the backend API.', 0);
  }
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok) {
    const err = (body as ApiErrorBody | null)?.error;
    throw new ApiError(
      err?.code ?? 'HTTP_ERROR',
      err?.message ?? `Request failed (HTTP ${res.status}).`,
      res.status,
      err?.details,
    );
  }
  return body as T;
}

export const api = {
  health: () => request<HealthResponse>('/api/health/'),
  analyzeRoutes: (payload: RouteAnalysisRequest, signal?: AbortSignal) =>
    request<RouteAnalysisResponse>('/api/v1/route-analysis/', {
      method: 'POST',
      body: JSON.stringify(payload),
      signal,
    }),
};
