import { ReactNode } from "react";

import "./globals.css";

// Brand fonts: Figtree Variable (sans/display) + Space Mono (mono), loaded via
// @fontsource so they're self-hosted and fingerprinted — no build-time fetch.
import "@fontsource-variable/figtree";
import "@fontsource/space-mono/400.css";
import "@fontsource/space-mono/700.css";

import { AppShell } from "@/components/app/AppShell";
import { QueryProvider } from "@/providers/query-provider";

export const metadata = {
  title: "Freya — Speaker Diarization",
  description: "Real-time voice AI with live speaker diarization, by Freya.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body>
        <QueryProvider>
          <div id="root">
            <AppShell title="Freya">{children}</AppShell>
          </div>
        </QueryProvider>
      </body>
    </html>
  );
}
