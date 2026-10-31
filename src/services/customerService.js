import { get, paged } from './api';

// Customers are users with role "customer" (they sign up themselves via /auth/register).
export const listCustomers = (params) => paged('/users', { role: 'customer', ...params });
export const listAllCustomers = () => get('/users', { role: 'customer', limit: 200 });
