import { createContext, useContext, useState } from 'react';
import * as auth from '../services/authService';

const Ctx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem('user') || 'null'));

  const login = async (email, password) => {
    const u = await auth.login(email, password); // { id, email, name, role, is_active }
    localStorage.setItem('user', JSON.stringify(u));
    setUser(u);
    return u;
  };

  const logout = () => {
    localStorage.clear();
    setUser(null);
  };

  return <Ctx.Provider value={{ user, login, logout, isAdmin: user?.role === 'admin' }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
