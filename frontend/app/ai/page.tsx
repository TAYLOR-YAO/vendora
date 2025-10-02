import Link from 'next/link';
export default async function Page() {
  return (<div>
    <h1>AI</h1>
    <p>Module shell. Backend API at {process.env.NEXT_PUBLIC_API_BASE}.</p>
    <ul>
      <li><Link href="/">Home</Link></li>
    </ul>
  </div>);
}
