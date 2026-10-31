import { useState } from 'react';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import StatusBadge from '../components/StatusBadge';
import useFetch from '../hooks/useFetch';
import useDebounce from '../hooks/useDebounce';
import { useAuth } from '../hooks/useAuth';
import { listSubscriptions, createSubscription, advanceSubscription } from '../services/subscriptionService';
import { listCustomers } from '../services/customerService';
import { listPlans, listProducts, listTaxes, listTemplates } from '../services/productService';
import { SUB_FLOW, PAY_TERMS } from '../utils/constants';
import { money, fmtDate, today, addDays, calcTotals } from '../utils/format';

const blank = () => ({ customerId: '', planId: '', startDate: today(), expiryDate: addDays(today(), 365), paymentTerms: 'Net 15', lines: [] });

export default function Subscriptions() {
  const { user } = useAuth();
  const isCustomer = user.role === 'customer';
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const q = useDebounce(search);

  const subs = useFetch(() => listSubscriptions({ search: q, status, customerId: isCustomer ? user.customerId : undefined }), [q, status]);
  const lookups = useFetch(
    () => (isCustomer ? Promise.resolve(null) : Promise.all([listCustomers(), listPlans(), listProducts(), listTaxes(), listTemplates()])),
    []
  );
  const [customers = [], plans = [], products = [], taxes = [], templates = []] = lookups.data || [];

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(blank());
  const [error, setError] = useState('');

  const makeLine = (productId, qty = 1, taxId = taxes[0]?.id) => {
    const p = products.find((x) => x.id === Number(productId));
    const t = taxes.find((x) => x.id === Number(taxId));
    return { productId: p.id, product: p.name, qty, unitPrice: p.salesPrice, taxId: t?.id, taxRate: t?.rate || 0 };
  };

  const applyTemplate = (id) => {
    const t = templates.find((x) => x.id === Number(id));
    if (!t) return;
    setForm({ ...form, planId: t.planId, expiryDate: addDays(form.startDate, t.validDays), lines: t.lines.map((l) => makeLine(l.productId, l.qty)) });
  };

  const updateLine = (i, patch) => setForm({ ...form, lines: form.lines.map((l, j) => (j === i ? { ...l, ...patch } : l)) });

  const save = async () => {
    if (!form.customerId || !form.planId || form.lines.length === 0) return setError('Choose a customer, a plan and at least one line');
    await createSubscription(form);
    setOpen(false); setForm(blank()); setError(''); subs.reload();
  };

  const advance = async (id) => { await advanceSubscription(id); subs.reload(); };
  const totals = calcTotals(form.lines);

  const columns = [
    { key: 'number', label: 'Number' },
    { key: 'customer', label: 'Customer' },
    { key: 'plan', label: 'Plan' },
    { key: 'startDate', label: 'Start', render: (r) => fmtDate(r.startDate) },
    { key: 'expiryDate', label: 'Expiry', render: (r) => fmtDate(r.expiryDate) },
    { key: 'paymentTerms', label: 'Terms' },
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
  ];
  if (!isCustomer) {
    columns.push({
      key: 'act', label: '',
      render: (r) => {
        const next = SUB_FLOW[SUB_FLOW.indexOf(r.status) + 1];
        return next ? <button className="btn btn-ghost" onClick={() => advance(r.id)}>→ {next}</button> : null;
      },
    });
  }

  return (
    <>
      <div className="toolbar">
        <input placeholder="Search number or customer…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {SUB_FLOW.map((s) => <option key={s}>{s}</option>)}
        </select>
        {!isCustomer && <button className="btn btn-primary" onClick={() => setOpen(true)}>+ New subscription</button>}
      </div>

      {subs.error && <div className="alert">{subs.error}</div>}
      <DataTable columns={columns} rows={subs.data || []} loading={subs.loading} />

      <Modal open={open} title="New subscription" onClose={() => setOpen(false)} wide>
        {error && <div className="alert">{error}</div>}
        <label className="field">Start from quotation template
          <select defaultValue="" onChange={(e) => applyTemplate(e.target.value)}>
            <option value="">— none —</option>
            {templates.map((t) => <option key={t.id} value={t.id}>{t.name} (valid {t.validDays} days)</option>)}
          </select>
        </label>
        <div className="grid2">
          <label className="field">Customer
            <select value={form.customerId} onChange={(e) => setForm({ ...form, customerId: e.target.value })}>
              <option value="">Select…</option>
              {customers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </label>
          <label className="field">Plan
            <select value={form.planId} onChange={(e) => setForm({ ...form, planId: e.target.value })}>
              <option value="">Select…</option>
              {plans.map((p) => <option key={p.id} value={p.id}>{p.name} · {p.billing}</option>)}
            </select>
          </label>
          <label className="field">Start date
            <input type="date" value={form.startDate} onChange={(e) => setForm({ ...form, startDate: e.target.value })} />
          </label>
          <label className="field">Expiry date
            <input type="date" value={form.expiryDate} onChange={(e) => setForm({ ...form, expiryDate: e.target.value })} />
          </label>
          <label className="field">Payment terms
            <select value={form.paymentTerms} onChange={(e) => setForm({ ...form, paymentTerms: e.target.value })}>
              {PAY_TERMS.map((t) => <option key={t}>{t}</option>)}
            </select>
          </label>
        </div>

        <h4>Lines</h4>
        <table className="table">
          <thead><tr><th>Product</th><th>Qty</th><th>Unit price</th><th>Tax</th><th>Amount</th><th></th></tr></thead>
          <tbody>
            {form.lines.map((l, i) => (
              <tr key={i}>
                <td>
                  <select value={l.productId} onChange={(e) => updateLine(i, makeLine(e.target.value, l.qty, l.taxId))}>
                    {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </td>
                <td><input type="number" min="1" value={l.qty} onChange={(e) => updateLine(i, { qty: Number(e.target.value) })} /></td>
                <td>{money(l.unitPrice)}</td>
                <td>
                  <select value={l.taxId} onChange={(e) => { const t = taxes.find((x) => x.id === Number(e.target.value)); updateLine(i, { taxId: t.id, taxRate: t.rate }); }}>
                    {taxes.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                  </select>
                </td>
                <td>{money(l.qty * l.unitPrice)}</td>
                <td><button className="icon-btn" onClick={() => setForm({ ...form, lines: form.lines.filter((_, j) => j !== i) })}>×</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <button className="btn btn-ghost" onClick={() => setForm({ ...form, lines: [...form.lines, makeLine(products[0].id)] })}>+ Add line</button>

        <div className="totals">
          <div>Subtotal <b>{money(totals.subtotal)}</b></div>
          <div>Tax <b>{money(totals.tax)}</b></div>
          <div>Total <b>{money(totals.total)}</b></div>
        </div>
        <button className="btn btn-primary" onClick={save}>Save as draft</button>
      </Modal>
    </>
  );
}
