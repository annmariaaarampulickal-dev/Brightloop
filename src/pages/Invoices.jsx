import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import StatusBadge from '../components/StatusBadge';
import useFetch from '../hooks/useFetch';
import useLookups from '../hooks/useLookups';
import { useAuth } from '../hooks/useAuth';
import { listInvoices, invoiceAction, runBilling, printInvoice } from '../services/invoiceService';
import { INVOICE_STATUSES } from '../utils/constants';
import { money, fmtDate, cap } from '../utils/format';
import { errMsg } from '../utils/errors';

// The quick filter maps to the backend's query flags
const FILTERS = [
  ...INVOICE_STATUSES.map((s) => [s, { status: s }]),
  ['outstanding', { outstanding: true }],
  ['overdue', { overdue: true }],
];

export default function Invoices() {
  const { user } = useAuth();
  const nav = useNavigate();
  const isCustomer = user.role === 'customer';
  const L = useLookups();

  const [filter, setFilter] = useState('');
  const [customerId, setCustomerId] = useState('');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [page, setPage] = useState(0);
  const params = { ...(FILTERS.find(([k]) => k === filter)?.[1] || {}), customer_id: customerId, issued_from: from, issued_to: to, page };
  const { data, loading, error, reload } = useFetch(() => listInvoices(params), [filter, customerId, from, to, page]);

  const [view, setView] = useState(null);
  const [msg, setMsg] = useState({ type: '', text: '' });
  const [autoConfirm, setAutoConfirm] = useState(false);
  const [busy, setBusy] = useState(false);

  const act = async (inv, action) => {
    try {
      if (action === 'print') return await printInvoice(inv.id);
      await invoiceAction(inv.id, action);
      setMsg({ type: 'info', text: `${inv.number}: ${action} done` });
      reload();
    } catch (e) { setMsg({ type: 'error', text: errMsg(e) }); }
  };

  const bill = async () => {
    setBusy(true);
    try {
      const r = await runBilling(autoConfirm);
      setMsg({ type: 'info', text: `Billing run for ${fmtDate(r.as_of)}: ${r.created} invoices created, ${r.skipped_already_billed} skipped (already billed), ${r.closed_subscriptions} subscriptions closed.` });
      setPage(0); reload();
    } catch (e) { setMsg({ type: 'error', text: errMsg(e) }); }
    finally { setBusy(false); }
  };

  const change = (setter) => (e) => { setter(e.target.value); setPage(0); };

  const columns = [
    { key: 'number', label: 'Invoice', render: (r) => <button className="link-btn" onClick={() => setView(r)}>{r.number}</button> },
    ...(isCustomer ? [] : [{ key: 'customer', label: 'Customer', render: (r) => L.customersById[r.customer_id]?.name || `#${r.customer_id}` }]),
    { key: 'period', label: 'Period', render: (r) => `${fmtDate(r.period_start)} – ${fmtDate(r.period_end)}` },
    { key: 'due_date', label: 'Due', render: (r) => fmtDate(r.due_date) },
    { key: 'total', label: 'Total', render: (r) => money(r.total) },
    { key: 'amount_due', label: 'Amount due', render: (r) => money(r.amount_due) },
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.is_overdue ? 'overdue' : r.status} /> },
    {
      key: 'act', label: '',
      render: (r) => (
        <div className="row-actions">
          {!isCustomer && r.status === 'draft' && <button className="btn btn-ghost" onClick={() => act(r, 'confirm')}>Confirm</button>}
          {!isCustomer && ['draft', 'confirmed'].includes(r.status) && r.amount_paid === 0 && <button className="btn btn-ghost" onClick={() => act(r, 'cancel')}>Cancel</button>}
          {!isCustomer && ['confirmed', 'paid'].includes(r.status) && <button className="btn btn-ghost" onClick={() => act(r, 'send')}>Send</button>}
          {!isCustomer && r.status === 'confirmed' && <button className="btn btn-ghost" onClick={() => nav('/app/payments', { state: { invoiceId: r.id } })}>Pay</button>}
          <button className="btn btn-ghost" onClick={() => act(r, 'print')}>Print</button>
        </div>
      ),
    },
  ];

  return (
    <>
      <div className="toolbar">
        <select value={filter} onChange={change(setFilter)}>
          <option value="">All invoices</option>
          {FILTERS.map(([k]) => <option key={k} value={k}>{cap(k)}</option>)}
        </select>
        {!isCustomer && (
          <select value={customerId} onChange={change(setCustomerId)}>
            <option value="">All customers</option>
            {L.customers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        )}
        <label className="inline">From <input type="date" value={from} onChange={change(setFrom)} /></label>
        <label className="inline">To <input type="date" value={to} onChange={change(setTo)} /></label>
        {!isCustomer && (
          <>
            <label className="inline"><input type="checkbox" checked={autoConfirm} onChange={(e) => setAutoConfirm(e.target.checked)} /> Auto-confirm</label>
            <button className="btn btn-primary" onClick={bill} disabled={busy}>{busy ? 'Billing…' : 'Run billing'}</button>
          </>
        )}
      </div>
      {msg.text && <div className={`alert ${msg.type === 'info' ? 'alert-info' : ''}`}>{msg.text}</div>}
      {error && <div className="alert">{error}</div>}
      <DataTable columns={columns} rows={data || []} loading={loading} page={page} onPageChange={setPage} />

      <Modal open={!!view} title={view ? `Invoice ${view.number}` : ''} onClose={() => setView(null)} wide>
        {view && (
          <>
            <p>
              <b>{L.customersById[view.customer_id]?.name || `Customer #${view.customer_id}`}</b> · issued {fmtDate(view.issue_date)} · due {fmtDate(view.due_date)}<br />
              <span className="muted">Period {fmtDate(view.period_start)} – {fmtDate(view.period_end)}</span> <StatusBadge status={view.is_overdue ? 'overdue' : view.status} />
            </p>
            <table className="table">
              <thead><tr><th>Description</th><th>Qty</th><th>Unit price</th><th>Tax</th><th>Amount</th></tr></thead>
              <tbody>{view.lines.map((l) => (
                <tr key={l.id}><td>{l.description}</td><td>{l.quantity}</td><td>{money(l.unit_price)}</td><td>{l.tax_rate}%</td><td>{money(l.amount)}</td></tr>
              ))}</tbody>
            </table>
            <div className="totals">
              <div>Subtotal <b>{money(view.subtotal)}</b></div>
              {view.discount_total > 0 && <div>Discount <b>-{money(view.discount_total)}</b></div>}
              <div>Tax <b>{money(view.tax_total)}</b></div>
              <div>Total <b>{money(view.total)}</b></div>
              <div>Paid <b>{money(view.amount_paid)}</b></div>
              <div>Due <b>{money(view.amount_due)}</b></div>
            </div>
          </>
        )}
      </Modal>
    </>
  );
}
