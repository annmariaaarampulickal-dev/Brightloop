import { useState } from 'react';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import useFetch from '../hooks/useFetch';
import { useAuth } from '../hooks/useAuth';
import { listCustomers, createCustomer } from '../services/customerService';
import { validEmail } from '../utils/validators';

export default function Customers() {
  const { isAdmin } = useAuth();
  const { data, loading, error, reload } = useFetch(listCustomers, []);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', phone: '' });
  const [err, setErr] = useState('');

  const save = async () => {
    if (!form.name || !validEmail(form.email)) return setErr('Name and a valid email are required');
    try {
      await createCustomer(form);
      setOpen(false); setForm({ name: '', email: '', phone: '' }); setErr(''); reload();
    } catch (e) { setErr(e.response?.data?.message || e.message); }
  };

  return (
    <>
      <div className="toolbar">
        <span className="muted">{isAdmin ? 'Admin' : 'Staff'} view</span>
        <button className="btn btn-primary" onClick={() => setOpen(true)}>+ New customer</button>
      </div>
      {error && <div className="alert">{error}</div>}
      <DataTable loading={loading} rows={data || []} columns={[
        { key: 'name', label: 'Name' }, { key: 'email', label: 'Email' }, { key: 'phone', label: 'Phone' },
      ]} />
      <Modal open={open} title="New customer" onClose={() => setOpen(false)}>
        {err && <div className="alert">{err}</div>}
        {['name', 'email', 'phone'].map((k) => (
          <label className="field" key={k}>{k[0].toUpperCase() + k.slice(1)}
            <input value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
          </label>
        ))}
        <button className="btn btn-primary" onClick={save}>Save</button>
      </Modal>
    </>
  );
}
