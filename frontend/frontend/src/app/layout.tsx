import type { Metadata } from "next";
import { Inter } from 'next/font/google';
import "./globals.css";
import { Providers } from "@/components/Providers";

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: "FileVault - Enterprise File Management",
  description: "Secure, multi-tenant file management platform with virus scanning, ML pipeline, and team collaboration.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <body className={`${inter.className} antialiased h-full`}>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
