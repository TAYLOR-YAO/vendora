'use client';

import { Link, usePathname } from '@/navigation';
import { Package, Home } from 'lucide-react';
import { useTranslations } from 'next-intl';

const links = [
  { href: '/dashboard', label: 'Dashboard', icon: Home },
  { href: '/dashboard/products', label: 'Products', icon: Package },
];

export function Sidebar() {
  const pathname = usePathname();
  const t = useTranslations('Dashboard');

  return (
    <aside className="z-20 hidden w-64 overflow-y-auto bg-white dark:bg-gray-800 md:block flex-shrink-0">
      <div className="py-4 text-gray-500 dark:text-gray-400">
        <a className="ml-6 text-lg font-bold text-gray-800 dark:text-gray-200" href="#">
          Vendora
        </a>
        <ul className="mt-6">
          {links.map((link) => (
            <li className="relative px-6 py-3" key={link.label}>
              {pathname === link.href && (
                <span
                  className="absolute inset-y-0 left-0 w-1 bg-purple-600 rounded-tr-lg rounded-br-lg"
                  aria-hidden="true"
                ></span>
              )}
              <Link
                href={link.href}
                className={`inline-flex items-center w-full text-sm font-semibold transition-colors duration-150 hover:text-gray-800 dark:hover:text-gray-200 ${
                  pathname === link.href ? 'text-gray-800 dark:text-gray-100' : ''
                }`}
              >
                <link.icon className="w-5 h-5" />
                <span className="ml-4">{link.label === 'Products' ? t('products') : link.label}</span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
