import { useState } from 'react';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import useFetch from '../hooks/useFetch';
import { useAuth } from '../hooks/useAuth';
import {
  listProducts, createProduct, listPlans, createPlan, updatePlan, listDiscounts, createDiscount, updateDiscount,
} from '../services/productService';
import { listSubscriptionsForPicker } from '../services/subscriptionService';
import { BILLING } from '../utils/constants';
import { money, fmtDate, today, addDays, cap } from '../utils/format';
import { errMsg } from '../utils/errors';

const emptyProduct = { name: '', type: 'software', sales_price: '', cost_price: '', notes: '', variants: [] };
const emptyPlan = { name: '', price: '', billing_period: 'monthly', min_quantity: 1, start_date: '', end_date: '', auto_close: false, allow_early_close: true, allow_pause: true, allow_renew: true };
const emptyDisc = { name: '', kind: 'percent', value: '', min_purchase: 0, min_quantity: 0, start_date: today(), end_date: addDays(today(), 90), usage_limit: '', scope: 'all', product_id: '', subscription_id: '' };

export default function Products() {
  const { isAdmin } = useAuth(); // only the admin creates products, plans and discounts
  const [tab, setTab] = useState('products');
  const products = useFetch(listProducts, []);
  const plans = useFetch(listPlans, []);
  const discounts = useFetch(listDiscounts, []);
  const subs = useFetch(() => (isAdmin ? listSubscriptionsForPicker() : Promise.resolve([])), [isAdmin]);
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState({});
  const [err, setErr] = useState('');
  const [note, setNote] = useState('');

  const openModal = (kind, init) => { setForm(init); setErr(''); setModal(kind); };
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });
  const productName = (id) => (products.data || []).find((p) => p.id === id)?.name || `#${id}`;
  const subNumber = (id) => (subs.data || []).find((s) => s.id === id)?.number || `#${id}`;
  const num = (v) => (v === '' || v == null ? null : Number(v));

  const save = async () => {
    try {
      if (modal === 'product') {
        if (!form.name || form.sales_price === '') return setErr('Name and sales price are required');
        await createProduct({
          name: form.name, type: form.type || 'software', sales_price: Number(form.sales_price),
          cost_price: Number(form.cost_price || 0), notes: form.notes || null,
          variants: form.variants.filter((v) => v.value).map((v) => ({ ...v, extra_price: Number(v.extra_price || 0) })),
        });
        products.reload();
      } else if (modal === 'plan') {
        if (!form.name || form.price === '') return setErr('Name and price are required');
        await createPlan({
          ...form, price: Number(form.price), min_quantity: Number(form.min_quantity || 1),
          start_date: form.start_date || null, end_date: form.end_date || null,
        });
        plans.reload();
      } else {
        if (!form.name || form.value === '') return setErr('Name and value are required');
        await createDiscount({
          name: form.name, kind: form.kind, value: Number(form.value),
          min_purchase: Number(form.min_purchase || 0), min_quantity: Number(form.min_quantity || 0),
          start_date: form.start_date || null, end_date: form.end_date || null, usage_limit: num(form.usage_limit),
          product_id: form.scope === 'product' ? num(form.product_id) : null,
          subscription_id: form.scope === 'subscription' ? num(form.subscription_id) : null,
        });
        discounts.reload();
      }
      setModal(null);
    } catch (e) { setErr(errMsg(e)); }
  };

  const deactivate = async (fn, reload) => {
    try { await fn(); reload(); setNote(''); } catch (e) { setNote(errMsg(e)); }
  };

  const addVariant = () => setForm({ ...form, variants: [...form.variants, { attribute: 'Brand', value: '', extra_price: 0 }] });
  const setVariant = (i, patch) => setForm({ ...form, variants: form.variants.map((v, j) => (j === i ? { ...v, ...patch } : v)) });

  const tabs = [['products', 'Products'], ['plans', 'Plans'], ['discounts', 'Discounts']];
  const addBtn = { products: ['product', emptyProduct, '+ Product'], plans: ['plan', emptyPlan, '+ Plan'], discounts: ['discount', emptyDisc, '+ Discount'] }[tab];

  return (
    <>
      <div className="toolbar">
        <div className="tabs">
          {tabs.map(([k, l]) => <button key={k} className={tab === k ? 'tab active' : 'tab'} onClick={() => setTab(k)}>{l}</button>)}
        </div>
        {isAdmin ? <button className="btn btn-primary" onClick={() => openModal(addBtn[0], addBtn[1])}>{addBtn[2]}</button>
          : <span className="muted">Read-only for staff</span>}
      </div>
      {note && <div className="alert">{note}</div>}

      {tab === 'products' && (
        <DataTable loading={products.loading} rows={products.data || []} columns={[
          { key: 'name', label: 'Name' }, { key: 'type', label: 'Type', render: (r) => cap(r.type) },
          { key: 'sales_price', label: 'Sales price', render: (r) => money(r.sales_price) },
          { key: 'cost_price', label: 'Cost price', render: (r) => money(r.cost_price) },
          { key: 'variants', label: 'Variants', render: (r) => r.variants.map((v) => `${v.value} (+${v.extra_price})`).join(', ') || '-' },
          { key: 'notes', label: 'Notes', render: (r) => r.notes || '-' },
        ]} />
      )}
      {tab === 'plans' && (
        <DataTable loading={plans.loading} rows={plans.data || []} columns={[
          { key: 'name', label: 'Plan' }, { key: 'price', label: 'Price', render: (r) => money(r.price) },
          { key: 'billing_period', label: 'Billing', render: (r) => cap(r.billing_period) },
          { key: 'min_quantity', label: 'Min qty' },
          { key: 'dates', label: 'Available', render: (r) => `${r.start_date ? fmtDate(r.start_date) : 'any time'} → ${r.end_date ? fmtDate(r.end_date) : 'open'}` },
          { key: 'opts', label: 'Rules', render: (r) => [r.auto_close && 'auto-close', r.allow_early_close && 'early close', r.allow_pause && 'pause', r.allow_renew && 'renew'].filter(Boolean).join(', ') || '-' },
          ...(isAdmin ? [{ key: 'act', label: '', render: (r) => <button className="btn btn-ghost" onClick={() => deactivate(() => updatePlan(r.id, { is_active: false }), plans.reload)}>Deactivate</button> }] : []),
        ]} />
      )}
      {tab === 'discounts' && (
        <DataTable loading={discounts.loading} rows={discounts.data || []} columns={[
          { key: 'name', label: 'Name' },
          { key: 'value', label: 'Value', render: (r) => (r.kind === 'percent' ? `${r.value}%` : money(r.value)) },
          { key: 'scope', label: 'Applies to', render: (r) => (r.product_id ? `Product: ${productName(r.product_id)}` : r.subscription_id ? `Subscription ${subNumber(r.subscription_id)}` : 'Every subscription') },
          { key: 'min', label: 'Minimum', render: (r) => `${money(r.min_purchase)} / ${r.min_quantity} qty` },
          { key: 'dates', label: 'Valid', render: (r) => `${r.start_date ? fmtDate(r.start_date) : 'now'} → ${r.end_date ? fmtDate(r.end_date) : 'open'}` },
          { key: 'use', label: 'Used', render: (r) => `${r.times_used} / ${r.usage_limit ?? '∞'}` },
          ...(isAdmin ? [{ key: 'act', label: '', render: (r) => <button className="btn btn-ghost" onClick={() => deactivate(() => updateDiscount(r.id, { is_active: false }), discounts.reload)}>Deactivate</button> }] : []),
        ]} />
      )}

      <Modal open={modal === 'product'} title="New product" onClose={() => setModal(null)} wide>
        {err && <div className="alert">{err}</div>}
        <div className="grid2">
          <label className="field">Name<input value={form.name || ''} onChange={set('name')} /></label>
          <label className="field">Type<input value={form.type || ''} onChange={set('type')} /></label>
          <label className="field">Sales price<input type="number" min="0" value={form.sales_price ?? ''} onChange={set('sales_price')} /></label>
          <label className="field">Cost price<input type="number" min="0" value={form.cost_price ?? ''} onChange={set('cost_price')} /></label>
        </div>
        <label className="field">Notes<textarea value={form.notes || ''} onChange={set('notes')} /></label>
        <h4>Variants (e.g. choosing the Odoo brand adds 560)</h4>
        {(form.variants || []).map((v, i) => (
          <div className="grid3" key={i}>
            <input placeholder="Attribute (Brand)" value={v.attribute} onChange={(e) => setVariant(i, { attribute: e.target.value })} />
            <input placeholder="Value (Odoo)" value={v.value} onChange={(e) => setVariant(i, { value: e.target.value })} />
            <input type="number" placeholder="Extra price" value={v.extra_price} onChange={(e) => setVariant(i, { extra_price: e.target.value })} />
          </div>
        ))}
        <button className="btn btn-ghost" onClick={addVariant}>+ Variant</button>
        <div><button className="btn btn-primary" onClick={save}>Save product</button></div>
      </Modal>

      <Modal open={modal === 'plan'} title="New plan" onClose={() => setModal(null)} wide>
        {err && <div className="alert">{err}</div>}
        <div className="grid2">
          <label className="field">Name<input value={form.name || ''} onChange={set('name')} /></label>
          <label className="field">Price per period<input type="number" min="0" value={form.price ?? ''} onChange={set('price')} /></label>
          <label className="field">Billing period
            <select value={form.billing_period || 'monthly'} onChange={set('billing_period')}>{BILLING.map((b) => <option key={b} value={b}>{cap(b)}</option>)}</select>
          </label>
          <label className="field">Minimum quantity<input type="number" min="1" value={form.min_quantity ?? 1} onChange={set('min_quantity')} /></label>
          <label className="field">Available from<input type="date" value={form.start_date || ''} onChange={set('start_date')} /></label>
          <label className="field">Available until<input type="date" value={form.end_date || ''} onChange={set('end_date')} /></label>
        </div>
        <div className="checks">
          {[['auto_close', 'Close automatically when it ends'], ['allow_early_close', 'Can be closed early'], ['allow_pause', 'Can be paused'], ['allow_renew', 'Can be renewed']].map(([k, l]) => (
            <label key={k}><input type="checkbox" checked={!!form[k]} onChange={set(k)} /> {l}</label>
          ))}
        </div>
        <button className="btn btn-primary" onClick={save}>Save plan</button>
      </Modal>

      <Modal open={modal === 'discount'} title="New discount rule" onClose={() => setModal(null)} wide>
        {err && <div className="alert">{err}</div>}
        <div className="grid2">
          <label className="field">Name<input value={form.name || ''} onChange={set('name')} /></label>
          <label className="field">Type
            <select value={form.kind || 'percent'} onChange={set('kind')}><option value="percent">Percentage</option><option value="fixed">Fixed amount</option></select>
          </label>
          <label className="field">Value<input type="number" min="0" value={form.value ?? ''} onChange={set('value')} /></label>
          <label className="field">Applies to
            <select value={form.scope || 'all'} onChange={set('scope')}>
              <option value="all">Every subscription</option><option value="product">A specific product</option><option value="subscription">One subscription</option>
            </select>
          </label>
          {form.scope === 'product' && (
            <label className="field">Product
              <select value={form.product_id} onChange={set('product_id')}><option value="">Select…</option>{(products.data || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select>
            </label>
          )}
          {form.scope === 'subscription' && (
            <label className="field">Subscription
              <select value={form.subscription_id} onChange={set('subscription_id')}><option value="">Select…</option>{(subs.data || []).map((s) => <option key={s.id} value={s.id}>{s.number}</option>)}</select>
            </label>
          )}
          <label className="field">Minimum purchase<input type="number" min="0" value={form.min_purchase ?? 0} onChange={set('min_purchase')} /></label>
          <label className="field">Minimum quantity<input type="number" min="0" value={form.min_quantity ?? 0} onChange={set('min_quantity')} /></label>
          <label className="field">Start date<input type="date" value={form.start_date || ''} onChange={set('start_date')} /></label>
          <label className="field">End date<input type="date" value={form.end_date || ''} onChange={set('end_date')} /></label>
          <label className="field">Usage limit (blank = unlimited)<input type="number" min="1" value={form.usage_limit ?? ''} onChange={set('usage_limit')} /></label>
        </div>
        <button className="btn btn-primary" onClick={save}>Save discount</button>
      </Modal>
    </>
  );
}
