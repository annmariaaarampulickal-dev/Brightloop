import { get, paged, post } from './api';

// params: { status, customer_id, plan_id, page, pageSize }
export const listSubscriptions = (params) => paged('/subscriptions', params);
export const listSubscriptionsForPicker = () => get('/subscriptions', { limit: 200 });

export const createSubscription = (data) => post('/subscriptions', data);
export const createFromTemplate = (templateId, data) => post(`/subscriptions/from-template/${templateId}`, data);

// to: quotation | confirmed | active | paused | closed
export const transitionSubscription = (id, to) => post(`/subscriptions/${id}/transition`, { to });
export const renewSubscription = (id) => post(`/subscriptions/${id}/renew`);
