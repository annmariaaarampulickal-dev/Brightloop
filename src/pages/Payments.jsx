import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import useFetch from '../hooks/useFetch';
import useLookups from '../hooks/useLookups';
import { useAuth } from '../hooks/useAuth';
import { listPayments, recordPayment } from '../services/paymentService';
import { listInvoices } from '../services/invoiceService';
import { PAY_METHODS } from '../utils/constants';
import { money, fmtDate, today } from '../utils/format';
import { errMsg } from '../utils/errors';

const methodLabel = (v) => PAY_METHODS.find((m) => m.value === v)?.label || v;
const blank = { invoice_id: '', method: 'bank_transfer', amount: '', payment_date: today(), note: '' };

export default function Payments() {
  const { user } = useAuth();
  const isCustomer = user.role === 'customer';
  const location = useLocation();
  const L = useLookups();

  const [method, setMethod] = useState('');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [page, setPage] = useState(0);
  const pays = useFetch(() => listPayments({ method, date_from: from, date_to: to, page }), [method, from, to, page]);

  // Payments only carry invoice_id, so load invoices to show the invoice number and customer.
  const invs = useFetch(() => listInvoices({ pageSize: 199 }), []);
  const invById = Object.fromEntries((invs.data || []).map((i) => [i.id, i]));
  const outstanding = useFetch(() => (isCustomer ? Promise.resolve([]) : listInvoices({ outstanding: true, pageSize: 199 })), []);

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(blank);
  const [err, setErr] = useState('');
  const [msg, setMsg] = useState('');

  const pick = (id, list = outstanding.data || []) => {
    const inv = list.find((i) => i.id === Number(id));
    setForm((f) => ({ ...f, invoice_id: id, amount: inv ? inv.amount_due : '' }));
  };

  // arriving from the "Pay" button on an invoice row
  useEffect(() => {
    const id = location.state?.invoiceId;
    if (id && outstanding.data) { pick(String(id), outstanding.data); setOpen(true); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state, outstanding.data]);

  const save = async () => {
    const inv = (outstanding.data || []).find((i) => i.id === Number(form.invoice_id));
    if (!inv) return setErr('Pick an outstanding invoice');
    if (!(Number(form.amount) > 0)) return setErr('Enter an amount');
    if (Number(form.amount) > inv.amount_due) return setErr(`Amount exceeds what is still owed (${money(inv.amount_due)})`);
    try {
      await recordPayment({ invoice_id: inv.id, method: form.method, amount: Number(form.amount), payment_date: form.payment_date, note: form.note || null });
      setOpen(false); setErr(''); setForm(blank);
      setMsg(`Payment recorded for ${inv.number}`);
      pays.reload(); invs.reload(); outstanding.reload();
    } catch (e) { setErr(errMsg(e)); }
  };

  const change = (setter) => (e) => { setter(e.target.value); setPage(0); };

  return (
    <>
      <div className="toolbar">
        <select value={method} onChange={change(setMethod)}>
          <option value="">All methods</option>
          {PAY_METHODS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
        </select>
        <label className="inline">From <input type="date" value={from} onChange={change(setFrom)} /></label>
        <label className="inline">To <input type="date" value={to} onChange={change(setTo)} /></label>
        {!isCustomer && <button className="btn btn-primary" onClick={() => { setOpen(true); setErr(''); }}>+ Record payment</button>}
      </div>
      {msg && <div className="alert alert-info">{msg}</div>}
      {pays.error && <div className="alert">{pays.error}</div>}
      <DataTable loading={pays.loading} rows={pays.data || []} page={page} onPageChange={setPage} columns={[
        { key: 'payment_date', label: 'Date', render: (r) => fmtDate(r.payment_date) },
        { key: 'invoice', label: 'Invoice', render: (r) => invById[r.invoice_id]?.number || `#${r.invoice_id}` },
        ...(isCustomer ? [] : [{ key: 'customer', label: 'Customer', render: (r) => L.customersById[invById[r.invoice_id]?.customer_id]?.name || '-' }]),
        { key: 'method', label: 'Method', render: (r) => methodLabel(r.method) },
        { key: 'amount', label: 'Amount', render: (r) => money(r.amount) },
        { key: 'note', label: 'Note', render: (r) => r.note || '-' },
      ]} />

      <Modal open={open} title="Record payment" onClose={() => setOpen(false)}>
        {err && <div className="alert">{err}</div>}
        <label className="field">Invoice
          <select value={form.invoice_id} onChange={(e) => pick(e.target.value)}>
            <option value="">Select an outstanding invoice…</option>
            {(outstanding.data || []).map((i) => (
              <option key={i.id} value={i.id}>{i.number} · {L.customersById[i.customer_id]?.name || `#${i.customer_id}`} · {money(i.amount_due)} due</option>
            ))}
          </select>
        </label>
        <label className="field">Method
          <select value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value })}>{PAY_METHODS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}</select>
        </label>
        <label className="field">Amount<input type="number" min="0" step="0.01" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></label>
        <label className="field">Date<input type="date" value={form.payment_date} onChange={(e) => setForm({ ...form, payment_date: e.target.value })} /></label>
        <label className="field">Note<textarea value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} /></label>
        <button className="btn btn-primary" onClick={save}>Save payment</button>
      </Modal>
    </>
  );
}
