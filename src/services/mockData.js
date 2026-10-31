// Fake in-memory database so the UI works before the backend exists.
import { today, addDays } from '../utils/format';

export const db = {
  users: [
    { id: 1, name: 'Admin', email: 'admin@brightloop.com', password: 'Admin@12345', role: 'admin' },
    { id: 2, name: 'Staff Sam', email: 'staff@brightloop.com', password: 'Staff@12345', role: 'staff' },
    { id: 3, name: 'Acme Traders', email: 'customer@acme.com', password: 'Cust@12345', role: 'customer', customerId: 1 },
  ],
  customers: [
    { id: 1, name: 'Acme Traders', email: 'customer@acme.com', phone: '9876543210' },
    { id: 2, name: 'Globex Corp', email: 'billing@globex.com', phone: '9123456780' },
    { id: 3, name: 'Initech', email: 'ap@initech.com', phone: '9000011111' },
  ],
  taxes: [
    { id: 1, name: 'GST 18%', rate: 18 },
    { id: 2, name: 'GST 5%', rate: 5 },
    { id: 3, name: 'No Tax', rate: 0 },
  ],
  products: [
    { id: 1, name: 'Brightloop CRM', type: 'Software', salesPrice: 1200, costPrice: 700, notes: 'Core CRM seat',
      variants: [{ attribute: 'Brand', value: 'Odoo', extraPrice: 560 }, { attribute: 'Brand', value: 'Zoho', extraPrice: 300 }] },
    { id: 2, name: 'Analytics Add-on', type: 'Add-on', salesPrice: 400, costPrice: 150, notes: '', variants: [] },
    { id: 3, name: 'Priority Support', type: 'Service', salesPrice: 900, costPrice: 400, notes: '', variants: [] },
  ],
  plans: [
    { id: 1, name: 'CRM Monthly', price: 1200, billing: 'monthly', minQty: 1, startDate: '2026-01-01', endDate: '2027-12-31',
      autoClose: true, closable: true, pausable: true, renewable: true },
    { id: 2, name: 'CRM Yearly', price: 12000, billing: 'yearly', minQty: 5, startDate: '2026-01-01', endDate: '2027-12-31',
      autoClose: false, closable: true, pausable: false, renewable: true },
  ],
  templates: [
    { id: 1, name: 'Standard SMB Offer', planId: 1, validDays: 30,
      lines: [{ productId: 1, qty: 5 }, { productId: 2, qty: 5 }] },
  ],
  discounts: [
    { id: 1, name: 'Volume 10%', type: 'percent', value: 10, minPurchase: 5000, minQty: 5,
      startDate: '2026-01-01', endDate: '2027-12-31', usageLimit: 100, used: 2, appliesTo: 'subscription', targetId: null },
  ],
  subscriptions: [],
  invoices: [],
  payments: [],
  seq: { sub: 1000, inv: 5000, id: 100 },
};

const line = (productId, qty, taxId = 1) => {
  const p = db.products.find((x) => x.id === productId);
  const t = db.taxes.find((x) => x.id === taxId);
  return { productId, product: p.name, qty, unitPrice: p.salesPrice, taxId, taxRate: t.rate };
};

db.subscriptions = [
  { id: 1, number: 'SUB-1001', customerId: 1, customer: 'Acme Traders', planId: 1, plan: 'CRM Monthly', status: 'Active',
    startDate: '2026-09-01', expiryDate: '2027-09-01', paymentTerms: 'Net 15', lines: [line(1, 5), line(2, 5)], lastBilled: '' },
  { id: 2, number: 'SUB-1002', customerId: 2, customer: 'Globex Corp', planId: 2, plan: 'CRM Yearly', status: 'Active',
    startDate: '2026-03-01', expiryDate: '2027-03-01', paymentTerms: 'Net 30', lines: [line(1, 20)], lastBilled: '' },
  { id: 3, number: 'SUB-1003', customerId: 3, customer: 'Initech', planId: 1, plan: 'CRM Monthly', status: 'Quotation',
    startDate: today(), expiryDate: addDays(today(), 365), paymentTerms: 'Immediate', lines: [line(3, 2)], lastBilled: '' },
];
db.seq.sub = 1003;

db.invoices = [
  { id: 1, number: 'INV-4001', subscriptionId: 2, customerId: 2, customer: 'Globex Corp', date: '2026-09-01', dueDate: '2026-10-01',
    status: 'Confirmed', lines: [line(1, 20)], subtotal: 24000, discount: 0, tax: 4320, total: 28320, paid: 0 },
  { id: 2, number: 'INV-4002', subscriptionId: 1, customerId: 1, customer: 'Acme Traders', date: '2026-10-01', dueDate: '2026-10-16',
    status: 'Paid', lines: [line(1, 5)], subtotal: 6000, discount: 0, tax: 1080, total: 7080, paid: 7080 },
];
db.payments = [
  { id: 1, invoiceId: 2, invoice: 'INV-4002', customerId: 1, customer: 'Acme Traders', method: 'UPI', amount: 7080, date: '2026-10-10', note: 'Paid in full' },
];
