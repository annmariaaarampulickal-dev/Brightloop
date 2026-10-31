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

// lines: [{qty, unitPrice, taxRate}]  discount: {type:'percent'|'fixed', value} | null
export const calcTotals = (lines = [], discount = null) => {
  const subtotal = lines.reduce((s, l) => s + l.qty * l.unitPrice, 0);
  let disc = 0;
  if (discount) disc = discount.type === 'percent' ? (subtotal * discount.value) / 100 : discount.value;
  disc = Math.min(disc, subtotal);
  const ratio = subtotal ? (subtotal - disc) / subtotal : 0;
  const tax = lines.reduce((s, l) => s + (l.qty * l.unitPrice * (l.taxRate || 0)) / 100, 0) * ratio;
  return { subtotal, discount: disc, tax, total: subtotal - disc + tax };
};

export const isOverdue = (inv) =>
  inv.status === 'Confirmed' && inv.dueDate < today() && inv.total - inv.paid > 0;
