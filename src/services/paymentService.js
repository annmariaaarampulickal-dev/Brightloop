import api, { call } from './api';
import { db } from './mockData';

export const listPayments = (params = {}) =>
  call(() => db.payments.filter((p) => !params.customerId || p.customerId === params.customerId), () => api.get('/payments', { params }));

export const recordPayment = (data) =>
  call(
    () => {
      const inv = db.invoices.find((i) => i.id === Number(data.invoiceId));
      const amount = Number(data.amount);
      if (inv.status === 'Draft' || inv.status === 'Cancelled') throw new Error('Confirm the invoice first');
      inv.paid += amount;
      if (inv.paid >= inv.total) inv.status = 'Paid';
      const p = { id: ++db.seq.id, invoiceId: inv.id, invoice: inv.number, customerId: inv.customerId, customer: inv.customer, ...data, amount };
      db.payments.unshift(p);
      return p;
    },
    () => api.post('/payments', data)
  );

// Summary for dashboard/analytics. Backend should compute this with SQL aggregates (keeps pages < 2s).
export const getSummary = (params = {}) =>
  call(
    () => {
      const invs = db.invoices.filter((i) => i.status !== 'Cancelled' && (!params.from || i.date >= params.from) && (!params.to || i.date <= params.to));
      const revenue = db.payments.filter((p) => (!params.from || p.date >= params.from) && (!params.to || p.date <= params.to))
        .reduce((s, p) => s + p.amount, 0);
      const outstanding = invs.reduce((s, i) => s + (i.total - i.paid), 0);
      const t = new Date().toISOString().slice(0, 10);
      const overdue = invs.filter((i) => i.status === 'Confirmed' && i.dueDate < t && i.total - i.paid > 0);
      const byMethod = {};
      db.payments.forEach((p) => { byMethod[p.method] = (byMethod[p.method] || 0) + p.amount; });
      return {
        activeSubscriptions: db.subscriptions.filter((s) => s.status === 'Active').length,
        mrr: db.subscriptions.filter((s) => s.status === 'Active').reduce((s, x) => s + x.lines.reduce((n, l) => n + l.qty * l.unitPrice, 0), 0),
        revenue, outstanding, overdueCount: overdue.length, overdue, byMethod,
      };
    },
    () => api.get('/reports/summary', { params })
  );
