import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Career Intelligence AI - Discover Your Perfect Career Path",
  description:
    "AI-powered career intelligence platform that analyzes your resume, assesses skill gaps, simulates career pivots, and builds personalized learning roadmaps.",
  keywords: [
    "AI career intelligence",
    "resume analyzer",
    "skill gap analysis",
    "career roadmap",
    "career simulation",
  ],
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-w-[320px] bg-[#f8f9fb] text-[#1f2328] antialiased">
        {children}
      </body>
    </html>
  );
}
