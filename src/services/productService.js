import { get, post, patch, del } from './api';

export const listProducts = () => get('/products', { limit: 200 });
export const createProduct = (d) => post('/products', d);

export const listPlans = () => get('/plans', { limit: 200 });
export const createPlan = (d) => post('/plans', d);
export const updatePlan = (id, d) => patch(`/plans/${id}`, d);

export const listTaxes = () => get('/taxes');
export const createTax = (d) => post('/taxes', d);
export const deactivateTax = (id) => del(`/taxes/${id}`);

export const listTemplates = () => get('/quotation-templates');

export const listDiscounts = () => get('/discounts', { limit: 200 });
export const createDiscount = (d) => post('/discounts', d);
export const updateDiscount = (id, d) => patch(`/discounts/${id}`, d);
