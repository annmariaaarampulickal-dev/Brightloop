import api, { call } from './api';
import { db } from './mockData';

const fail = (msg) => { const e = new Error(msg); e.response = { data: { message: msg } }; throw e; };

export const login = (email, password) =>
  call(
    () => {
      const u = db.users.find((x) => x.email.toLowerCase() === email.toLowerCase() && x.password === password);
      if (!u) fail('Invalid email or password');
      const { password: _p, ...user } = u;
      return { token: 'mock-token-' + u.id, user };
    },
    () => api.post('/auth/login', { email, password })
  );

export const register = (name, email, password) =>
  call(
    () => {
      if (db.users.some((u) => u.email.toLowerCase() === email.toLowerCase())) fail('This email already has an account');
      const cust = { id: ++db.seq.id, name, email, phone: '' };
      db.customers.push(cust);
      db.users.push({ id: cust.id + 1000, name, email, password, role: 'customer', customerId: cust.id });
      return { ok: true };
    },
    () => api.post('/auth/register', { name, email, password })
  );

// Backend should email a reset link to the registered address
export const forgotPassword = (email) =>
  call(() => ({ ok: true }), () => api.post('/auth/forgot-password', { email }));

export const resetPassword = (token, password) =>
  call(() => ({ ok: true }), () => api.post('/auth/reset-password', { token, password }));

// Admin only
export const addStaff = (data) =>
  call(
    () => {
      if (db.users.some((u) => u.email === data.email)) fail('Email already in use');
      db.users.push({ id: ++db.seq.id, role: 'staff', ...data });
      return { ok: true };
    },
    () => api.post('/users/staff', data)
  );

export const listStaff = () =>
  call(() => db.users.filter((u) => u.role === 'staff').map(({ password, ...u }) => u), () => api.get('/users/staff'));
