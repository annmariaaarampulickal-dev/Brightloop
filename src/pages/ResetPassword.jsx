import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { resetPassword } from '../services/authService';
import { passwordErrors } from '../utils/validators';
import { errMsg } from '../utils/errors';

// The backend emails a link to  <FRONTEND_URL>/reset-password?token=...
export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const nav = useNavigate();
  const [pw, setPw] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const errs = passwordErrors(pw);

  const submit = async (e) => {
    e.preventDefault();
    if (!token) return setError('This link is missing its token. Request a new reset email.');
    if (errs.length) return setError('Password does not meet the rules');
    if (pw !== confirm) return setError('Passwords do not match');
    try {
      const r = await resetPassword(token, pw);
      nav('/login', { state: { notice: r.message } });
    } catch (err) { setError(errMsg(err)); }
  };

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <h2>Choose a new password</h2>
        {error && <div className="alert">{error}</div>}
        <label className="field">New password<input type="password" value={pw} onChange={(e) => setPw(e.target.value)} /></label>
        {pw && errs.length > 0 && <ul className="rules">{errs.map((r) => <li key={r}>{r}</li>)}</ul>}
        <label className="field">Confirm password<input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} /></label>
        <button className="btn btn-primary block">Update password</button>
        <div className="auth-links"><Link to="/login">Back to sign in</Link></div>
      </form>
    </div>
  );
}
