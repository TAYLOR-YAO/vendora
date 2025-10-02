export const metadata = { title: "Vendora" };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (<html lang="en"><body style={{fontFamily:"system-ui"}}><header style={{padding:12,borderBottom:"1px solid #eee"}}><b>Vendora</b></header><main style={{padding:16}}>{children}</main></body></html>);
}
