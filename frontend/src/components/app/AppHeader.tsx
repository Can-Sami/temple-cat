"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

/** Two speaker dots in a soft tile — a quiet nod to the diarization theme. */
function BrandMark() {
  return (
    <span
      aria-hidden
      className="relative grid h-9 w-9 place-items-center rounded-xl bg-secondary/70 ring-1 ring-border shadow-sm"
    >
      <span className="flex items-center gap-1">
        <span className="h-2.5 w-2.5 rounded-full bg-speaker1" />
        <span className="h-2.5 w-2.5 rounded-full bg-speaker2" />
      </span>
    </span>
  );
}

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
        <BrandMark />
        <div className="min-w-0 leading-tight">
          <h1 className="truncate font-display text-base font-extrabold tracking-tight md:text-lg">
            {title}
          </h1>
          <p className="truncate font-mono text-[11px] text-muted-foreground">
            Live speaker diarization
          </p>
        </div>
      </div>
      {right ? <div className="shrink-0">{right}</div> : null}
    </header>
  );
}
