import axios from 'axios';

export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || '/api' });

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.clear();
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

const delay = (ms = 150) => new Promise((r) => setTimeout(r, ms));

// call(mockFn, realRequestFn): runs the mock when VITE_USE_MOCK=true, else hits the backend.
export const call = async (mockFn, realFn) => {
  if (USE_MOCK) {
    await delay();
    return mockFn();
  }
  const res = await realFn();
  return res.data;
};

export default api;
