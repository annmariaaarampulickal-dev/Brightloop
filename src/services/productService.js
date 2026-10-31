import api, { call } from './api';
import { db } from './mockData';

const add = (key, data) => { const row = { id: ++db.seq.id, ...data }; db[key].push(row); return row; };

export const listProducts = () => call(() => [...db.products], () => api.get('/products'));
export const createProduct = (d) => call(() => add('products', d), () => api.post('/products', d));

export const listPlans = () => call(() => [...db.plans], () => api.get('/plans'));
export const createPlan = (d) => call(() => add('plans', d), () => api.post('/plans', d));
// action: 'close' | 'pause' | 'renew' -- only allowed where the admin enabled it on the plan
export const planAction = (id, action) =>
  call(() => ({ ok: true }), () => api.post(`/plans/${id}/${action}`));

export const listDiscounts = () => call(() => [...db.discounts], () => api.get('/discounts'));
export const createDiscount = (d) => call(() => add('discounts', { used: 0, ...d }), () => api.post('/discounts', d));

export const listTaxes = () => call(() => [...db.taxes], () => api.get('/taxes'));
export const createTax = (d) => call(() => add('taxes', d), () => api.post('/taxes', d));

export const listTemplates = () => call(() => [...db.templates], () => api.get('/quotation-templates'));
