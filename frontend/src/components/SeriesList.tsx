import { useState } from 'react';
import { parseWeeklyCsv } from '../utils/csv';
import { createSeries, listSeries } from '../api/client';
import type { SeriesRecord } from '../types';

interface Props {
  series: SeriesRecord[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onRefresh: () => void;
}

export function SeriesList({ series, selectedId, onSelect, onRefresh }: Props) {
  const [name, setName] = useState('');
  const [errors, setErrors] = useState<string[]>([]);
  const [points, setPoints] = useState<{ date: string; value: number }[]>([]);
  const [saving, setSaving] = useState(false);

  async function handleFile(file: File) {
    const text = await file.text();
    const parsed = parseWeeklyCsv(text);
    setErrors(parsed.errors);
    setPoints(parsed.points);
    if (!name) setName(file.name.replace(/\.csv$/i, ''));
  }

  async function save() {
    if (!points.length || errors.some((e) => e.includes('缺少') || e.includes('不是'))) return;
    setSaving(true);
    try {
      const created = await createSeries(name || '未命名序列', points);
      onRefresh();
      onSelect(created.id);
      setPoints([]);
      setErrors([]);
    } catch (e) {
      setErrors([e instanceof Error ? e.message : String(e)]);
    } finally {
      setSaving(false);
    }
  }

  return (
    <aside className="sidebar">
      <h2>周销量序列</h2>
      <div className="series-list">
        {series.map((s) => (
          <button
            key={s.id}
            className={s.id === selectedId ? 'series-item active' : 'series-item'}
            onClick={() => onSelect(s.id)}
          >
            <strong>{s.name}</strong>
            <span>{s.dates.length} 周 · {s.dates[0]} 起</span>
          </button>
        ))}
        {series.length === 0 && <p className="muted">还没有序列，请上传 CSV。</p>}
      </div>

      <div className="upload-box">
        <h3>上传 CSV</h3>
        <p className="muted">两列：周起始日期、销量，例如 2026-01-05,1234</p>
        <input value={name} placeholder="序列名称" onChange={(e) => setName(e.target.value)} />
        <input type="file" accept=".csv,text/csv" onChange={(e) => void handleFile(e.target.files?.[0] as File)} />
        {points.length > 0 && <p>已解析 {points.length} 行；{points[0].date} 至 {points[points.length - 1].date}</p>}
        {errors.length > 0 && (
          <ul className="errors">{errors.map((e, i) => <li key={`${e}-${i}`}>{e}</li>)}</ul>
        )}
        <button className="primary" disabled={saving || points.length === 0} onClick={() => void save()}>
          {saving ? '保存中…' : '保存序列'}
        </button>
      </div>
    </aside>
  );
}
