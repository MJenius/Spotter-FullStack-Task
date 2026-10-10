import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from '../App';
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
