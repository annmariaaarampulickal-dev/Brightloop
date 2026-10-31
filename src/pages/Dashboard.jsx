import { Link } from 'react-router-dom';
import StatCard from '../components/StatCard';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import useFetch from '../hooks/useFetch';
import { getSummary, getOverdue } from '../services/reportService';
import { money, fmtDate } from '../utils/format';

export default function Dashboard() {
  const sum = useFetch(() => getSummary(), []);
  const od = useFetch(() => getOverdue({ limit: 10 }), []);
  if (sum.error) return <div className="alert">{sum.error}</div>;
  if (sum.loading || !sum.data) return <p className="muted">Loading…</p>;
  const s = sum.data;

  return (
    <>
      <div className="stat-grid">
        <StatCard label="Active subscriptions" value={s.subscriptions.active} />
        <StatCard label="Monthly recurring revenue" value={money(s.subscriptions.mrr)} tone="green" />
        <StatCard label="Revenue collected" value={money(s.payments.collected)} hint={`${s.payments.count} payments`} tone="green" />
        <StatCard label="Outstanding" value={money(s.receivables.outstanding)} tone="amber" />
        <StatCard label="Overdue" value={s.receivables.overdue_count} hint={money(s.receivables.overdue_amount)} tone="red" />
      </div>

      <div className="card">
        <div className="card-head">
          <h3>Overdue invoices – chase these first</h3>
          <Link to="/app/invoices" className="btn btn-ghost">All invoices</Link>
        </div>
        {od.error && <div className="alert">{od.error}</div>}
        <DataTable
          rows={od.data || []}
          loading={od.loading}
          pageSize={5}
          empty="No overdue invoices 🎉"
          columns={[
            { key: 'number', label: 'Invoice' },
            { key: 'customer_name', label: 'Customer' },
            { key: 'due_date', label: 'Due', render: (r) => fmtDate(r.due_date) },
            { key: 'days_overdue', label: 'Days late' },
            { key: 'amount_due', label: 'Amount due', render: (r) => money(r.amount_due) },
            { key: 'status', label: 'Status', render: () => <StatusBadge status="overdue" /> },
          ]}
        />
      </div>
    </>
  );
}
