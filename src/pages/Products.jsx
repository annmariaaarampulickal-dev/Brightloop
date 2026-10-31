import { useState } from 'react';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import useFetch from '../hooks/useFetch';
import { useAuth } from '../hooks/useAuth';
import { listProducts, createProduct, listPlans, createPlan, listDiscounts, createDiscount } from '../services/productService';
import { BILLING } from '../utils/constants';
import { money, fmtDate, today, addDays } from '../utils/format';

const emptyProduct = { name: '', type: 'Software', salesPrice: '', costPrice: '', notes: '', variants: [] };
const emptyPlan = { name: '', price: '', billing: 'monthly', minQty: 1, startDate: today(), endDate: addDays(today(), 365), autoClose: false, closable: true, pausable: false, renewable: true };
const emptyDisc = { name: '', type: 'percent', value: '', minPurchase: 0, minQty: 1, startDate: today(), endDate: addDays(today(), 90), usageLimit: 100, appliesTo: 'subscription' };

export default function Products() {
  const { isAdmin } = useAuth(); // only admin can create products, plans and discounts
  const [tab, setTab] = useState('products');
  const products = useFetch(listProducts, []);
  const plans = useFetch(listPlans, []);
  const discounts = useFetch(listDiscounts, []);
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState({});
  const [err, setErr] = useState('');

  const openModal = (kind, init) => { setForm(init); setErr(''); setModal(kind); };
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });

  const save = async () => {
    try {
      if (modal === 'product') {
        if (!form.name || !form.salesPrice) return setErr('Name and sales price are required');
        await createProduct({ ...form, salesPrice: Number(form.salesPrice), costPrice: Number(form.costPrice || 0) });
        products.reload();
      } else if (modal === 'plan') {
        if (!form.name || !form.price) return setErr('Name and price are required');
        await createPlan({ ...form, price: Number(form.price), minQty: Number(form.minQty) });
        plans.reload();
      } else {
        if (!form.name || !form.value) return setErr('Name and value are required');
        await createDiscount({ ...form, value: Number(form.value), minPurchase: Number(form.minPurchase), minQty: Number(form.minQty), usageLimit: Number(form.usageLimit) });
        discounts.reload();
      }
      setModal(null);
    } catch (e) { setErr(e.response?.data?.message || e.message); }
  };

  const addVariant = () => setForm({ ...form, variants: [...form.variants, { attribute: 'Brand', value: '', extraPrice: 0 }] });
  const setVariant = (i, patch) => setForm({ ...form, variants: form.variants.map((v, j) => (j === i ? { ...v, ...patch } : v)) });

  const tabs = [['products', 'Products'], ['plans', 'Plans'], ['discounts', 'Discounts']];
  const addBtn = { products: ['product', emptyProduct, '+ Product'], plans: ['plan', emptyPlan, '+ Plan'], discounts: ['discount', emptyDisc, '+ Discount'] }[tab];

  return (
    <>
      <div className="toolbar">
        <div className="tabs">
          {tabs.map(([k, l]) => <button key={k} className={tab === k ? 'tab active' : 'tab'} onClick={() => setTab(k)}>{l}</button>)}
        </div>
        {isAdmin && <button className="btn btn-primary" onClick={() => openModal(...addBtn.slice(0, 2))}>{addBtn[2]}</button>}
      </div>

      {tab === 'products' && (
        <DataTable loading={products.loading} rows={products.data || []} columns={[
          { key: 'name', label: 'Name' }, { key: 'type', label: 'Type' },
          { key: 'salesPrice', label: 'Sales price', render: (r) => money(r.salesPrice) },
          { key: 'costPrice', label: 'Cost price', render: (r) => money(r.costPrice) },
          { key: 'variants', label: 'Variants', render: (r) => r.variants.map((v) => `${v.value} (+${v.extraPrice})`).join(', ') || '-' },
        ]} />
      )}
      {tab === 'plans' && (
        <DataTable loading={plans.loading} rows={plans.data || []} columns={[
          { key: 'name', label: 'Plan' }, { key: 'price', label: 'Price', render: (r) => money(r.price) },
          { key: 'billing', label: 'Billing' }, { key: 'minQty', label: 'Min qty' },
          { key: 'dates', label: 'Available', render: (r) => `${fmtDate(r.startDate)} → ${fmtDate(r.endDate)}` },
          { key: 'opts', label: 'Options', render: (r) => [r.autoClose && 'auto-close', r.closable && 'closable', r.pausable && 'pausable', r.renewable && 'renewable'].filter(Boolean).join(', ') },
        ]} />
      )}
      {tab === 'discounts' && (
        <DataTable loading={discounts.loading} rows={discounts.data || []} columns={[
          { key: 'name', label: 'Name' },
          { key: 'value', label: 'Value', render: (r) => (r.type === 'percent' ? `${r.value}%` : money(r.value)) },
          { key: 'appliesTo', label: 'Applies to' },
          { key: 'min', label: 'Minimum', render: (r) => `${money(r.minPurchase)} / ${r.minQty} qty` },
          { key: 'dates', label: 'Valid', render: (r) => `${fmtDate(r.startDate)} → ${fmtDate(r.endDate)}` },
          { key: 'use', label: 'Used', render: (r) => `${r.used} / ${r.usageLimit}` },
        ]} />
      )}

      <Modal open={modal === 'product'} title="New product" onClose={() => setModal(null)} wide>
        {err && <div className="alert">{err}</div>}
        <div className="grid2">
          <label className="field">Name<input value={form.name || ''} onChange={set('name')} /></label>
          <label className="field">Type<input value={form.type || ''} onChange={set('type')} /></label>
          <label className="field">Sales price<input type="number" value={form.salesPrice || ''} onChange={set('salesPrice')} /></label>
          <label className="field">Cost price<input type="number" value={form.costPrice || ''} onChange={set('costPrice')} /></label>
        </div>
        <label className="field">Notes<textarea value={form.notes || ''} onChange={set('notes')} /></label>
        <h4>Variants (e.g. brand adds to price)</h4>
        {(form.variants || []).map((v, i) => (
          <div className="grid3" key={i}>
            <input placeholder="Attribute" value={v.attribute} onChange={(e) => setVariant(i, { attribute: e.target.value })} />
            <input placeholder="Value (Odoo)" value={v.value} onChange={(e) => setVariant(i, { value: e.target.value })} />
            <input type="number" placeholder="Extra price" value={v.extraPrice} onChange={(e) => setVariant(i, { extraPrice: Number(e.target.value) })} />
          </div>
        ))}
        <button className="btn btn-ghost" onClick={addVariant}>+ Variant</button>
        <div><button className="btn btn-primary" onClick={save}>Save product</button></div>
      </Modal>

      <Modal open={modal === 'plan'} title="New plan" onClose={() => setModal(null)} wide>
        {err && <div className="alert">{err}</div>}
        <div className="grid2">
          <label className="field">Name<input value={form.name || ''} onChange={set('name')} /></label>
          <label className="field">Price<input type="number" value={form.price || ''} onChange={set('price')} /></label>
          <label className="field">Billing period
            <select value={form.billing || 'monthly'} onChange={set('billing')}>{BILLING.map((b) => <option key={b}>{b}</option>)}</select>
          </label>
          <label className="field">Minimum quantity<input type="number" min="1" value={form.minQty || 1} onChange={set('minQty')} /></label>
          <label className="field">Available from<input type="date" value={form.startDate || ''} onChange={set('startDate')} /></label>
          <label className="field">Available until<input type="date" value={form.endDate || ''} onChange={set('endDate')} /></label>
        </div>
        <div className="checks">
          {[['autoClose', 'Close automatically at end'], ['closable', 'Can be closed early'], ['pausable', 'Can be paused'], ['renewable', 'Can be renewed']].map(([k, l]) => (
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
            <select value={form.type || 'percent'} onChange={set('type')}><option value="percent">Percentage</option><option value="fixed">Fixed amount</option></select>
          </label>
          <label className="field">Value<input type="number" value={form.value || ''} onChange={set('value')} /></label>
          <label className="field">Applies to
            <select value={form.appliesTo || 'subscription'} onChange={set('appliesTo')}><option value="subscription">Whole subscription</option><option value="product">Specific products</option></select>
          </label>
          <label className="field">Minimum purchase<input type="number" value={form.minPurchase ?? 0} onChange={set('minPurchase')} /></label>
          <label className="field">Minimum quantity<input type="number" value={form.minQty ?? 1} onChange={set('minQty')} /></label>
          <label className="field">Start date<input type="date" value={form.startDate || ''} onChange={set('startDate')} /></label>
          <label className="field">End date<input type="date" value={form.endDate || ''} onChange={set('endDate')} /></label>
          <label className="field">Usage limit<input type="number" value={form.usageLimit ?? 100} onChange={set('usageLimit')} /></label>
        </div>
        <button className="btn btn-primary" onClick={save}>Save discount</button>
      </Modal>
    </>
  );
}
