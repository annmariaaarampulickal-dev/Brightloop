export const SUB_FLOW = ['Draft', 'Quotation', 'Confirmed', 'Active', 'Closed'];
export const INVOICE_STATUS = ['Draft', 'Confirmed', 'Paid', 'Cancelled'];
export const BILLING = ['daily', 'weekly', 'monthly', 'yearly'];
export const PAY_METHODS = ['Bank Transfer', 'Card', 'UPI', 'Cash', 'Cheque'];
export const PAY_TERMS = ['Immediate', 'Net 15', 'Net 30', 'Net 60'];
export const termDays = (t) => (t === 'Immediate' ? 0 : parseInt(t.replace('Net ', ''), 10));
export const ROLES = { ADMIN: 'admin', STAFF: 'staff', CUSTOMER: 'customer' };
