import type { Point } from '../types';

export interface ParseResult {
  points: Point[];
  errors: string[];
}

const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

export function parseWeeklyCsv(text: string): ParseResult {
  const errors: string[] = [];
  const lines = text.replace(/^﻿/, '').split(/\r?\n/).filter((line) => line.trim().length > 0);
  if (lines.length < 2) {
    return { points: [], errors: ['CSV 至少需要表头和一行数据'] };
  }

  const points: Point[] = [];
  lines.forEach((line, index) => {
    const columns = splitCsvLine(line);
    if (columns.length !== 2) {
      errors.push(`第 ${index + 1} 行必须恰好是两列，实际为 ${columns.length} 列`);
      return;
    }
    const rawDate = columns[0].trim();
    const rawValue = columns[1].trim();
    if (index === 0 && /date|日期|周/i.test(rawDate)) {
      return;
    }
    const parsedDate = parseDate(rawDate);
    const value = Number(rawValue);
    if (!parsedDate) {
      errors.push(`第 ${index + 1} 行日期无法识别：${rawDate}`);
      return;
    }
    if (!Number.isFinite(value)) {
      errors.push(`第 ${index + 1} 行销量不是数字：${rawValue}`);
      return;
    }
    points.push({ date: toISODate(parsedDate), value });
  });

  points.sort((a, b) => a.date.localeCompare(b.date));
  const seen = new Set<string>();
  for (const point of points) {
    if (seen.has(point.date)) {
      errors.push(`日期重复：${point.date}`);
    }
    seen.add(point.date);
  }
  errors.push(...findMissingWeeks(points.map((p) => p.date)));
  return { points: dedupeByDate(points), errors };
}

export function findMissingWeeks(dates: string[]): string[] {
  const missing: string[] = [];
  for (let i = 1; i < dates.length; i += 1) {
    const prev = parseDate(dates[i - 1]);
    const current = parseDate(dates[i]);
    if (!prev || !current) continue;
    const diffWeeks = Math.round((current.getTime() - prev.getTime()) / WEEK_MS);
    if (diffWeeks > 1) {
      for (let k = 1; k < diffWeeks; k += 1) {
        const missingDate = new Date(prev.getTime() + k * WEEK_MS);
        missing.push(`缺少周起始日：${toISODate(missingDate)}`);
      }
    } else if (diffWeeks <= 0) {
      missing.push(`日期不是严格递增：${dates[i - 1]} -> ${dates[i]}`);
    }
  }
  return missing;
}

function splitCsvLine(line: string): string[] {
  const fields: string[] = [];
  let current = '';
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      if (quoted && line[i + 1] === '"') {
        current += '"';
        i += 1;
      } else {
        quoted = !quoted;
      }
    } else if (ch === ',' && !quoted) {
      fields.push(current);
      current = '';
    } else {
      current += ch;
    }
  }
  fields.push(current);
  return fields;
}

function parseDate(input: string): Date | null {
  if (!/^\d{4}-\d{1,2}-\d{1,2}$/.test(input)) return null;
  const [year, month, day] = input.split('-').map(Number);
  const date = new Date(year, month - 1, day);
  if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) {
    return null;
  }
  return date;
}

function toISODate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function dedupeByDate(points: Point[]): Point[] {
  const map = new Map<string, Point>();
  points.forEach((p) => map.set(p.date, p));
  return [...map.values()].sort((a, b) => a.date.localeCompare(b.date));
}
