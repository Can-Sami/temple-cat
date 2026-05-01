import { ReactNode } from "react";

import "./globals.css";

import { QueryProvider } from "@/providers/query-provider";
import { cn } from "@/lib/utils";
import { GeistSans } from "geist/font/sans";

const geist = GeistSans;

export const metadata = {
  title: "Temple-cat Voice AI Interview",
  description: "Real-time voice AI interview application built with Pipecat and Next.js",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={cn("font-sans", geist.variable)}>
      <body>
        <QueryProvider>
          <div id="root">{children}</div>
        </QueryProvider>
      </body>
    </html>
  );
}
