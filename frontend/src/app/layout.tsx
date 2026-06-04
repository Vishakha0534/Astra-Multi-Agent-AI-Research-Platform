import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "ASTRA AI | Multi-Agent Research Platform",
  description: "Advanced AI reliability and research orchestration",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} overflow-hidden`}>
        <div className="flex h-screen bg-background text-foreground">
          <Sidebar />
          <main className="flex-1 overflow-y-auto relative">
            {children}
            {/* Ambient Background Glows */}
            <div className="fixed top-[-10%] right-[-10%] w-[40%] h-[40%] bg-primary/5 rounded-full blur-[120px] pointer-events-none" />
            <div className="fixed bottom-[-10%] left-[-10%] w-[30%] h-[30%] bg-blue-500/5 rounded-full blur-[100px] pointer-events-none" />
          </main>
        </div>
      </body>
    </html>
  );
}
