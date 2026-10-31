import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import useFetch from '../hooks/useFetch';
import { useAuth } from '../hooks/useAuth';
import { listPayments, recordPayment } from '../services/paymentService';
import { listInvoices } from '../services/invoiceService';
import { PAY_METHODS } from '../utils/constants';
import { money, fmtDate, today } from '../utils/format';

export default function Payments() {
  const { user } = useAuth();
  const isCustomer = user.role === 'customer';
  const location = useLocation();
  const cid = isCustomer ? user.customerId : undefined;
  const pays = useFetch(() => listPayments({ customerId: cid }), []);
  const invs = useFetch(() => (isCustomer ? Promise.resolve([]) : listInvoices({ status: 'Confirmed' })), []);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ invoiceId: '', method: 'Bank Transfer', amount: '', date: today(), note: '' });
  const [err, setErr] = useState('');

  // arrive from the "Pay" button on an invoice
  useEffect(() => {
    if (location.state?.invoiceId) { setForm((f) => ({ ...f, invoiceId: location.state.invoiceId })); setOpen(true); }
  }, [location.state]);

  const pickInvoice = (id) => {
    const inv = (invs.data || []).find((i) => i.id === Number(id));
    setForm({ ...form, invoiceId: id, amount: inv ? inv.total - inv.paid : '' });
  };

  const save = async () => {
    if (!form.invoiceId || !(Number(form.amount) > 0)) return setErr('Pick an invoice and enter an amount');
    try {
      await recordPayment(form);
      setOpen(false); setErr(''); pays.reload(); invs.reload();
    } catch (e) { setErr(e.response?.data?.message || e.message); }
  };

  return (
    <>
      <div className="toolbar">
        <span className="muted">{(pays.data || []).length} payments recorded</span>
        {!isCustomer && <button className="btn btn-primary" onClick={() => setOpen(true)}>+ Record payment</button>}
      </div>
      <DataTable loading={pays.loading} rows={pays.data || []} columns={[
        { key: 'date', label: 'Date', render: (r) => fmtDate(r.date) },
        { key: 'invoice', label: 'Invoice' }, { key: 'customer', label: 'Customer' },
        { key: 'method', label: 'Method' },
        { key: 'amount', label: 'Amount', render: (r) => money(r.amount) },
        { key: 'note', label: 'Note' },
      ]} />

      <Modal open={open} title="Record payment" onClose={() => setOpen(false)}>
        {err && <div className="alert">{err}</div>}
        <label className="field">Invoice
          <select value={form.invoiceId} onChange={(e) => pickInvoice(e.target.value)}>
            <option value="">Select outstanding invoice…</option>
            {(invs.data || []).map((i) => <option key={i.id} value={i.id}>{i.number} · {i.customer} · {money(i.total - i.paid)} due</option>)}
          </select>
        </label>
        <label className="field">Method
          <select value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value })}>{PAY_METHODS.map((m) => <option key={m}>{m}</option>)}</select>
        </label>
        <label className="field">Amount<input type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></label>
        <label className="field">Date<input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} /></label>
        <label className="field">Note<textarea value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} /></label>
        <button className="btn btn-primary" onClick={save}>Save payment</button>
      </Modal>
    </>
  );
}
