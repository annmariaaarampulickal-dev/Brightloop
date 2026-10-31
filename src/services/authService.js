import { get, post } from './api';

// POST /auth/login returns only a token, so we fetch the profile (id, name, role) with GET /auth/me
export const login = async (email, password) => {
  const { access_token } = await post('/auth/login', { email, password });
  localStorage.setItem('token', access_token);
  try {
    return await get('/auth/me');
  } catch (e) {
    localStorage.removeItem('token');
    throw e;
  }
};

export const register = (name, email, password) => post('/auth/register', { name, email, password });
export const forgotPassword = (email) => post('/auth/forgot-password', { email });
export const resetPassword = (token, newPassword) => post('/auth/reset-password', { token, new_password: newPassword });

// Admin only
export const addStaff = (data) => post('/users/staff', data);
export const listStaff = () => get('/users', { role: 'staff', limit: 200 });
