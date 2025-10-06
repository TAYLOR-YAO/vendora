'use client';

import { useAuth } from '@/hooks/use-auth';
import { useTranslations } from 'next-intl';

export default function DashboardPage() {
  const { user } = useAuth();
  const t = useTranslations('Dashboard');

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-700 dark:text-gray-200">
        {t('welcome')}, {user?.full_name || 'User'}!
      </h1>
      <p className="mt-2 text-gray-600 dark:text-gray-400">
        This is your main dashboard. Select an option from the sidebar to get started.
      </p>
    </div>
  );
}
