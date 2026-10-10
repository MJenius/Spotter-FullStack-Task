import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from '../App';
import type { Checkpoint } from '../api/types';
import { RiskLegend } from '../components/RiskLegend';
import { toOffsetIso } from '../lib/dateUtils';

function mockFetch(handler: (url: string, init?: RequestInit) => Response) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => Promise.resolve(handler(url, init))),
  );
}
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

afterEach(() => vi.unstubAllGlobals());

describe('App shell', () => {
  it('renders empty state and backend health honestly', async () => {
    mockFetch(() =>
      json({
        status: 'ok',
        service: 's',
        version: 'v1',
        providers: { routing_configured: false, weather_base_url: '' },
      }),
    );
    render(<App />);
    expect(screen.getByText(/Enter a trip to compare/i)).toBeInTheDocument();
    expect(screen.getByText(/Route comparisons will appear here/i)).toBeInTheDocument();
    expect(await screen.findByText(/routing not configured/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Forecast scenario/i)).toBeDisabled();
  });

  it('shows backend unreachable when health fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('net'))),
    );
    render(<App />);
    expect(await screen.findByText(/Backend unreachable/i)).toBeInTheDocument();
  });

  it('validates required fields before calling the API', async () => {
    mockFetch(() =>
      json({
        status: 'ok',
        service: 's',
        version: 'v1',
        providers: { routing_configured: true, weather_base_url: '' },
      }),
    );
    render(<App />);
    await userEvent.click(screen.getByRole('button', { name: /Analyze routes/i }));
    expect(screen.getByText('Origin is required.')).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1); // health only
  });

  it('surfaces structured API errors', async () => {
    mockFetch((url) =>
      url.includes('route-analysis')
        ? json({ error: { code: 'NOT_IMPLEMENTED', message: 'Route analysis is not implemented yet.' } }, 501)
        : json({
            status: 'ok',
            service: 's',
            version: 'v1',
            providers: { routing_configured: true, weather_base_url: '' },
          }),
    );
    render(<App />);
    await userEvent.type(screen.getByLabelText('Origin'), 'Chicago, IL');
    await userEvent.type(screen.getByLabelText('Destination'), 'Denver, CO');
    await userEvent.click(screen.getByRole('button', { name: /Analyze routes/i }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('NOT_IMPLEMENTED'));
  });
});

describe('RiskLegend', () => {
  it('lists every category including Unknown', () => {
    render(<RiskLegend />);
    for (const r of ['Low', 'Moderate', 'High', 'Severe', 'No Travel', 'Unknown']) {
      expect(screen.getByText(r)).toBeInTheDocument();
    }
  });
});

describe('toOffsetIso', () => {
  it('appends an explicit UTC offset', () => {
    expect(toOffsetIso('2026-10-11T08:00')).toMatch(/^2026-10-11T08:00:00[+-]\d{2}:\d{2}$/);
  });
});

