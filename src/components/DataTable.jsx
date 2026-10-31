import { useEffect, useState } from 'react';

// columns: [{ key, label, render?(row) }]. Client-side paging keeps big lists snappy.
export default function DataTable({ columns, rows = [], pageSize = 15, loading = false, empty = 'Nothing here yet' }) {
  const [page, setPage] = useState(0);
  const pages = Math.max(1, Math.ceil(rows.length / pageSize));

  useEffect(() => setPage(0), [rows.length]);

  const slice = rows.slice(page * pageSize, page * pageSize + pageSize);

  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>{columns.map((c) => <th key={c.key}>{c.label}</th>)}</tr>
        </thead>
        <tbody>
          {loading && <tr><td colSpan={columns.length} className="muted center">Loading…</td></tr>}
          {!loading && slice.length === 0 && <tr><td colSpan={columns.length} className="muted center">{empty}</td></tr>}
          {!loading && slice.map((row, i) => (
            <tr key={row.id ?? i}>
              {columns.map((c) => <td key={c.key}>{c.render ? c.render(row) : row[c.key]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > pageSize && (
        <div className="pager">
          <button className="btn btn-ghost" disabled={page === 0} onClick={() => setPage(page - 1)}>Prev</button>
          <span>Page {page + 1} of {pages} · {rows.length} rows</span>
          <button className="btn btn-ghost" disabled={page >= pages - 1} onClick={() => setPage(page + 1)}>Next</button>
        </div>
      )}
    </div>
  );
}
