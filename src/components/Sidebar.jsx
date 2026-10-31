import { NavLink } from 'react-router-dom';

export default function Sidebar({ links }) {
  return (
    <aside className="sidebar">
      <div className="brand">◎ Brightloop</div>
      <nav>
        {links.map((l) => (
          <NavLink key={l.to} to={l.to} end={l.end} className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            <span>{l.icon}</span> {l.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
