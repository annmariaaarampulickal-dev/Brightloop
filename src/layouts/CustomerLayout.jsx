import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Topbar from '../components/Topbar';

const LINKS = [
  { to: '/portal', end: true, label: 'My Subscriptions', icon: '↻' },
  { to: '/portal/invoices', label: 'My Invoices', icon: '☰' },
  { to: '/portal/payments', label: 'My Payments', icon: '₹' },
];

export default function CustomerLayout() {
  return (
    <div className="shell">
      <Sidebar links={LINKS} />
      <div className="main">
        <Topbar title="Customer Portal" />
        <div className="content"><Outlet /></div>
      </div>
    </div>
  );
}
