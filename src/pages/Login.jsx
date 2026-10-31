import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { forgotPassword } from '../services/authService';
import { validEmail } from '../utils/validators';
import { errMsg } from '../utils/errors';
import Modal from '../components/Modal';

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [forgot, setForgot] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetMsg, setResetMsg] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    if (!validEmail(form.email)) return setError('Enter a valid email');
    setBusy(true);
    try {
      const u = await login(form.email, form.password);
      nav(u.role === 'customer' ? '/portal' : '/app');
    } catch (err) {
      setError(errMsg(err));
    } finally { setBusy(false); }
  };

  const sendReset = async () => {
    if (!validEmail(resetEmail)) return setResetMsg('Enter a valid email');
    try {
      const r = await forgotPassword(resetEmail);
      setResetMsg(r.message);
    } catch (e) { setResetMsg(errMsg(e)); }
  };

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <h2>Welcome back</h2>
        <p className="muted">Sign in to Brightloop</p>
        {location.state?.notice && <div className="alert alert-info">{location.state.notice}</div>}
        {error && <div className="alert">{error}</div>}
        <label className="field">Email
          <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </label>
        <label className="field">Password
          <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </label>
        <button className="btn btn-primary block" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
        <div className="auth-links">
          <button type="button" className="link-btn" onClick={() => { setForgot(true); setResetMsg(''); }}>Forgot password?</button>
          <Link to="/register">Create account</Link>
        </div>
        <p className="muted small">Demo (after <code>python -m app.seed</code>): admin@brightloop.com / Admin@12345 · staff@brightloop.com / Demo@12345 · acme@example.com / Demo@12345</p>
      </form>

      <Modal open={forgot} title="Reset password" onClose={() => setForgot(false)}>
        <label className="field">Registered email
          <input type="email" value={resetEmail} onChange={(e) => setResetEmail(e.target.value)} />
        </label>
        {resetMsg && <div className="alert alert-info">{resetMsg}</div>}
        <button className="btn btn-primary" onClick={sendReset}>Send reset link</button>
      </Modal>
    </div>
  );
}
