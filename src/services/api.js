import axios from 'axios';
import { PAGE_SIZE } from '../utils/constants';

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000' });

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    // an expired token sends you back to login (but a wrong password on the login form just shows an error)
    if (err.response?.status === 401 && !err.config?.url?.includes('/auth/login')) {
      localStorage.clear();
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// FastAPI treats "?status=" as the text "" (matches nothing), so drop empty params.
const clean = (p = {}) => Object.fromEntries(Object.entries(p).filter(([, v]) => v !== undefined && v !== null && v !== ''));

export const get = (url, params) => api.get(url, { params: clean(params) }).then((r) => r.data);
export const post = (url, body) => api.post(url, body).then((r) => r.data);
export const patch = (url, body) => api.patch(url, body).then((r) => r.data);
export const del = (url) => api.delete(url).then((r) => r.data);

// The backend pages with skip/limit and has no "total", so we ask for one extra row
// to learn whether a next page exists (DataTable hides the extra row).
export const paged = (url, { page = 0, pageSize = PAGE_SIZE, ...rest } = {}) =>
  get(url, { ...rest, skip: page * pageSize, limit: pageSize + 1 });

export default api;
