export interface Point {
  date: string;
  value: number;
}

export interface SeriesRecord {
  id: string;
  name: string;
  dates: string[];
  values: number[];
  period: string;
  created_at: string;
}

export interface ModelDescription {
  seasonal: 'additive' | 'multiplicative';
  trend: 'none' | 'additive';
  damped: boolean;
  name: string;
}

export interface Parameters {
  alpha: number;
  beta: number | null;
  gamma: number;
  phi: number | null;
}

export interface ForecastPayload {
  point: number[];
  lower: number[];
  upper: number[];
  half_width: number[];
}

export interface FitPayload {
  model: ModelDescription;
  parameters: Parameters;
  sse: number;
  aic: number;
  fitted: number[];
  residuals: number[];
  final_state: {
    level: number;
    trend: number;
    seasonal: number[];
    next_season_index: number;
  };
  forecast: ForecastPayload | null;
}

export interface Candidate {
  ok: boolean;
  result?: FitPayload;
  model?: ModelDescription;
  error?: string;
}

export interface FitResult {
  best: FitPayload;
  candidates: Candidate[];
}

export type JobStatus = 'pending' | 'running' | 'succeeded' | 'failed';

export interface Job<T> {
  job_id: string;
  status: JobStatus;
  progress: number;
  message: string;
  error?: string | null;
  result?: T | null;
  created_at?: string;
}

export interface MetricBlock {
  mae: number;
  mape: number | null;
  mase: number | null;
  per_origin_mae: number[];
  per_horizon: Array<{ horizon: number; mae: number; mape: number | null }>;
}

export interface OriginBacktest {
  origin: number;
  model_name: string;
  actual: number[];
  forecast: number[];
  naive_forecast: number[];
  errors: number[];
  naive_errors: number[];
  mae: number;
  mape: number | null;
  mase: number | null;
  naive_mae: number;
  naive_mape: number | null;
  naive_mase: number | null;
}

export interface BacktestResult {
  m: number;
  h: number;
  origins: OriginBacktest[];
  summary: {
    holt_winters: MetricBlock;
    seasonal_naive: MetricBlock;
    origin_count: number;
    mae_improvement_pct: number | null;
  };
}

export interface FitOptions {
  m: number;
  horizon: number;
  confidence: number;
  auto: boolean;
  seasonal: 'additive' | 'multiplicative';
  trend: 'none' | 'additive';
  damped: boolean;
  fixedParams: Record<string, number>;
}

export interface BacktestOptions {
  m: number;
  h: number;
  start_index?: number;
  step: number;
  origins?: number;
  confidence: number;
  auto: boolean;
  seasonal: 'additive' | 'multiplicative';
  trend: 'none' | 'additive';
  damped: boolean;
}
