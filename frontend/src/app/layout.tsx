import { ReactNode } from "react";

export const metadata = {
  title: "Goatcat Voice AI Interview",
  description: "Real-time voice AI interview application built with Pipecat and Next.js",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div id="root">{children}</div>
      </body>
    </html>
  );
}
