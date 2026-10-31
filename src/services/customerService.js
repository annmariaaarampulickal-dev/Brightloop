import api, { call } from './api';
import { db } from './mockData';

export const listCustomers = () => call(() => [...db.customers], () => api.get('/customers'));

export const createCustomer = (data) =>
  call(() => { const c = { id: ++db.seq.id, ...data }; db.customers.push(c); return c; }, () => api.post('/customers', data));
