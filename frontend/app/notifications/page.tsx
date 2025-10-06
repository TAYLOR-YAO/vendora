import { useLocale } from 'next-intl';
import Link from 'next/link';
export default async function Page() {
  const locale = useLocale();

  return (<div>
    <h1>NOTIFICATIONS</h1>
    <p>Module shell. Backend API at {process.env.NEXT_PUBLIC_API_BASE}.</p>
    <ul>
      <li><Link href="/" locale={locale}>Home</Link></li>
    </ul>
  </div>);
}
