import { useState } from 'react';
import type { BacktestOptions, SeriesRecord } from '../types';
import { getBacktestJob, startBacktest } from '../api/client';
import { usePolledJob } from '../hooks/usePolledJob';
import { ProgressBar } from './ProgressBar';

interface Props {
  series: SeriesRecord;
}

export function BacktestPage({ series }: Props) {
  const defaultM = Math.min(52, Math.max(2, Math.floor(series.values.length / 2)));
  const [options, setOptions] = useState<BacktestOptions>({
    m: defaultM,
    h: 8,
    step: 1,
    origins: 8,
    confidence: 0.95,
    auto: true,
    seasonal: 'additive',
    trend: 'additive',
    damped: false,
  });
  const [jobId, setJobId] = useState<string | null>(null);
  const { job, error } = usePolledJob(jobId, getBacktestJob);
  const result = job?.result ?? null;

  async function run() {
    const started = await startBacktest(series.id, options);
    setJobId(started.job_id);
  }

  return (
    <div className="page-grid">
      <section className="panel">
        <h2>滚动原点回测</h2>
        <div className="form-grid">
          <label>季节周期<input type="number" value={options.m} onChange={(e) => setOptions({ ...options, m: Number(e.target.value) })} /></label>
          <label>预测步长 h<input type="number" value={options.h} onChange={(e) => setOptions({ ...options, h: Number(e.target.value) })} /></label>
          <label>原点数量上限<input type="number" value={options.origins ?? ''} onChange={(e) => setOptions({ ...options, origins: e.target.value ? Number(e.target.value) : undefined })} /></label>
          <label>原点间隔<input type="number" value={options.step} onChange={(e) => setOptions({ ...options, step: Number(e.target.value) })} /></label>
          <label>季节项
            <select value={options.seasonal} disabled={options.auto} onChange={(e) => setOptions({ ...options, seasonal: e.target.value as BacktestOptions['seasonal'] })}>
              <option value="additive">加法</option>
              <option value="multiplicative">乘法</option>
            </select>
          </label>
          <label>趋势
            <select value={options.trend} disabled={options.auto} onChange={(e) => setOptions({ ...options, trend: e.target.value as BacktestOptions['trend'] })}>
              <option value="none">无趋势</option>
              <option value="additive">加法趋势</option>
            </select>
          </label>
          <label className="checkbox"><input type="checkbox" disabled={options.auto || options.trend === 'none'} checked={options.damped} onChange={(e) => setOptions({ ...options, damped: e.target.checked })} />阻尼趋势</label>
        </div>
        <label className="checkbox wide"><input type="checkbox" checked={options.auto} onChange={(e) => setOptions({ ...options, auto: e.target.checked })} />每个原点自动按 AIC 选型</label>
        <p className="muted">每个原点仅用截至当时的数据重新拟合；基准为「照抄上一个季节」的季节朴素法。</p>
        <button className="primary" onClick={() => void run()}>启动后台回测</button>
        {error && <p className="error-text">{error}</p>}
        <ProgressBar job={job} />
      </section>

      {result && (
        <section className="panel">
          <h2>指标汇总</h2>
          <table>
            <thead><tr><th>方法</th><th>MAE</th><th>MAPE</th><th>MASE</th></tr></thead>
            <tbody>
              <tr className="best-row"><td>Holt-Winters</td><td>{result.summary.holt_winters.mae.toFixed(3)}</td><td>{fmt(result.summary.holt_winters.mape)}</td><td>{fmt(result.summary.holt_winters.mase)}</td></tr>
              <tr><td>季节朴素法</td><td>{result.summary.seasonal_naive.mae.toFixed(3)}</td><td>{fmt(result.summary.seasonal_naive.mape)}</td><td>{fmt(result.summary.seasonal_naive.mase)}</td></tr>
            </tbody>
          </table>
          <p>MAE 改善：{result.summary.mae_improvement_pct === null ? '—' : `${result.summary.mae_improvement_pct.toFixed(2)}%`}</p>
        </section>
      )}

      {result && (
        <section className="panel wide-panel">
          <h2>每个原点的误差</h2>
          <table>
            <thead>
              <tr><th>原点</th><th>模型</th><th>HW MAE</th><th>朴素 MAE</th><th>HW MAPE</th><th>朴素 MAPE</th><th>HW MASE</th><th>朴素 MASE</th></tr>
            </thead>
            <tbody>
              {result.origins.map((o) => (
                <tr key={o.origin}>
                  <td>{o.origin}（{series.dates[o.origin]}）</td>
                  <td>{o.model_name}</td>
                  <td>{o.mae.toFixed(3)}</td><td>{o.naive_mae.toFixed(3)}</td>
                  <td>{fmt(o.mape)}</td><td>{fmt(o.naive_mape)}</td>
                  <td>{fmt(o.mase)}</td><td>{fmt(o.naive_mase)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}

function fmt(v: number | null | undefined) {
  return v === null || v === undefined ? '—' : `${v.toFixed(3)}`;
}
