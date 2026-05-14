import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import "@/styles/eleven-tokens.css";
import "@/styles/kbid-tokens.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "입찰 인사이트",
  description: "공공데이터 기반 입찰가 산정 및 사정률 분석 플랫폼",
};

// v6: ElevenLabs Refero 톤 — Inter 폰트 + eleven-app 클래스
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko" className={inter.variable}>
      <body className="eleven-app">{children}</body>
    </html>
  );
}
