import api, { call } from './api';
import { db } from './mockData';
import { SUB_FLOW } from '../utils/constants';

// params: { search, status, customerId, page, pageSize }  (backend should paginate for thousands of rows)
export const listSubscriptions = (params = {}) =>
  call(
    () =>
      db.subscriptions.filter(
        (s) =>
          (!params.customerId || s.customerId === params.customerId) &&
          (!params.status || s.status === params.status) &&
          (!params.search || (s.number + s.customer).toLowerCase().includes(params.search.toLowerCase()))
      ),
    () => api.get('/subscriptions', { params })
  );

export const createSubscription = (data) =>
  call(
    () => {
      const cust = db.customers.find((c) => c.id === Number(data.customerId));
      const plan = db.plans.find((p) => p.id === Number(data.planId));
      const sub = {
        id: ++db.seq.id, number: `SUB-${++db.seq.sub}`, ...data,
        customerId: cust.id, customer: cust.name, planId: plan.id, plan: plan.name, status: 'Draft', lastBilled: '',
      };
      db.subscriptions.unshift(sub);
      return sub;
    },
    () => api.post('/subscriptions', data)
  );

// Moves one step forward: Draft -> Quotation -> Confirmed -> Active -> Closed
export const advanceSubscription = (id) =>
  call(
    () => {
      const s = db.subscriptions.find((x) => x.id === id);
      const i = SUB_FLOW.indexOf(s.status);
      if (i < SUB_FLOW.length - 1) s.status = SUB_FLOW[i + 1];
      return s;
    },
    () => api.post(`/subscriptions/${id}/advance`)
  );
