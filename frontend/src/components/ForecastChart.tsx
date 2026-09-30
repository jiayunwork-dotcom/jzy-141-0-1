import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { FitPayload, SeriesRecord } from '../types';

interface Props {
  series: SeriesRecord;
  fit: FitPayload | null;
}

function addWeeks(isoDate: string, weeks: number): string {
  const d = new Date(`${isoDate}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 7 * weeks);
  return d.toISOString().slice(0, 10);
}

export function ForecastChart({ series, fit }: Props) {
  const data = series.dates.map((date, i) => ({
    date,
    actual: series.values[i],
    fitted: fit?.fitted[i] ?? null,
  }));
  const horizon = fit?.forecast?.point.length ?? 0;
  const forecast = fit?.forecast;
  if (horizon > 0) {
    data[series.dates.length - 1] = {
      ...data[series.dates.length - 1],
      forecast: fit?.fitted[series.dates.length - 1] ?? null,
      lower: forecast?.lower[0] ?? null,
      upper: forecast?.upper[0] ?? null,
    } as never;
  }
  for (let h = 0; h < horizon; h += 1) {
    data.push({
      date: addWeeks(series.dates[series.dates.length - 1], h + 1),
      actual: null,
      fitted: null,
      forecast: forecast?.point[h] ?? null,
      lower: forecast?.lower[h] ?? null,
      upper: forecast?.upper[h] ?? null,
    } as never);
  }

  return (
    <div className="chart-card">
      <h2>原始值、拟合值与预测区间</h2>
      <ResponsiveContainer width="100%" height={430}>
        <LineChart data={data} margin={{ top: 12, right: 24, bottom: 12, left: 8 }}>
          <CartesianGrid stroke="#e7eaf0" />
          <XAxis dataKey="date" minTickGap={48} />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="actual" name="实际销量" stroke="#27364a" dot={false} strokeWidth={2} />
          <Line type="monotone" dataKey="fitted" name="历史拟合" stroke="#2f80ed" dot={false} />
          <Line type="monotone" dataKey="forecast" name="预测" stroke="#eb5757" dot={false} strokeWidth={2} />
          <Line type="monotone" dataKey="upper" name="区间上界" stroke="#9aa5b1" dot={false} strokeDasharray="4 4" />
          <Line type="monotone" dataKey="lower" name="区间下界" stroke="#9aa5b1" dot={false} strokeDasharray="4 4" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
