import { cap } from '../utils/format';

const COLORS = {
  draft: 'gray', quotation: 'blue', confirmed: 'purple', active: 'green', paused: 'amber', closed: 'gray',
  paid: 'green', cancelled: 'red', overdue: 'red',
};

export default function StatusBadge({ status }) {
  return <span className={`badge badge-${COLORS[status] || 'gray'}`}>{cap(status)}</span>;
}
