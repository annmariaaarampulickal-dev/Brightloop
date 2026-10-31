import { useState } from 'react';
import DataTable from '../components/DataTable';
import useFetch from '../hooks/useFetch';
import useDebounce from '../hooks/useDebounce';
import { listCustomers } from '../services/customerService';

export default function Customers() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const q = useDebounce(search);
  const { data, loading, error } = useFetch(() => listCustomers({ q, page }), [q, page]);

  return (
    <>
      <div className="toolbar">
        <input placeholder="Search name or email…" value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} />
        <span className="muted">Customers create their own account on the Register page.</span>
      </div>
      {error && <div className="alert">{error}</div>}
      <DataTable
        loading={loading} rows={data || []} page={page} onPageChange={setPage}
        columns={[
          { key: 'id', label: 'ID' },
          { key: 'name', label: 'Name' },
          { key: 'email', label: 'Email' },
          { key: 'is_active', label: 'Active', render: (r) => (r.is_active ? 'Yes' : 'No') },
        ]}
      />
    </>
  );
}
