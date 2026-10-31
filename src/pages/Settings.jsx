import { useState } from 'react';
import DataTable from '../components/DataTable';
import useFetch from '../hooks/useFetch';
import { listTaxes, createTax } from '../services/productService';
import { addStaff, listStaff } from '../services/authService';
import { passwordErrors, validEmail } from '../utils/validators';

export default function Settings() {
  const taxes = useFetch(listTaxes, []);
  const staff = useFetch(listStaff, []);
  const [tax, setTax] = useState({ name: '', rate: '' });
  const [member, setMember] = useState({ name: '', email: '', password: '' });
  const [msg, setMsg] = useState('');

  const saveTax = async () => {
    if (!tax.name || tax.rate === '') return setMsg('Tax name and rate are required');
    await createTax({ name: tax.name, rate: Number(tax.rate) });
    setTax({ name: '', rate: '' }); setMsg(''); taxes.reload();
  };

  const saveStaff = async () => {
    if (!member.name || !validEmail(member.email)) return setMsg('Staff name and valid email are required');
    if (passwordErrors(member.password).length) return setMsg('Staff password: ' + passwordErrors(member.password).join(', '));
    try { await addStaff(member); setMember({ name: '', email: '', password: '' }); setMsg(''); staff.reload(); }
    catch (e) { setMsg(e.response?.data?.message || e.message); }
  };

  return (
    <>
      {msg && <div className="alert">{msg}</div>}
      <div className="card">
        <h3>Tax rules</h3>
        <div className="toolbar">
          <input placeholder="Name (GST 18%)" value={tax.name} onChange={(e) => setTax({ ...tax, name: e.target.value })} />
          <input type="number" placeholder="Rate %" value={tax.rate} onChange={(e) => setTax({ ...tax, rate: e.target.value })} />
          <button className="btn btn-primary" onClick={saveTax}>Add tax</button>
        </div>
        <DataTable rows={taxes.data || []} loading={taxes.loading} columns={[
          { key: 'name', label: 'Name' }, { key: 'rate', label: 'Rate', render: (r) => `${r.rate}%` }]} />
      </div>

      <div className="card">
        <h3>Staff members (admin only)</h3>
        <div className="toolbar">
          <input placeholder="Name" value={member.name} onChange={(e) => setMember({ ...member, name: e.target.value })} />
          <input placeholder="Email" value={member.email} onChange={(e) => setMember({ ...member, email: e.target.value })} />
          <input type="password" placeholder="Temp password" value={member.password} onChange={(e) => setMember({ ...member, password: e.target.value })} />
          <button className="btn btn-primary" onClick={saveStaff}>Add staff</button>
        </div>
        <DataTable rows={staff.data || []} loading={staff.loading} columns={[
          { key: 'name', label: 'Name' }, { key: 'email', label: 'Email' }]} />
      </div>
    </>
  );
}
