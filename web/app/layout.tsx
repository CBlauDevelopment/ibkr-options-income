import type { Metadata } from "next";
import { Hanken_Grotesk, Red_Hat_Mono } from "next/font/google";
import "./globals.css";
import { Rail } from "@/components/shell/Rail";
import { Providers } from "@/app/providers";
import { THEME_INIT_SCRIPT } from "@/lib/theme";

const sans = Hanken_Grotesk({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800", "900"],
  variable: "--font-sans",
});

const mono = Red_Hat_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "IBKR Income",
  description: "Options income console",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // data-theme is set by THEME_INIT_SCRIPT before paint; suppressHydrationWarning
    // because the server always renders "light" and the script may have changed it.
    <html
      lang="en"
      data-theme="light"
      className={`${sans.variable} ${mono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body
        className="bg-background text-content font-sans antialiased"
        suppressHydrationWarning
      >
        <Providers>
          <div className="flex h-screen overflow-hidden">
            <Rail />
            <main className="flex-1 overflow-y-auto overflow-x-hidden">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
