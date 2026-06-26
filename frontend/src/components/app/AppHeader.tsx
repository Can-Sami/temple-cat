"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

export function AppHeader({
  title,
  right,
  className,
}: Readonly<{
  title: string;
  right?: React.ReactNode;
  className?: string;
}>) {
  return (
    <header
      className={cn(
        "sticky top-0 z-30 flex items-center justify-between gap-4 border-b border-border/80 bg-background/80 px-4 py-3 backdrop-blur-md md:px-6",
        className
      )}
    >
      <div className="flex min-w-0 items-center gap-3">
        <h1 className="flex items-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/freya_logo_white.svg" alt={title} className="h-6 w-auto md:h-7" />
        </h1>
        <span className="hidden border-l border-border pl-3 font-mono text-xs text-muted-foreground sm:inline">
          Speaker Diarization
        </span>
      </div>
      {right ? <div className="shrink-0">{right}</div> : null}
    </header>
  );
}
