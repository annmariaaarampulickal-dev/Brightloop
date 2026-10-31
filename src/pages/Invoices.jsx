import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import StatusBadge from '../components/StatusBadge';
import useFetch from '../hooks/useFetch';
import useDebounce from '../hooks/useDebounce';
import { useAuth } from '../hooks/useAuth';
import { listInvoices, invoiceAction, generateDueInvoices, printInvoice } from '../services/invoiceService';
import { money, fmtDate, isOverdue } from '../utils/format';

export default function Invoices() {
  const { user } = useAuth();
  const nav = useNavigate();
  const isCustomer = user.role === 'customer';
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const q = useDebounce(search);
  const { data, loading, error, reload } = useFetch(
    () => listInvoices({ search: q, status, customerId: isCustomer ? user.customerId : undefined }), [q, status]);
  const [view, setView] = useState(null);
  const [msg, setMsg] = useState('');

  const act = async (id, action) => {
    if (action === 'print') return printInvoice(id);
    await invoiceAction(id, action);
    if (action === 'send') setMsg('Invoice sent to the customer');
    reload();
  };

  const runBilling = async () => {
    const r = await generateDueInvoices();
    setMsg(`Billing run complete: ${r.created} invoices created, ${r.skipped} skipped (already billed)`);
    reload();
  };

  const columns = [
    { key: 'number', label: 'Invoice', render: (r) => <button className="link-btn" onClick={() => setView(r)}>{r.number}</button> },
    { key: 'customer', label: 'Customer' },
    { key: 'date', label: 'Date', render: (r) => fmtDate(r.date) },
    { key: 'dueDate', label: 'Due', render: (r) => fmtDate(r.dueDate) },
    { key: 'total', label: 'Total', render: (r) => money(r.total) },
    { key: 'bal', label: 'Balance', render: (r) => money(r.total - r.paid) },
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={isOverdue(r) ? 'Overdue' : r.status} /> },
    {
      key: 'act', label: '',
      render: (r) => (
        <div className="row-actions">
          {!isCustomer && r.status === 'Draft' && <button className="btn btn-ghost" onClick={() => act(r.id, 'confirm')}>Confirm</button>}
          {!isCustomer && r.status !== 'Paid' && r.status !== 'Cancelled' && <button className="btn btn-ghost" onClick={() => act(r.id, 'cancel')}>Cancel</button>}
          {!isCustomer && r.status === 'Confirmed' && <button className="btn btn-ghost" onClick={() => act(r.id, 'send')}>Send</button>}
          {!isCustomer && r.status === 'Confirmed' && <button className="btn btn-ghost" onClick={() => nav('/app/payments', { state: { invoiceId: r.id } })}>Pay</button>}
          <button className="btn btn-ghost" onClick={() => act(r.id, 'print')}>Print</button>
        </div>
      ),
    },
  ];

  return (
    <>
      <div className="toolbar">
        <input placeholder="Search invoice or customer…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All</option>
          {['Draft', 'Confirmed', 'Paid', 'Cancelled', 'Overdue'].map((s) => <option key={s}>{s}</option>)}
        </select>
        {!isCustomer && <button className="btn btn-primary" onClick={runBilling}>Run billing</button>}
      </div>
      {msg && <div className="alert alert-info">{msg}</div>}
      {error && <div className="alert">{error}</div>}
      <DataTable columns={columns} rows={data || []} loading={loading} />

      <Modal open={!!view} title={view?.number} onClose={() => setView(null)} wide>
        {view && (
          <>
            <p><b>{view.customer}</b> · {fmtDate(view.date)} · due {fmtDate(view.dueDate)}</p>
            <table className="table">
              <thead><tr><th>Product</th><th>Qty</th><th>Unit price</th><th>Tax %</th><th>Amount</th></tr></thead>
              <tbody>{view.lines.map((l, i) => (
                <tr key={i}><td>{l.product}</td><td>{l.qty}</td><td>{money(l.unitPrice)}</td><td>{l.taxRate}%</td><td>{money(l.qty * l.unitPrice)}</td></tr>
              ))}</tbody>
            </table>
            <div className="totals">
              <div>Subtotal <b>{money(view.subtotal)}</b></div>
              {view.discount > 0 && <div>Discount <b>-{money(view.discount)}</b></div>}
              <div>Tax <b>{money(view.tax)}</b></div>
              <div>Total <b>{money(view.total)}</b></div>
              <div>Paid <b>{money(view.paid)}</b></div>
            </div>
          </>
        )}
      </Modal>
    </>
  );
}
