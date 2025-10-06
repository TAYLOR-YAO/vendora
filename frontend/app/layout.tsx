// app/layout.tsx
import { ReactNode } from 'react';
import { notFound } from 'next/navigation';
import { getMessages, getLocale } from 'next-intl/server';
import { Providers } from '@/components/providers';
import { locales } from '@/i18n';
import './globals.css';

export const metadata = {
  title: 'Vendora',
};

type Props = {
  children: ReactNode;
};

export default async function RootLayout({ children }: Props) {
  const locale = await getLocale();
  if (!locales.includes(locale)) notFound();
  const messages = await getMessages({ locale });

  return (
    <html lang={locale}>
      <body>
        <Providers locale={locale} messages={messages}>
          {children}
        </Providers>
      </body>
    </html>
  );
}
