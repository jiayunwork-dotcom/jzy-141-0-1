import { describe, expect, it } from 'vitest';
import { findMissingWeeks, parseWeeklyCsv } from './csv';

describe('parseWeeklyCsv', () => {
  it('parses a two-column weekly CSV with Chinese header', () => {
    const csv = ['日期,销量', '2026-01-05,12', '2026-01-12,14.5'].join('\n');
    const parsed = parseWeeklyCsv(csv);
    expect(parsed.errors).toEqual([]);
    expect(parsed.points).toEqual([
      { date: '2026-01-05', value: 12 },
      { date: '2026-01-12', value: 14.5 },
    ]);
  });

  it('reports malformed values', () => {
    const csv = ['date,value', '2026-01-05,12', 'not-a-date,14', '2026-01-19,oops'].join('\n');
    const parsed = parseWeeklyCsv(csv);
    expect(parsed.errors.join(' ')).toContain('日期无法识别');
    expect(parsed.errors.join(' ')).toContain('销量不是数字');
  });

  it('deduplicates repeated dates', () => {
    const csv = ['date,value', '2026-01-05,12', '2026-01-05,18', '2026-01-12,20'].join('\n');
    const parsed = parseWeeklyCsv(csv);
    expect(parsed.errors.join(' ')).toContain('日期重复');
    expect(parsed.points).toHaveLength(2);
  });
});

describe('findMissingWeeks', () => {
  it('returns no error for consecutive Mondays', () => {
    expect(findMissingWeeks(['2026-01-05', '2026-01-12', '2026-01-19'])).toEqual([]);
  });

  it('names every missing week-start date', () => {
    const errors = findMissingWeeks(['2026-01-05', '2026-01-26']);
    expect(errors).toEqual(['缺少周起始日：2026-01-12', '缺少周起始日：2026-01-19']);
  });

  it('detects reversed dates', () => {
    expect(findMissingWeeks(['2026-01-12', '2026-01-05'])[0]).toContain('不是严格递增');
  });
});
