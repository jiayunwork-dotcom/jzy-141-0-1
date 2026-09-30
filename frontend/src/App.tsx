import { useCallback, useEffect, useState } from 'react';
import { listSeries } from './api/client';
import { BacktestPage } from './components/BacktestPage';
import { FitPage } from './components/FitPage';
import { SeriesList } from './components/SeriesList';
import type { SeriesRecord } from './types';

type Tab = 'fit' | 'backtest';

export default function App() {
  const [series, setSeries] = useState<SeriesRecord[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('fit');
  const [loadError, setLoadError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const rows = await listSeries();
      setSeries(rows);
      setSelectedId((current) => current ?? rows[0]?.id ?? null);
      setLoadError(null);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const selected = series.find((s) => s.id === selectedId) ?? null;

  return (
    <div className="app-shell">
      <header>
        <div>
          <h1>周销量 Holt–Winters 补货预测</h1>
          <p>加法/乘法季节、趋势与阻尼自动选型；所有数字由后端拟合与回测得到。</p>
        </div>
        <nav>
          <button className={tab === 'fit' ? 'active' : ''} onClick={() => setTab('fit')}>拟合预测</button>
          <button className={tab === 'backtest' ? 'active' : ''} onClick={() => setTab('backtest')}>滚动回测</button>
        </nav>
      </header>
      {loadError && <div className="banner-error">后端连接失败：{loadError}</div>}
      <main className="layout">
        <SeriesList series={series} selectedId={selectedId} onSelect={setSelectedId} onRefresh={() => void refresh()} />
        <section className="content">
          {!selected && <div className="empty">请先上传或选择一条周销量序列。</div>}
          {selected && tab === 'fit' && <FitPage key={selected.id} series={selected} />}
          {selected && tab === 'backtest' && <BacktestPage key={selected.id} series={selected} />}
        </section>
      </main>
    </div>
  );
}
