import { paged, post } from './api';

// params: { method, date_from, date_to, page, pageSize }
export const listPayments = (params) => paged('/payments', params);

// data: { invoice_id, method, amount, payment_date, note }
export const recordPayment = (data) => post('/payments', data);
