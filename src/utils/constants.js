export const PAGE_SIZE = 20;

export const ROLES = { ADMIN: 'admin', STAFF: 'staff', CUSTOMER: 'customer' };

export const BILLING = ['daily', 'weekly', 'monthly', 'yearly'];

// Backend values: cash | card | bank_transfer | upi | cheque | other
export const PAY_METHODS = [
  { value: 'bank_transfer', label: 'Bank transfer' },
  { value: 'upi', label: 'UPI' },
  { value: 'card', label: 'Card' },
  { value: 'cash', label: 'Cash' },
  { value: 'cheque', label: 'Cheque' },
  { value: 'other', label: 'Other' },
];

// Payment terms are stored as a number of days
export const TERMS_DAYS = [0, 15, 30, 60];
export const termsLabel = (d) => (d === 0 ? 'Immediate' : `Net ${d}`);

export const SUB_STATUSES = ['draft', 'quotation', 'confirmed', 'active', 'paused', 'closed'];
export const INVOICE_STATUSES = ['draft', 'confirmed', 'paid', 'cancelled'];

// Forward moves staff can make (mirrors TRANSITIONS in the backend); "closed" is offered separately.
export const NEXT_STATUS = {
  draft: ['quotation'],
  quotation: ['confirmed'],
  confirmed: ['active'],
  active: ['paused'],
  paused: ['active'],
  closed: [],
};
