import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'ترب مپ',
  description: 'مقایسه قیمت، استعلام موجودی، مسیریابی و خرید هوشمند در فروشگاه‌های تهران',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fa" dir="rtl">
      <head>
        <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <link rel="stylesheet" href="/css/style.css" />
      </head>
      <body>{children}</body>
    </html>
  );
}