describe('Route Comparison & Interaction Experience', () => {
  const MOCK_CHECKPOINT: Checkpoint = {
    index: 0,
    lat: 41.8781,
    lon: -87.6298,
    distance_miles: 0,
    interval_start_miles: 0,
    interval_end_miles: 12.5,
    represented_miles: 12.5,
    eta: '2026-10-11T13:00:00Z',
    weather: {
      wind_mph: 15.0,
      rain_in_per_hr: 0.05,
      snow_in_per_hr: 0.0,
      forecast_time: '2026-10-11T13:00:00Z',
    },
    forecast_available: true,
    risk: { wind: 'Low', rain: 'Low', snow: 'Low', overall: 'Low' },
    reasons: [],
  };

  const MOCK_ROUTE_1 = {
    id: 'route-0',
    label: 'DEFAULT_ROUTE',
    description: 'Route via I-80 W',
    distance_miles: 1000.5,
    duration_seconds: 54000,
    polyline: [
      [41.8781, -87.6298],
      [39.7392, -104.9903],
    ],
    checkpoints: [MOCK_CHECKPOINT],
    segments: [
      {
        start_miles: 0,
        end_miles: 12.5,
        risk: 'Low',
        coordinates: [
          [41.8781, -87.6298],
          [41.5, -88.0],
        ],
      },
    ],
    metrics: {
      severe_miles: 0,
      high_miles: 15.0,
      moderate_miles: 50.0,
      low_miles: 935.5,
      no_travel_miles: 0,
      unknown_miles: 0,
      average_risk: 0.25,
      duration_seconds: 54000,
    },
    eligible: true,
    weather_incomplete: false,
    unsafe_reasons: [],
  };

  const MOCK_ROUTE_2 = {
    ...MOCK_ROUTE_1,
    id: 'route-1',
    description: 'Route via I-70 W',
    metrics: {
      ...MOCK_ROUTE_1.metrics,
      severe_miles: 45.0,
      average_risk: 0.75,
    },
  };

  const MOCK_SUCCESS_RESPONSE = {
    request: {
      origin: 'Chicago, IL',
      destination: 'Denver, CO',
      departure_time: '2026-10-11T08:00:00-05:00',
      load_weight_lbs: 35000,
      checkpoint_interval_miles: 25,
      forecast_offset_hours: 0,
    },
    effective_departure_time: '2026-10-11T13:00:00Z',
    routes: [MOCK_ROUTE_1, MOCK_ROUTE_2],
    recommendation: {
      status: 'RECOMMENDED',
      route_id: 'route-0',
      deciding_criterion: 'FEWEST_SEVERE_MILES',
      explanation: 'Route 1 has the fewest Severe weather miles (0.0 mi vs 45.0 mi).',
    },
    warnings: [{ code: 'FEWER_THAN_THREE_ROUTES', message: 'Only 2 routes were returned by the routing provider.' }],
    attribution: { routing: 'Google Routes API', weather: 'Open-Meteo.com' },
  };

  it('renders multiple route alternatives, recommendation badge, and warnings', async () => {
    mockFetch((url) =>
      url.includes('route-analysis')
        ? json(MOCK_SUCCESS_RESPONSE)
        : json({
            status: 'ok',
            service: 's',
            version: 'v1',
            providers: { routing_configured: true, weather_base_url: '' },
          }),
    );
    render(<App />);

    await userEvent.type(screen.getByLabelText('Origin'), 'Chicago, IL');
    await userEvent.type(screen.getByLabelText('Destination'), 'Denver, CO');
    await userEvent.click(screen.getByRole('button', { name: /Analyze routes/i }));

    expect(await screen.findByText('Route via I-80 W')).toBeInTheDocument();
    expect(screen.getByText('Route via I-70 W')).toBeInTheDocument();
    expect(screen.getByText('★ Recommended')).toBeInTheDocument();
    expect(screen.getByText(/Route 1 has the fewest Severe weather miles/i)).toBeInTheDocument();
    expect(screen.getByText(/Only 2 routes were returned/i)).toBeInTheDocument();
  });

  it('displays NO_SAFE_ROUTE alert without recommended badge when all routes are unsafe', async () => {
    const unsafeResponse = {
      ...MOCK_SUCCESS_RESPONSE,
      routes: [
        {
          ...MOCK_ROUTE_1,
          eligible: false,
          unsafe_reasons: ['Wind 58.0 mph exceeds 55 mph threshold -> No Travel'],
          metrics: { ...MOCK_ROUTE_1.metrics, no_travel_miles: 25.0 },
        },
      ],
      recommendation: {
        status: 'NO_SAFE_ROUTE',
        route_id: null,
        deciding_criterion: null,
        explanation: 'All routes contain No Travel conditions.',
      },
    };

    mockFetch((url) =>
      url.includes('route-analysis')
        ? json(unsafeResponse)
        : json({
            status: 'ok',
            service: 's',
            version: 'v1',
            providers: { routing_configured: true, weather_base_url: '' },
          }),
    );
    render(<App />);

    await userEvent.type(screen.getByLabelText('Origin'), 'Chicago, IL');
    await userEvent.type(screen.getByLabelText('Destination'), 'Denver, CO');
    await userEvent.click(screen.getByRole('button', { name: /Analyze routes/i }));

    expect(await screen.findByText(/No Safe Route Available/i)).toBeInTheDocument();
    expect(screen.queryByText('★ Recommended')).not.toBeInTheDocument();
    expect(screen.getByText(/Unsafe \(No Travel\)/i)).toBeInTheDocument();
  });

  it('renders weather incomplete warning honestly for unverified routes', async () => {
    const incompleteResponse = {
      ...MOCK_SUCCESS_RESPONSE,
      routes: [
        {
          ...MOCK_ROUTE_1,
          weather_incomplete: true,
          metrics: { ...MOCK_ROUTE_1.metrics, unknown_miles: 75.0 },
        },
      ],
      warnings: [{ code: 'FORECAST_INCOMPLETE', message: 'One or more checkpoints lack complete forecast data.' }],
    };

    mockFetch((url) =>
      url.includes('route-analysis')
        ? json(incompleteResponse)
        : json({
            status: 'ok',
            service: 's',
            version: 'v1',
            providers: { routing_configured: true, weather_base_url: '' },
          }),
    );
    render(<App />);

    await userEvent.type(screen.getByLabelText('Origin'), 'Chicago, IL');
    await userEvent.type(screen.getByLabelText('Destination'), 'Denver, CO');
    await userEvent.click(screen.getByRole('button', { name: /Analyze routes/i }));

    expect(await screen.findByText(/Missing weather forecast for 75.0 mi/i)).toBeInTheDocument();
    expect(screen.getByText(/One or more checkpoints lack complete forecast data/i)).toBeInTheDocument();
  });

  it('allows clicking alternative route card to select it', async () => {
    mockFetch((url) =>
      url.includes('route-analysis')
        ? json(MOCK_SUCCESS_RESPONSE)
        : json({
            status: 'ok',
            service: 's',
            version: 'v1',
            providers: { routing_configured: true, weather_base_url: '' },
          }),
    );
    render(<App />);

    await userEvent.type(screen.getByLabelText('Origin'), 'Chicago, IL');
    await userEvent.type(screen.getByLabelText('Destination'), 'Denver, CO');
    await userEvent.click(screen.getByRole('button', { name: /Analyze routes/i }));

    const altRouteButton = await screen.findByRole('button', { name: /Route via I-70 W/i });
    expect(altRouteButton).toHaveAttribute('aria-pressed', 'false');

    await userEvent.click(altRouteButton);
    expect(altRouteButton).toHaveAttribute('aria-pressed', 'true');
  });

  it('renders CheckpointDetails with complete weather measurements and risk tags', async () => {
    const { CheckpointDetails } = await import('../components/CheckpointDetails');
    render(<CheckpointDetails checkpoint={MOCK_CHECKPOINT} />);

    expect(screen.getByText(/Checkpoint #0/i)).toBeInTheDocument();
    expect(screen.getByText(/15.0 mph/i)).toBeInTheDocument();
    expect(screen.getByText(/0.05 in\/hr/i)).toBeInTheDocument();
    expect(screen.getByText(/0.00 in\/hr/i)).toBeInTheDocument();
    expect(screen.getAllByText('Low').length).toBeGreaterThan(0);
  });

  it('renders CheckpointDetails correctly for all 6 risk levels including Unknown and No Travel', async () => {
    const { CheckpointDetails } = await import('../components/CheckpointDetails');
    const levels: Array<'Low' | 'Moderate' | 'High' | 'Severe' | 'No Travel' | 'Unknown'> = [
      'Low',
      'Moderate',
      'High',
      'Severe',
      'No Travel',
      'Unknown',
    ];

    for (const level of levels) {
      const cp: Checkpoint = {
        ...MOCK_CHECKPOINT,
        risk: { wind: level, rain: level, snow: level, overall: level },
        forecast_available: level !== 'Unknown',
        weather: {
          wind_mph: level === 'Unknown' ? null : 20.0,
          rain_in_per_hr: level === 'Unknown' ? null : 0.1,
          snow_in_per_hr: level === 'Unknown' ? null : 0.0,
          forecast_time: level === 'Unknown' ? null : '2026-10-11T13:00:00Z',
        },
      };
      const { unmount } = render(<CheckpointDetails checkpoint={cp} />);
      expect(screen.getAllByText(level).length).toBeGreaterThan(0);
      if (level === 'Unknown') {
        expect(screen.getByText(/Forecast unavailable for this checkpoint ETA/i)).toBeInTheDocument();
        expect(screen.getAllByText('Unavailable').length).toBeGreaterThanOrEqual(3);
      }
      unmount();
    }
  });

  it('triggers debounced re-analysis when forecast slider is adjusted', async () => {
    const { fireEvent } = await import('@testing-library/react');
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('route-analysis')) {
        const body = JSON.parse(init?.body as string);
        const offset = body.forecast_offset_hours || 0;
        return Promise.resolve(
          json({
            ...MOCK_SUCCESS_RESPONSE,
            request: { ...MOCK_SUCCESS_RESPONSE.request, forecast_offset_hours: offset },
            effective_departure_time: `2026-10-12T${String(offset).padStart(2, '0')}:00:00Z`,
          }),
        );
      }
      return Promise.resolve(
        json({
          status: 'ok',
          service: 's',
          version: 'v1',
          providers: { routing_configured: true, weather_base_url: '' },
        }),
      );
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<App />);
    await userEvent.type(screen.getByLabelText('Origin'), 'Chicago, IL');
    await userEvent.type(screen.getByLabelText('Destination'), 'Denver, CO');
    await userEvent.click(screen.getByRole('button', { name: /Analyze routes/i }));

    const slider = await screen.findByLabelText(/Forecast scenario/i);
    expect(slider).not.toBeDisabled();

    // Change slider value to 12
    fireEvent.change(slider, { target: { value: '12' } });

    await waitFor(
      () => {
        expect(fetchMock).toHaveBeenCalledWith(
          expect.stringContaining('/api/v1/route-analysis/'),
          expect.objectContaining({
            body: expect.stringMatching(/"forecast_offset_hours":12/),
          }),
        );
      },
      { timeout: 3000 },
    );
  });
});
