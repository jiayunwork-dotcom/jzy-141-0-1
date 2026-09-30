import { useMemo } from 'react';
import type { FitOptions, FitPayload } from '../types';

interface Props {
  options: FitOptions;
  onChange: (next: FitOptions) => void;
  onSubmit: () => void;
  busy: boolean;
  best: FitPayload | null;
}

export function ParameterPanel({ options, onChange, onSubmit, busy, best }: Props) {
  const lockable = useMemo(
    () => [
      { key: 'alpha', label: 'α 水平平滑', disabled: false },
      { key: 'beta', label: 'β 趋势平滑', disabled: options.trend === 'none' },
      { key: 'gamma', label: 'γ 季节平滑', disabled: false },
      { key: 'phi', label: 'φ 阻尼系数', disabled: !options.damped },
    ] as const,
    [options.trend, options.damped],
  );

  function update<K extends keyof FitOptions>(key: K, value: FitOptions[K]) {
    onChange({ ...options, [key]: value });
  }

  function toggleLock(key: string, checked: boolean) {
    const current = best?.parameters[key as keyof typeof best.parameters];
    const fixed = { ...options.fixedParams };
    if (checked && typeof current === 'number') fixed[key] = current;
    else delete fixed[key];
    onChange({ ...options, fixedParams: fixed });
  }

  return (
    <section className="panel">
      <h2>模型与参数</h2>
      <div className="form-grid">
        <label>
          季节周期（周）
          <input type="number" min={2} value={options.m} onChange={(e) => update('m', Number(e.target.value))} />
        </label>
        <label>
          预测期数
          <input type="number" min={1} max={52} value={options.horizon} onChange={(e) => update('horizon', Number(e.target.value))} />
        </label>
        <label>
          置信水平
          <input type="number" min={0.5} max={0.999} step={0.01} value={options.confidence} onChange={(e) => update('confidence', Number(e.target.value))} />
        </label>
        <label>
          季节项
          <select value={options.seasonal} onChange={(e) => update('seasonal', e.target.value as FitOptions['seasonal'])} disabled={options.auto}>
            <option value="additive">加法</option>
            <option value="multiplicative">乘法</option>
          </select>
        </label>
        <label>
          趋势
          <select value={options.trend} onChange={(e) => update('trend', e.target.value as FitOptions['trend'])} disabled={options.auto}>
            <option value="none">无趋势</option>
            <option value="additive">加法趋势</option>
          </select>
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={options.damped}
            disabled={options.auto || options.trend === 'none'}
            onChange={(e) => update('damped', e.target.checked)}
          />
          阻尼趋势
        </label>
      </div>

      <label className="checkbox wide">
        <input type="checkbox" checked={options.auto} onChange={(e) => update('auto', e.target.checked)} />
        自动按 AIC 在 6 种加法/乘法 × 无趋势/趋势/阻尼趋势组合中选型
      </label>

      <table className="param-table">
        <thead>
          <tr><th>参数</th><th>锁定</th><th>手动值</th><th>当前最优</th></tr>
        </thead>
        <tbody>
          {lockable.map((p) => (
            <tr key={p.key}>
              <td>{p.label}</td>
              <td>
                <input
                  type="checkbox"
                  disabled={p.disabled || options.auto || best === null}
                  checked={p.key in options.fixedParams}
                  onChange={(e) => toggleLock(p.key, e.target.checked)}
                />
              </td>
              <td>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.01}
                  disabled={p.disabled || !(p.key in options.fixedParams)}
                  value={options.fixedParams[p.key] ?? ''}
                  onChange={(e) => update('fixedParams', { ...options.fixedParams, [p.key]: Number(e.target.value) })}
                />
              </td>
              <td>{best?.parameters[p.key as 'alpha'] ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <button className="primary" disabled={busy} onClick={onSubmit}>
        {busy ? '后台计算中…' : '拟合 / 重新拟合'}
      </button>
    </section>
  );
}
