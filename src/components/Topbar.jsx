import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function Topbar({ title }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  return (
    <header className="topbar">
      <h1>{title}</h1>
      <div className="topbar-user">
        <div>
          <strong>{user?.name}</strong>
          <div className="muted small">{user?.role}</div>
        </div>
        <button className="btn btn-ghost" onClick={() => { logout(); nav('/login'); }}>Logout</button>
      </div>
    </header>
  );
}
