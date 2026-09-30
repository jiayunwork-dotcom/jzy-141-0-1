import type { FitResult } from '../types';

export function CandidateScores({ result }: { result: FitResult | null }) {
  if (!result) return null;
  const rows = result.candidates
    .map((c) => (c.ok && c.result ? c.result : null))
    .filter((x): x is NonNullable<typeof x> => x !== null)
    .sort((a, b) => a.aic - b.aic);

  return (
    <section className="panel">
      <h2>自动选型得分（AIC 越小越优）</h2>
      <table>
        <thead>
          <tr><th>模型</th><th>季节</th><th>趋势</th><th>阻尼</th><th>SSE</th><th>AIC</th></tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.model.name} className={r.model.name === result.best.model.name ? 'best-row' : ''}>
              <td>{r.model.name}</td>
              <td>{r.model.seasonal}</td>
              <td>{r.model.trend}</td>
              <td>{r.model.damped ? '是' : '否'}</td>
              <td>{r.sse.toFixed(3)}</td>
              <td>{r.aic.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
