// app/[locale]/page.tsx
import { notFound } from "next/navigation";

const SUPPORTED = ["en", "fr", "de"] as const;
type Locale = (typeof SUPPORTED)[number];

export default function LocaleHome({
  params,
}: {
  params: { locale: string };
}) {
  const locale = params.locale as Locale;
  if (!SUPPORTED.includes(locale as Locale)) notFound();

  return (
    <main style={{ padding: 24 }}>
      <h1>Vendora – {locale.toUpperCase()}</h1>
      <p>App is running. Locale segment: {locale}</p>
      <p>Backend: {process.env.NEXT_PUBLIC_API_BASE ?? "(not set)"}</p>
    </main>
  );
}
