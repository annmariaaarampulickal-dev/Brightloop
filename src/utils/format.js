export const money = (n) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(n || 0);

export const fmtDate = (d) =>
  d ? new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '-';

export const today = () => new Date().toISOString().slice(0, 10);

export const addDays = (date, days) => {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
};

// "bank_transfer" -> "Bank transfer"
export const cap = (s = '') => {
  const t = String(s).replace(/_/g, ' ');
  return t.charAt(0).toUpperCase() + t.slice(1);
};

// Rough on-screen estimate for the new-subscription form. The backend does the real maths.
export const estimate = (lines = []) => {
  const subtotal = lines.reduce((s, l) => s + l.quantity * l.unit_price, 0);
  const tax = lines.reduce((s, l) => s + (l.quantity * l.unit_price * (l.tax_rate || 0)) / 100, 0);
  return { subtotal, tax, total: subtotal + tax };
};
