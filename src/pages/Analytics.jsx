import { useState } from 'react';
import StatCard from '../components/StatCard';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import useFetch from '../hooks/useFetch';
import { getSummary } from '../services/paymentService';
import { money, fmtDate } from '../utils/format';

export default function Analytics() {
  const [range, setRange] = useState({ from: '', to: '' });
  const { data, loading, error } = useFetch(() => getSummary(range), [range.from, range.to]);

  const methods = Object.entries(data?.byMethod || {});
  const max = Math.max(1, ...methods.map(([, v]) => v));

  return (
    <>
      <div className="toolbar">
        <label className="inline">From <input type="date" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} /></label>
        <label className="inline">To <input type="date" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} /></label>
        <button className="btn btn-ghost" onClick={() => setRange({ from: '', to: '' })}>Clear</button>
      </div>
      {error && <div className="alert">{error}</div>}
      {loading || !data ? <p className="muted">Loading…</p> : (
        <>
          <div className="stat-grid">
            <StatCard label="Active subscriptions" value={data.activeSubscriptions} />
            <StatCard label="Recurring revenue / cycle" value={money(data.mrr)} tone="green" />
            <StatCard label="Revenue received" value={money(data.revenue)} tone="green" />
            <StatCard label="Still owed" value={money(data.outstanding)} tone="amber" />
            <StatCard label="Overdue invoices" value={data.overdueCount} tone="red" />
          </div>

          <div className="card">
            <h3>Payments by method</h3>
            {methods.length === 0 && <p className="muted">No payments in this range</p>}
            {methods.map(([m, v]) => (
              <div className="bar-row" key={m}>
                <span className="bar-label">{m}</span>
                <div className="bar"><div className="bar-fill" style={{ width: `${(v / max) * 100}%` }} /></div>
                <span className="bar-val">{money(v)}</span>
              </div>
            ))}
          </div>

          <div className="card">
            <h3>Overdue invoices</h3>
            <DataTable rows={data.overdue} pageSize={10} empty="Nothing overdue" columns={[
              { key: 'number', label: 'Invoice' }, { key: 'customer', label: 'Customer' },
              { key: 'dueDate', label: 'Due', render: (r) => fmtDate(r.dueDate) },
              { key: 'bal', label: 'Balance', render: (r) => money(r.total - r.paid) },
              { key: 's', label: 'Status', render: () => <StatusBadge status="Overdue" /> },
            ]} />
          </div>
        </>
      )}
    </>
  );
}
