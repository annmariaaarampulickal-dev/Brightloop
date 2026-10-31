import { Link } from 'react-router-dom';
import StatCard from '../components/StatCard';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import useFetch from '../hooks/useFetch';
import { getSummary } from '../services/paymentService';
import { money, fmtDate } from '../utils/format';

export default function Dashboard() {
  const { data, loading, error } = useFetch(() => getSummary(), []);
  if (error) return <div className="alert">{error}</div>;
  if (loading || !data) return <p className="muted">Loading…</p>;

  return (
    <>
      <div className="stat-grid">
        <StatCard label="Active subscriptions" value={data.activeSubscriptions} />
        <StatCard label="Monthly recurring revenue" value={money(data.mrr)} tone="green" />
        <StatCard label="Revenue collected" value={money(data.revenue)} tone="green" />
        <StatCard label="Outstanding" value={money(data.outstanding)} tone="amber" />
        <StatCard label="Overdue invoices" value={data.overdueCount} tone="red" />
      </div>

      <div className="card">
        <div className="card-head">
          <h3>Overdue invoices – chase these first</h3>
          <Link to="/app/invoices" className="btn btn-ghost">All invoices</Link>
        </div>
        <DataTable
          rows={data.overdue}
          pageSize={5}
          empty="No overdue invoices 🎉"
          columns={[
            { key: 'number', label: 'Invoice' },
            { key: 'customer', label: 'Customer' },
            { key: 'dueDate', label: 'Due', render: (r) => fmtDate(r.dueDate) },
            { key: 'bal', label: 'Balance', render: (r) => money(r.total - r.paid) },
            { key: 'status', label: 'Status', render: () => <StatusBadge status="Overdue" /> },
          ]}
        />
      </div>
    </>
  );
}
