import { useEffect, useState } from 'react';
import { listRuns } from '../api/client';
import type { FitResult, Job } from '../types';

interface Props {
  seriesId: string;
  refreshSignal: number;
  onLoad: (result: FitResult) => void;
}

export function RunHistory({ seriesId, refreshSignal, onLoad }: Props) {
  const [runs, setRuns] = useState<Array<Job<FitResult>>>([]);

  useEffect(() => {
    listRuns(seriesId)
      .then((data) => setRuns(data.fits))
      .catch(() => setRuns([]));
  }, [seriesId, refreshSignal]);

  const succeeded = runs.filter((r) => r.status === 'succeeded' && r.result);

  return (
    <section className="panel wide-panel">
      <h2>历史拟合（保留并可相互比较）</h2>
      {succeeded.length === 0 ? (
        <p className="muted">尚无成功拟合。</p>
      ) : (
        <table>
          <thead>
            <tr><th>时间</th><th>最优模型</th><th>AIC</th><th>SSE</th><th>操作</th></tr>
          </thead>
          <tbody>
            {succeeded.map((run) => (
              <tr key={run.job_id}>
                <td>{run.created_at}</td>
                <td>{run.result?.best.model.name}</td>
                <td>{run.result?.best.aic.toFixed(3)}</td>
                <td>{run.result?.best.sse.toFixed(3)}</td>
                <td><button onClick={() => run.result && onLoad(run.result)}>载入比较</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
