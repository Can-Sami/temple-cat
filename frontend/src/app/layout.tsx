import { ReactNode } from "react";

import "./globals.css";

import { AppShell } from "@/components/app/AppShell";
import { QueryProvider } from "@/providers/query-provider";
import { GeistSans } from "geist/font/sans";

const geist = GeistSans;

export const metadata = {
  title: "Temple-cat Voice AI Interview",
  description: "Real-time voice AI interview application built with Pipecat and Next.js",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" className={`font-sans ${geist.variable}`}>
      <body>
        <QueryProvider>
          <div id="root">
            <AppShell title="Temple-cat Voice AI Interview">{children}</AppShell>
          </div>
        </QueryProvider>
      </body>
    </html>
  );
}
