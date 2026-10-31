import { useState } from 'react';
import DataTable from '../components/DataTable';
import useFetch from '../hooks/useFetch';
import { listTaxes, createTax, deactivateTax } from '../services/productService';
import { addStaff, listStaff } from '../services/authService';
import { passwordErrors, validEmail } from '../utils/validators';
import { errMsg } from '../utils/errors';

export default function Settings() {
  const taxes = useFetch(listTaxes, []);
  const staff = useFetch(listStaff, []);
  const [tax, setTax] = useState({ name: '', rate_percent: '' });
  const [member, setMember] = useState({ name: '', email: '', password: '' });
  const [msg, setMsg] = useState({ type: '', text: '' });

  const saveTax = async () => {
    if (!tax.name || tax.rate_percent === '') return setMsg({ type: 'error', text: 'Tax name and rate are required' });
    try {
      await createTax({ name: tax.name, rate_percent: Number(tax.rate_percent) });
      setTax({ name: '', rate_percent: '' }); setMsg({ type: '', text: '' }); taxes.reload();
    } catch (e) { setMsg({ type: 'error', text: errMsg(e) }); }
  };

  const removeTax = async (id) => {
    try { await deactivateTax(id); taxes.reload(); } catch (e) { setMsg({ type: 'error', text: errMsg(e) }); }
  };

  const saveStaff = async () => {
    if (!member.name || !validEmail(member.email)) return setMsg({ type: 'error', text: 'Staff name and a valid email are required' });
    const errs = passwordErrors(member.password);
    if (errs.length) return setMsg({ type: 'error', text: `Password: ${errs.join(', ')}` });
    try {
      await addStaff(member);
      setMember({ name: '', email: '', password: '' });
      setMsg({ type: 'info', text: 'Staff member added' }); staff.reload();
    } catch (e) { setMsg({ type: 'error', text: errMsg(e) }); }
  };

  return (
    <>
      {msg.text && <div className={`alert ${msg.type === 'info' ? 'alert-info' : ''}`}>{msg.text}</div>}
      <div className="card">
        <h3>Tax rules</h3>
        <div className="toolbar">
          <input placeholder="Name (GST 18%)" value={tax.name} onChange={(e) => setTax({ ...tax, name: e.target.value })} />
          <input type="number" min="0" max="100" placeholder="Rate %" value={tax.rate_percent} onChange={(e) => setTax({ ...tax, rate_percent: e.target.value })} />
          <button className="btn btn-primary" onClick={saveTax}>Add tax</button>
        </div>
        <DataTable rows={taxes.data || []} loading={taxes.loading} columns={[
          { key: 'name', label: 'Name' }, { key: 'rate_percent', label: 'Rate', render: (r) => `${r.rate_percent}%` },
          { key: 'act', label: '', render: (r) => <button className="btn btn-ghost" onClick={() => removeTax(r.id)}>Deactivate</button> },
        ]} />
        <p className="muted small">Taxes are deactivated, never deleted, so old invoices keep their history.</p>
      </div>

      <div className="card">
        <h3>Staff members</h3>
        <div className="toolbar">
          <input placeholder="Name" value={member.name} onChange={(e) => setMember({ ...member, name: e.target.value })} />
          <input placeholder="Email" value={member.email} onChange={(e) => setMember({ ...member, email: e.target.value })} />
          <input type="password" placeholder="Password" value={member.password} onChange={(e) => setMember({ ...member, password: e.target.value })} />
          <button className="btn btn-primary" onClick={saveStaff}>Add staff</button>
        </div>
        <DataTable rows={staff.data || []} loading={staff.loading} columns={[
          { key: 'name', label: 'Name' }, { key: 'email', label: 'Email' }]} />
      </div>
    </>
  );
}
