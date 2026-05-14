import type { Metadata } from "next";
import "./globals.css";
import "@/styles/kbid-tokens.css";

export const metadata: Metadata = {
  title: "입찰 인사이트 - 조달 입찰 분석 플랫폼 (KBID 동등 UI)",
  description: "공공데이터 기반 입찰가 산정 및 사정률 분석 웹 플랫폼",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="kbid-app">
        {children}
      </body>
    </html>
  );
}
