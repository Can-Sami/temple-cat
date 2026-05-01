import { ReactNode } from "react";

import "./globals.css";

import { QueryProvider } from "@/providers/query-provider";

export const metadata = {
  title: "Temple-cat Voice AI Interview",
  description: "Real-time voice AI interview application built with Pipecat and Next.js",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>
          <div id="root">{children}</div>
        </QueryProvider>
      </body>
    </html>
  );
}
