import api, { call } from './api';
import { db } from './mockData';
import { today, addDays, calcTotals, isOverdue } from '../utils/format';
import { termDays } from '../utils/constants';

export const listInvoices = (params = {}) =>
  call(
    () =>
      db.invoices.filter(
        (i) =>
          (!params.customerId || i.customerId === params.customerId) &&
          (!params.status || (params.status === 'Overdue' ? isOverdue(i) : i.status === params.status)) &&
          (!params.search || (i.number + i.customer).toLowerCase().includes(params.search.toLowerCase()))
      ),
    () => api.get('/invoices', { params })
  );

// action: 'confirm' | 'cancel' | 'send' | 'print'
export const invoiceAction = (id, action) =>
  call(
    () => {
      const inv = db.invoices.find((i) => i.id === id);
      if (action === 'confirm' && inv.status === 'Draft') inv.status = 'Confirmed';
      if (action === 'cancel' && inv.status !== 'Paid') inv.status = 'Cancelled';
      return inv;
    },
    () => api.post(`/invoices/${id}/${action}`)
  );

export const printInvoice = (id) => window.open(`${import.meta.env.VITE_API_URL || '/api'}/invoices/${id}/print`, '_blank');

// Bulk billing run. Backend must be idempotent: one invoice per subscription per period.
export const generateDueInvoices = () =>
  call(
    () => {
      const period = today().slice(0, 7);
      let created = 0, skipped = 0;
      db.subscriptions.filter((s) => s.status === 'Active').forEach((s) => {
        if (s.lastBilled === period) { skipped++; return; }
        const disc = db.discounts.find((d) => d.endDate >= today() && d.used < d.usageLimit &&
          s.lines.reduce((n, l) => n + l.qty, 0) >= d.minQty);
        const t = calcTotals(s.lines, disc);
        db.invoices.unshift({
          id: ++db.seq.id, number: `INV-${++db.seq.inv}`, subscriptionId: s.id, customerId: s.customerId, customer: s.customer,
          date: today(), dueDate: addDays(today(), termDays(s.paymentTerms)), status: 'Draft', lines: s.lines,
          subtotal: t.subtotal, discount: t.discount, tax: t.tax, total: t.total, paid: 0,
        });
        if (disc) disc.used++;
        s.lastBilled = period;
        created++;
      });
      return { created, skipped };
    },
    () => api.post('/invoices/generate')
  );
