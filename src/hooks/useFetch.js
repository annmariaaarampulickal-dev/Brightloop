import { useCallback, useEffect, useState } from 'react';

// const { data, loading, error, reload } = useFetch(() => listInvoices(filters), [filters])
export default function useFetch(fn, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const run = useCallback(() => {
    setLoading(true);
    fn()
      .then((d) => { setData(d); setError(''); })
      .catch((e) => setError(e.response?.data?.message || e.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(run, [run]);
  return { data, loading, error, reload: run };
}
