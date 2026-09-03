import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://last-gate-prototype.tencekdw.chatgpt.site"),
  title: "마지막 관문 · 덱빌딩 로그라이크",
  description: "카드를 뽑고 덱을 성장시키며 다섯 번의 전투를 돌파하는 짧은 로그라이크 게임",
  openGraph: {
    title: "마지막 관문 · Last Gate",
    description: "다섯 번의 전투, 하나의 덱. 관문 너머까지 살아남으세요.",
    images: [{ url: "/og.jpg", width: 1672, height: 941, alt: "마지막 관문 덱빌딩 로그라이크" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "마지막 관문 · Last Gate",
    description: "다섯 번의 전투, 하나의 덱. 관문 너머까지 살아남으세요.",
    images: ["/og.jpg"],
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body className={`${geistSans.variable} ${geistMono.variable}`}>
        {children}
      </body>
    </html>
  );
}
