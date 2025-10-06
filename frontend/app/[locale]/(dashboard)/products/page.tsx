// frontend/app/[locale]/products/page.tsx
'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/api'; // baseURL: '/api/b'

type ProductImage = {
  id: string;
  url: string;
  alt_text?: string;
};
type Variant = {
  id: string;
  sku: string;
  price: string;
  is_active: boolean;
};
type Product = {
  id: string;
  name: string;
  description?: string;
  images?: ProductImage[];
  variants?: Variant[];
};

export default function ProductsPage() {
  const [items, setItems] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        // Note: include the trailing slash
        const res = await api.get('/api/v1/commerce/product/');
        if (!alive) return;
        setItems(res.data ?? []);
      } catch (e: any) {
        console.error('Products fetch failed:', e);
        setErr(e?.response?.data?.detail || e?.message || 'Failed to load products');
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  if (loading) return <div className="p-6">Loading products…</div>;
  if (err) return <div className="p-6 text-red-600">{err}</div>;

  if (!items.length) {
    return <div className="p-6">No products yet.</div>;
  }

  return (
    <div className="max-w-5xl mx-auto p-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((p) => (
        <article key={p.id} className="border rounded-xl p-4">
          <h2 className="font-semibold text-lg mb-1">{p.name || 'Untitled product'}</h2>
          {p.images?.[0]?.url && (
            // If your API returns absolute URLs, <img> is fine; otherwise map to /public or prefix.
            <img
              src={p.images[0].url}
              alt={p.images[0].alt_text || p.name || 'Product image'}
              className="w-full h-40 object-cover rounded mb-3"
            />
          )}
          {p.description && <p className="text-sm text-gray-700 mb-3">{p.description}</p>}
          {!!p.variants?.length && (
            <div className="text-sm">
              <div className="font-medium mb-1">Variants</div>
              <ul className="list-disc ml-5">
                {p.variants.map((v) => (
                  <li key={v.id}>
                    {v.sku} — {v.price}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </article>
      ))}
    </div>
  );
}
