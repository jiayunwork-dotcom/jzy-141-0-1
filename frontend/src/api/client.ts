import type {
  BacktestOptions,
  BacktestResult,
  FitOptions,
  FitResult,
  Job,
  Point,
  SeriesRecord,
} from '../types';

const API = '/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    } catch {
      // keep status text
    }
    throw new Error(detail);
  }
  return response.json();
}

export function listSeries(): Promise<SeriesRecord[]> {
  return request<SeriesRecord[]>('/series');
}

export function createSeries(name: string, points: Point[]): Promise<SeriesRecord> {
  return request<SeriesRecord>('/series', {
    method: 'POST',
    body: JSON.stringify({ name, points }),
  });
}

export function getSeries(id: string): Promise<SeriesRecord> {
  return request<SeriesRecord>(`/series/${id}`);
}

export function startFit(seriesId: string, options: FitOptions): Promise<Job<FitResult>> {
  const { fixedParams, ...rest } = options;
  const fixed_params = Object.fromEntries(Object.entries(fixedParams).filter(([, v]) => Number.isFinite(v)));
  return request<Job<FitResult>>(`/series/${seriesId}/fit`, {
    method: 'POST',
    body: JSON.stringify({ ...rest, fixed_params }),
  });
}

export function startBacktest(seriesId: string, options: BacktestOptions): Promise<Job<BacktestResult>> {
  return request<Job<BacktestResult>>(`/series/${seriesId}/backtest`, {
    method: 'POST',
    body: JSON.stringify(options),
  });
}

export function getFitJob(jobId: string): Promise<Job<FitResult>> {
  return request<Job<FitResult>>(`/jobs/fit/${jobId}`);
}

export function getBacktestJob(jobId: string): Promise<Job<BacktestResult>> {
  return request<Job<BacktestResult>>(`/jobs/backtest/${jobId}`);
}

export function listRuns(seriesId: string): Promise<{ fits: Array<Job<FitResult>>; backtests: Array<Job<BacktestResult>> }> {
  return request(`/series/${seriesId}/runs`);
}
