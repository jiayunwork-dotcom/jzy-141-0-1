import type { FitPayload } from '../types';

export function FitStats({ fit }: { fit: FitPayload | null }) {
  if (!fit) return null;
  const p = fit.parameters;
  return (
    <section className="panel stats">
      <h2>拟合结果</h2>
      <div><span>模型</span><strong>{fit.model.name}</strong></div>
      <div><span>SSE</span><strong>{fit.sse.toFixed(4)}</strong></div>
      <div><span>AIC</span><strong>{fit.aic.toFixed(4)}</strong></div>
      <div><span>α</span><strong>{p.alpha.toFixed(4)}</strong></div>
      <div><span>β</span><strong>{p.beta === null ? '—' : p.beta.toFixed(4)}</strong></div>
      <div><span>γ</span><strong>{p.gamma.toFixed(4)}</strong></div>
      <div><span>φ</span><strong>{p.phi === null ? '—' : p.phi.toFixed(4)}</strong></div>
      <div><span>最终水平</span><strong>{fit.final_state.level.toFixed(4)}</strong></div>
      <div><span>最终趋势</span><strong>{fit.final_state.trend.toFixed(4)}</strong></div>
    </section>
  );
}
