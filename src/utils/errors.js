// FastAPI errors look like { detail: "text" } or { detail: [{ msg, loc }, ...] } for validation (422).
export const errMsg = (e) => {
  const d = e?.response?.data?.detail;
  if (Array.isArray(d)) {
    return d.map((x) => (x.msg || '').replace(/^Value error, /, '')).filter(Boolean).join('. ') || 'Invalid input';
  }
  if (typeof d === 'string') return d;
  if (e?.code === 'ERR_NETWORK') return 'Cannot reach the server. Is the backend running on port 8000?';
  return e?.message || 'Something went wrong';
};
