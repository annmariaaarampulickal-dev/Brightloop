export const validEmail = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);

// Same rule as the backend: MORE than 8 characters, uppercase, lowercase, special character
export const passwordErrors = (pw = '') => {
  const errs = [];
  if (pw.length <= 8) errs.push('Must be more than 8 characters');
  if (new TextEncoder().encode(pw).length > 72) errs.push('Must be at most 72 bytes');
  if (!/[A-Z]/.test(pw)) errs.push('Needs an uppercase letter');
  if (!/[a-z]/.test(pw)) errs.push('Needs a lowercase letter');
  if (!/[^A-Za-z0-9]/.test(pw)) errs.push('Needs a special character');
  return errs;
};
