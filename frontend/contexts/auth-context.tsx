'use client';

import React, { createContext, useState, useEffect, useCallback, useContext } from 'react';
import { useRouter } from 'next/navigation';

type User = { user_id: string; full_name?: string };

type AuthContextType = {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const fetchMe = useCallback(async () => {
    try {
      const res = await fetch('/api/auth/me', { method: 'GET', headers: { accept: 'application/json' } });
      if (!res.ok) {
        setUser(null);
        return;
      }
      const data = await res.json();
      if (data?.authenticated) {
        setUser(data.user as User);
        // Optional silent refresh: if token expires soon, ping refresh
        const ttlMs = Number(data.ttlMs ?? 0);
        if (ttlMs > 0 && ttlMs < 60_000) {
          await fetch('/api/auth/refresh', { method: 'POST' });
          // re-fetch me after refresh
          const res2 = await fetch('/api/auth/me');
          if (res2.ok) {
            const data2 = await res2.json();
            if (data2?.authenticated) setUser(data2.user as User);
          }
        }
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    (async () => {
      await fetchMe();
      setIsLoading(false);
    })();
  }, [fetchMe]);

  const login = async (email: string, password: string) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'content-type': 'application/json', accept: 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const e = await res.json().catch(() => ({}));
      throw new Error(e?.detail || 'Login failed');
    }
    // read user from /me (cookies are now set)
    await fetchMe();
  };

  const logout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' });
    setUser(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
