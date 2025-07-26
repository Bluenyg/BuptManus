import { GeistSans } from "geist/font/sans";
import { type Metadata } from "next";

import "~/styles/globals.css";
import ParticlesBackground from './_components/ParticlesBackground';
import DarkModeToggle from './_components/DarkModeToggle';
import LanguageToggle from './_components/LanguageToggle';

export const metadata: Metadata = {
  title: "BuptManus",
  description:
    "This is a universal super AI assistant that can help you with anything.",
  icons: [{ rel: "icon", url: "/favicon.ico" }],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${GeistSans.variable}`}>
      <body className="relative bg-body text-default dark:bg-black dark:text-white transition-colors duration-300">
        {/* 粒子背景在底层 */}
        <ParticlesBackground />
        {/* 暗黑模式切换按钮 */}
        <DarkModeToggle />
        {/* 页面内容层 */}
        <main className="relative z-10">{children}</main>
      </body>
    </html>
  );
}
