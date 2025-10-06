'use client';

import { useState } from 'react';
import { useAuth } from '@/contexts/auth-context'; // ← path matches the context below
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return; // guard against double submit
    setSubmitting(true);
    setErr(null);
    try {
      await login(email, password);
      // ✅ redirect only after success
      router.push('/en/products');
    } catch (ex: any) {
      console.log('ex:: ',ex)
      const detail =
        ex?.response?.data?.detail ||
        ex?.response?.data?.non_field_errors?.[0] ||
        ex?.message ||
        'Login failed';
      setErr(detail);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-sm mx-auto p-6">
      <h1 className="text-xl font-semibold mb-4">Sign in</h1>
      <form onSubmit={onSubmit} noValidate>
        <label className="block mb-2">
          <span className="block text-sm mb-1">Email</span>
          <input
            className="border rounded w-full p-2"
            type="email"
            inputMode="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={submitting}
          />
        </label>

        <label className="block mb-4">
          <span className="block text-sm mb-1">Password</span>
          <input
            className="border rounded w-full p-2"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={submitting}
          />
        </label>

        {err && <p className="text-red-600 mb-3">{err}</p>}

        <button
          type="submit"
          className="rounded px-4 py-2 border"
          aria-busy={submitting}
          disabled={submitting}
        >
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  );
}
