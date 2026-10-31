import { useEffect, useState } from 'react';
import { PAGE_SIZE } from '../utils/constants';

// columns: [{ key, label, render?(row) }]
// Client mode (default): pass all rows, the table pages them itself.
// Server mode: pass `page` + `onPageChange` and rows fetched with services' paged() helper.
//   paged() asks for PAGE_SIZE + 1 rows; the extra one only tells us a next page exists.
export default function DataTable({ columns, rows = [], pageSize = PAGE_SIZE, loading = false, empty = 'Nothing here yet', page = 0, onPageChange }) {
  const server = typeof onPageChange === 'function';
  const [localPage, setLocalPage] = useState(0);
  useEffect(() => { if (!server) setLocalPage(0); }, [rows.length, server]);

  const cur = server ? page : localPage;
  const setCur = server ? onPageChange : setLocalPage;
  const shown = server ? rows.slice(0, pageSize) : rows.slice(cur * pageSize, cur * pageSize + pageSize);
  const hasNext = server ? rows.length > pageSize : (cur + 1) * pageSize < rows.length;
  const showPager = server ? cur > 0 || hasNext : rows.length > pageSize;
  const pages = Math.max(1, Math.ceil(rows.length / pageSize));

  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>{columns.map((c) => <th key={c.key}>{c.label}</th>)}</tr>
        </thead>
        <tbody>
          {loading && <tr><td colSpan={columns.length} className="muted center">Loading…</td></tr>}
          {!loading && shown.length === 0 && <tr><td colSpan={columns.length} className="muted center">{empty}</td></tr>}
          {!loading && shown.map((row, i) => (
            <tr key={row.id ?? row.invoice_id ?? i}>
              {columns.map((c) => <td key={c.key}>{c.render ? c.render(row) : row[c.key]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      {showPager && (
        <div className="pager">
          <button className="btn btn-ghost" disabled={cur === 0} onClick={() => setCur(cur - 1)}>Prev</button>
          <span>{server ? `Page ${cur + 1}` : `Page ${cur + 1} of ${pages} · ${rows.length} rows`}</span>
          <button className="btn btn-ghost" disabled={!hasNext} onClick={() => setCur(cur + 1)}>Next</button>
        </div>
      )}
    </div>
  );
}
