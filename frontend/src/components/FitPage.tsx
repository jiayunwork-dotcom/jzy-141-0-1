import { useEffect, useRef, useState } from 'react';
import { getFitJob, startFit } from '../api/client';
import type { FitOptions, FitResult, SeriesRecord } from '../types';
import { usePolledJob } from '../hooks/usePolledJob';
import { CandidateScores } from './CandidateScores';
import { FitStats } from './FitStats';
import { ForecastChart } from './ForecastChart';
import { ParameterPanel } from './ParameterPanel';
import { ProgressBar } from './ProgressBar';
import { RunHistory } from './RunHistory';

export function FitPage({ series }: { series: SeriesRecord }) {
  const defaultM = Math.min(52, Math.max(2, Math.floor(series.values.length / 2)));
  const [options, setOptions] = useState<FitOptions>({
    m: defaultM,
    horizon: 8,
    confidence: 0.95,
    auto: true,
    seasonal: 'additive',
    trend: 'additive',
    damped: false,
    fixedParams: {},
  });
  const [jobId, setJobId] = useState<string | null>(null);
  const { job, error } = usePolledJob<FitResult>(jobId, getFitJob);
  const [historical, setHistorical] = useState<FitResult | null>(null);
  const result = job?.result ?? historical;
  const firstRun = useRef(true);

  async function submit(next = options) {
    setHistorical(null);
    const started = await startFit(series.id, next);
    setJobId(started.job_id);
  }

  useEffect(() => {
    if (firstRun.current) {
      firstRun.current = false;
      void submit(options);
    }
    // Run once per selected series.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [series.id]);

  // Manual locked-value edits trigger a short debounce, giving the requested
  // immediate backend recomputation without firing on every keystroke.
  useEffect(() => {
    if (options.auto || Object.keys(options.fixedParams).length === 0) return undefined;
    const handle = window.setTimeout(() => void submit(options), 450);
    return () => window.clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options.fixedParams, options.seasonal, options.trend, options.damped]);

  return (
    <div className="page-grid">
      <ParameterPanel
        options={options}
        onChange={setOptions}
        onSubmit={() => void submit()}
        busy={job?.status === 'running' || job?.status === 'pending'}
        best={result?.best ?? null}
      />
      <FitStats fit={result?.best ?? null} />
      <section className="panel chart-panel">
        <ProgressBar job={job} />
        {error && <p className="error-text">{error}</p>}
        <ForecastChart series={series} fit={result?.best ?? null} />
      </section>
      <CandidateScores result={result} />
      <RunHistory seriesId={series.id} refreshSignal={job?.progress ?? 0} onLoad={setHistorical} />
    </div>
  );
}
