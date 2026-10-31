const COLORS = {
  Draft: 'gray', Quotation: 'blue', Confirmed: 'purple', Active: 'green', Closed: 'gray',
  Paid: 'green', Cancelled: 'red', Overdue: 'red', Outstanding: 'amber',
};

export default function StatusBadge({ status }) {
  return <span className={`badge badge-${COLORS[status] || 'gray'}`}>{status}</span>;
}
