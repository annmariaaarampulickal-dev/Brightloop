import { get } from './api';

// params: { date_from, date_to, customer_id, plan_id }
export const getSummary = (params) => get('/reports/summary', params);
export const getOverdue = (params) => get('/reports/overdue', { limit: 50, ...params });
export const getMonthly = (months = 12) => get('/reports/monthly', { months });
