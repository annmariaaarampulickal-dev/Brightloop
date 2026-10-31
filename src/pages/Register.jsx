import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { register } from '../services/authService';
import { passwordErrors, validEmail } from '../utils/validators';
import { errMsg } from '../utils/errors';

export default function Register() {
  const nav = useNavigate();
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' });
  const [error, setError] = useState('');
  const pwErrs = passwordErrors(form.password);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return setError('Enter your name');
    if (!validEmail(form.email)) return setError('Enter a valid email');
    if (pwErrs.length) return setError('Password does not meet the rules');
    if (form.password !== form.confirm) return setError('Passwords do not match');
    try {
      await register(form.name.trim(), form.email, form.password);
      nav('/login', { state: { notice: 'Account created. You can sign in now.' } });
    } catch (err) {
      setError(errMsg(err)); // 409 = "An account with this email already exists"
    }
  };

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <h2>Create your account</h2>
        {error && <div className="alert">{error}</div>}
        <label className="field">Business / full name<input value={form.name} onChange={set('name')} /></label>
        <label className="field">Email<input type="email" value={form.email} onChange={set('email')} /></label>
        <label className="field">Password<input type="password" value={form.password} onChange={set('password')} /></label>
        {form.password && pwErrs.length > 0 && <ul className="rules">{pwErrs.map((r) => <li key={r}>{r}</li>)}</ul>}
        <label className="field">Confirm password<input type="password" value={form.confirm} onChange={set('confirm')} /></label>
        <button className="btn btn-primary block">Sign up</button>
        <div className="auth-links"><Link to="/login">Already have an account?</Link></div>
      </form>
    </div>
  );
}
