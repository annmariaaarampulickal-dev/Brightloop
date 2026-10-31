import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Topbar from '../components/Topbar';
import { useAuth } from '../hooks/useAuth';

const ALL = [
  { to: '/app', end: true, label: 'Dashboard', icon: '▦' },
  { to: '/app/subscriptions', label: 'Subscriptions', icon: '↻' },
  { to: '/app/customers', label: 'Customers', icon: '☺' },
  { to: '/app/products', label: 'Products & Plans', icon: '▣' },
  { to: '/app/invoices', label: 'Invoices', icon: '☰' },
  { to: '/app/payments', label: 'Payments', icon: '₹' },
  { to: '/app/analytics', label: 'Analytics', icon: '◔' },
  { to: '/app/settings', label: 'Settings', icon: '⚙', adminOnly: true },
];

export default function AdminLayout() {
  const { isAdmin } = useAuth();
  const links = ALL.filter((l) => !l.adminOnly || isAdmin);
  return (
    <div className="shell">
      <Sidebar links={links} />
      <div className="main">
        <Topbar title="Subscription Management" />
        <div className="content"><Outlet /></div>
      </div>
    </div>
  );
}
