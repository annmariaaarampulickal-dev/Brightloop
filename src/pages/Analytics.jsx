import { useState } from 'react';
import StatCard from '../components/StatCard';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import useFetch from '../hooks/useFetch';
import useLookups from '../hooks/useLookups';
import { getSummary, getOverdue, getMonthly } from '../services/reportService';
import { PAY_METHODS } from '../utils/constants';
import { money, fmtDate, cap } from '../utils/format';

export default function Analytics() {
  const L = useLookups();
  const [f, setF] = useState({ date_from: '', date_to: '', customer_id: '', plan_id: '' });
  const sum = useFetch(() => getSummary(f), [f.date_from, f.date_to, f.customer_id, f.plan_id]);
  const od = useFetch(() => getOverdue({ customer_id: f.customer_id }), [f.customer_id]);
  const monthly = useFetch(() => getMonthly(12), []);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const s = sum.data;
  const methods = Object.entries(s?.payments.by_method || {});
  const maxMethod = Math.max(1, ...methods.map(([, v]) => v));
  const months = monthly.data || [];
  const maxMonth = Math.max(1, ...months.flatMap((m) => [m.invoiced, m.collected]));

  return (
    <>
      <div className="toolbar">
        <label className="inline">From <input type="date" value={f.date_from} onChange={set('date_from')} /></label>
        <label className="inline">To <input type="date" value={f.date_to} onChange={set('date_to')} /></label>
        <select value={f.customer_id} onChange={set('customer_id')}>
          <option value="">All customers</option>
          {L.customers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <select value={f.plan_id} onChange={set('plan_id')}>
          <option value="">All plans</option>
          {L.plans.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <button className="btn btn-ghost" onClick={() => setF({ date_from: '', date_to: '', customer_id: '', plan_id: '' })}>Clear</button>
      </div>
      {sum.error && <div className="alert">{sum.error}</div>}
      {sum.loading || !s ? <p className="muted">Loading…</p> : (
        <>
          <div className="stat-grid">
            <StatCard label="Active subscriptions" value={s.subscriptions.active} />
            <StatCard label="Monthly recurring revenue" value={money(s.subscriptions.mrr)} tone="green" />
            <StatCard label="Invoiced (period)" value={money(s.invoices.invoiced_total)} />
            <StatCard label="Collected (period)" value={money(s.payments.collected)} hint={`${s.payments.count} payments`} tone="green" />
            <StatCard label="Still owed" value={money(s.receivables.outstanding)} tone="amber" />
            <StatCard label="Overdue" value={s.receivables.overdue_count} hint={money(s.receivables.overdue_amount)} tone="red" />
          </div>

          <div className="card">
            <h3>Invoiced vs collected – last 12 months</h3>
            <div className="legend"><span className="dot dot-a" /> Invoiced <span className="dot dot-b" /> Collected</div>
            <div className="chart">
              {months.map((m) => (
                <div className="chart-col" key={m.month} title={`${m.month}: invoiced ${money(m.invoiced)}, collected ${money(m.collected)}`}>
                  <div className="chart-bars">
                    <div className="chart-bar bar-a" style={{ height: `${(m.invoiced / maxMonth) * 100}%` }} />
                    <div className="chart-bar bar-b" style={{ height: `${(m.collected / maxMonth) * 100}%` }} />
                  </div>
                  <div className="chart-label">{m.month.slice(5)}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid2">
            <div className="card">
              <h3>Collected by method</h3>
              {methods.length === 0 && <p className="muted">No payments in this range</p>}
              {methods.map(([m, v]) => (
                <div className="bar-row" key={m}>
                  <span className="bar-label">{PAY_METHODS.find((x) => x.value === m)?.label || m}</span>
                  <div className="bar"><div className="bar-fill" style={{ width: `${(v / maxMethod) * 100}%` }} /></div>
                  <span className="bar-val">{money(v)}</span>
                </div>
              ))}
            </div>
            <div className="card">
              <h3>Subscriptions by status</h3>
              {Object.entries(s.subscriptions.by_status).map(([k, v]) => (
                <div className="bar-row" key={k}><span className="bar-label"><StatusBadge status={k} /></span><b>{v}</b></div>
              ))}
              <h3 style={{ marginTop: 16 }}>Invoices by status</h3>
              {Object.entries(s.invoices.by_status).map(([k, v]) => (
                <div className="bar-row" key={k}><span className="bar-label">{cap(k)}</span><b>{v}</b></div>
              ))}
            </div>
          </div>

          <div className="card">
            <h3>Overdue invoices (oldest first)</h3>
            {od.error && <div className="alert">{od.error}</div>}
            <DataTable rows={od.data || []} loading={od.loading} pageSize={10} empty="Nothing overdue" columns={[
              { key: 'number', label: 'Invoice' }, { key: 'customer_name', label: 'Customer' }, { key: 'customer_email', label: 'Email' },
              { key: 'due_date', label: 'Due', render: (r) => fmtDate(r.due_date) },
              { key: 'days_overdue', label: 'Days late' },
              { key: 'amount_due', label: 'Amount due', render: (r) => money(r.amount_due) },
            ]} />
          </div>
        </>
      )}
    </>
  );
}
