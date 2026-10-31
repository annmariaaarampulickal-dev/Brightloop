import api, { paged, post } from './api';

// params: { status, customer_id, overdue, outstanding, issued_from, issued_to, page, pageSize }
export const listInvoices = (params) => paged('/invoices', params);

// action: confirm | cancel | send
export const invoiceAction = (id, action) => post(`/invoices/${id}/${action}`);

// The print page needs the login token, so fetch it with axios and open the HTML in a new tab.
export const printInvoice = async (id) => {
  const win = window.open('', '_blank');
  const { data } = await api.get(`/invoices/${id}/print`, { responseType: 'text' });
  const url = URL.createObjectURL(new Blob([data], { type: 'text/html' }));
  win.location.href = url;
};

// Billing day. Safe to run twice: periods that already have an invoice are skipped.
export const runBilling = (autoConfirm = false) => post('/billing/run', { auto_confirm: autoConfirm });
