import { useState } from 'react';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import StatusBadge from '../components/StatusBadge';
import useFetch from '../hooks/useFetch';
import useLookups from '../hooks/useLookups';
import { useAuth } from '../hooks/useAuth';
import {
  listSubscriptions, createSubscription, createFromTemplate, transitionSubscription, renewSubscription,
} from '../services/subscriptionService';
import { SUB_STATUSES, NEXT_STATUS, TERMS_DAYS, termsLabel } from '../utils/constants';
import { money, fmtDate, today, cap, estimate } from '../utils/format';
import { errMsg } from '../utils/errors';

const blankForm = () => ({ templateId: '', customerId: '', planId: '', startDate: today(), expiryDate: '', terms: 30, lines: [] });
const blankLine = (productId) => ({ product_id: productId, variant_id: '', quantity: 1, tax_id: '' });
const ACTION_LABEL = { quotation: 'Make quotation', confirmed: 'Confirm', active: 'Activate', paused: 'Pause', closed: 'Close' };

export default function Subscriptions() {
  const { user } = useAuth();
  const isCustomer = user.role === 'customer';
  const L = useLookups();

  const [status, setStatus] = useState('');
  const [customerId, setCustomerId] = useState('');
  const [planId, setPlanId] = useState('');
  const [page, setPage] = useState(0);
  const subs = useFetch(
    () => listSubscriptions({ status, customer_id: customerId, plan_id: planId, page }),
    [status, customerId, planId, page]
  );

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(blankForm());
  const [formErr, setFormErr] = useState('');
  const [msg, setMsg] = useState({ type: '', text: '' });

  const template = L.templates.find((t) => t.id === Number(form.templateId));
  const plan = L.plansById[template ? template.plan_id : Number(form.planId)];

  // ---- row actions: which buttons to show depends on role and on what the plan allows ----
  const actionsFor = (s) => {
    const p = L.plansById[s.plan_id];
    const acts = [];
    if (isCustomer) {
      if (s.status === 'active' && p?.allow_pause) acts.push(['paused']);
      if (s.status === 'paused') acts.push(['active']);
    } else {
      (NEXT_STATUS[s.status] || []).forEach((to) => acts.push([to]));
    }
    if (['active', 'paused'].includes(s.status) && (!isCustomer || p?.allow_early_close || (s.expiry_date && s.expiry_date <= today()))) acts.push(['closed']);
    if (!isCustomer && ['draft', 'quotation', 'confirmed'].includes(s.status)) acts.push(['closed']);
    return acts;
  };

  const run = async (fn, ok) => {
    try { await fn(); setMsg({ type: 'info', text: ok }); subs.reload(); }
    catch (e) { setMsg({ type: 'error', text: errMsg(e) }); }
  };
  const move = (s, to) => {
    if (to === 'closed' && !window.confirm(`Close ${s.number}? This cannot be undone.`)) return;
    run(() => transitionSubscription(s.id, to), `${s.number} is now ${to}`);
  };

  // ---- create form ----
  const setLine = (i, patch) => setForm({ ...form, lines: form.lines.map((l, j) => (j === i ? { ...l, ...patch } : l)) });
  const lineInfo = (l) => {
    const p = L.productsById[Number(l.product_id)];
    const v = p?.variants.find((x) => x.id === Number(l.variant_id));
    const t = L.taxes.find((x) => x.id === Number(l.tax_id));
    return { p, unit_price: p ? p.sales_price + (v?.extra_price || 0) : 0, tax_rate: t?.rate_percent || 0 };
  };
  const totals = estimate(form.lines.map((l) => ({ quantity: Number(l.quantity) || 0, ...lineInfo(l) })));

  const save = async () => {
    if (!form.customerId) return setFormErr('Choose a customer');
    if (!template && (!form.planId || form.lines.length === 0)) return setFormErr('Choose a plan and add at least one line');
    const common = {
      customer_id: Number(form.customerId), start_date: form.startDate,
      expiry_date: form.expiryDate || null, payment_terms_days: Number(form.terms),
    };
    try {
      const sub = template
        ? await createFromTemplate(template.id, common)
        : await createSubscription({
            ...common, plan_id: Number(form.planId),
            lines: form.lines.map((l) => ({
              product_id: Number(l.product_id), variant_id: l.variant_id ? Number(l.variant_id) : null,
              quantity: Number(l.quantity), tax_id: l.tax_id ? Number(l.tax_id) : null,
            })),
          });
      setOpen(false); setForm(blankForm()); setFormErr('');
      setMsg({ type: 'info', text: `Created ${sub.number} as a draft` });
      subs.reload();
    } catch (e) { setFormErr(errMsg(e)); }
  };

  const columns = [
    { key: 'number', label: 'Number' },
    ...(isCustomer ? [] : [{ key: 'customer', label: 'Customer', render: (r) => L.customersById[r.customer_id]?.name || `#${r.customer_id}` }]),
    { key: 'plan', label: 'Plan', render: (r) => L.plansById[r.plan_id]?.name || `#${r.plan_id}` },
    { key: 'start_date', label: 'Start', render: (r) => fmtDate(r.start_date) },
    { key: 'expiry_date', label: 'Expiry', render: (r) => fmtDate(r.expiry_date) },
    { key: 'next', label: 'Next invoice', render: (r) => fmtDate(r.next_invoice_date) },
    { key: 'terms', label: 'Terms', render: (r) => termsLabel(r.payment_terms_days) },
    { key: 'total', label: 'Lines total', render: (r) => money(r.lines.reduce((s, l) => s + l.amount, 0)) },
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
    {
      key: 'act', label: '',
      render: (r) => (
        <div className="row-actions">
          {actionsFor(r).map(([to]) => (
            <button key={to} className="btn btn-ghost" onClick={() => move(r, to)}>
              {to === 'active' && r.status === 'paused' ? 'Resume' : ACTION_LABEL[to]}
            </button>
          ))}
          {r.status === 'active' && L.plansById[r.plan_id]?.allow_renew && (
            <button className="btn btn-ghost" onClick={() => run(() => renewSubscription(r.id), `${r.number} renewed`)}>Renew</button>
          )}
        </div>
      ),
    },
  ];

  const filterChange = (setter) => (e) => { setter(e.target.value); setPage(0); };

  return (
    <>
      <div className="toolbar">
        <select value={status} onChange={filterChange(setStatus)}>
          <option value="">All statuses</option>
          {SUB_STATUSES.map((s) => <option key={s} value={s}>{cap(s)}</option>)}
        </select>
        {!isCustomer && (
          <select value={customerId} onChange={filterChange(setCustomerId)}>
            <option value="">All customers</option>
            {L.customers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        )}
        <select value={planId} onChange={filterChange(setPlanId)}>
          <option value="">All plans</option>
          {L.plans.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        {!isCustomer && <button className="btn btn-primary" onClick={() => { setOpen(true); setFormErr(''); }}>+ New subscription</button>}
      </div>

      {msg.text && <div className={`alert ${msg.type === 'info' ? 'alert-info' : ''}`}>{msg.text}</div>}
      {subs.error && <div className="alert">{subs.error}</div>}
      <DataTable columns={columns} rows={subs.data || []} loading={subs.loading} page={page} onPageChange={setPage} />

      <Modal open={open} title="New subscription" onClose={() => setOpen(false)} wide>
        {formErr && <div className="alert">{formErr}</div>}
        <label className="field">Start from a quotation template (optional)
          <select value={form.templateId} onChange={(e) => setForm({ ...form, templateId: e.target.value })}>
            <option value="">— build from scratch —</option>
            {L.templates.map((t) => <option key={t.id} value={t.id}>{t.name} · valid {t.validity_days} days</option>)}
          </select>
        </label>
        <div className="grid2">
          <label className="field">Customer
            <select value={form.customerId} onChange={(e) => setForm({ ...form, customerId: e.target.value })}>
              <option value="">Select…</option>
              {L.customers.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.email})</option>)}
            </select>
          </label>
          <label className="field">Plan
            <select disabled={!!template} value={template ? template.plan_id : form.planId} onChange={(e) => setForm({ ...form, planId: e.target.value })}>
              <option value="">Select…</option>
              {L.plans.map((p) => <option key={p.id} value={p.id}>{p.name} · {p.billing_period} · min qty {p.min_quantity}</option>)}
            </select>
          </label>
          <label className="field">Start date
            <input type="date" value={form.startDate} onChange={(e) => setForm({ ...form, startDate: e.target.value })} />
          </label>
          <label className="field">Expiry date (blank = plan end date, else 1 year)
            <input type="date" value={form.expiryDate} onChange={(e) => setForm({ ...form, expiryDate: e.target.value })} />
          </label>
          <label className="field">Payment terms
            <select value={form.terms} onChange={(e) => setForm({ ...form, terms: e.target.value })}>
              {TERMS_DAYS.map((d) => <option key={d} value={d}>{termsLabel(d)}</option>)}
            </select>
          </label>
        </div>

        {template ? (
          <p className="muted">Lines come from the template ({template.lines.length} line{template.lines.length > 1 ? 's' : ''}). The quotation stays valid for {template.validity_days} days.</p>
        ) : (
          <>
            <h4>Lines {plan && <span className="muted small">(plan minimum quantity: {plan.min_quantity})</span>}</h4>
            <table className="table">
              <thead><tr><th>Product</th><th>Variant</th><th>Qty</th><th>Tax</th><th>Unit price</th><th>Amount</th><th></th></tr></thead>
              <tbody>
                {form.lines.map((l, i) => {
                  const info = lineInfo(l);
                  return (
                    <tr key={i}>
                      <td>
                        <select value={l.product_id} onChange={(e) => setLine(i, { product_id: e.target.value, variant_id: '' })}>
                          {L.products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                        </select>
                      </td>
                      <td>
                        <select value={l.variant_id} onChange={(e) => setLine(i, { variant_id: e.target.value })}>
                          <option value="">—</option>
                          {(info.p?.variants || []).map((v) => <option key={v.id} value={v.id}>{v.value} (+{v.extra_price})</option>)}
                        </select>
                      </td>
                      <td><input type="number" min="1" value={l.quantity} onChange={(e) => setLine(i, { quantity: e.target.value })} /></td>
                      <td>
                        <select value={l.tax_id} onChange={(e) => setLine(i, { tax_id: e.target.value })}>
                          <option value="">No tax</option>
                          {L.taxes.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                        </select>
                      </td>
                      <td>{money(info.unit_price)}</td>
                      <td>{money(info.unit_price * (Number(l.quantity) || 0))}</td>
                      <td><button className="icon-btn" onClick={() => setForm({ ...form, lines: form.lines.filter((_, j) => j !== i) })}>×</button></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <button className="btn btn-ghost" disabled={!L.products.length} onClick={() => setForm({ ...form, lines: [...form.lines, blankLine(L.products[0].id)] })}>+ Add line</button>
            <div className="totals">
              <div>Lines <b>{money(totals.subtotal)}</b></div>
              <div>Tax (est.) <b>{money(totals.tax)}</b></div>
              <div>Per period <b>{money(totals.total + (plan?.price || 0))}</b></div>
            </div>
            {plan && <p className="muted small">Includes the plan fee of {money(plan.price)} per {plan.billing_period} period (untaxed). Discounts are applied on the invoice.</p>}
          </>
        )}
        <button className="btn btn-primary" onClick={save}>Save as draft</button>
      </Modal>
    </>
  );
}
