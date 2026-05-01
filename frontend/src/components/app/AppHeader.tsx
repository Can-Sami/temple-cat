"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

export function AppHeader({
  title,
  right,
  className,
}: {
  title: string;
  right?: React.ReactNode;
  className?: string;
}) {
  return (
    <header
      className={cn(
        "flex items-center justify-between gap-4 border-b bg-background px-3 py-2 md:px-4",
        className
      )}
    >
      <div className="flex items-center gap-2">
        <div className="min-w-0">
          <h1 className="truncate text-sm font-medium md:text-base">{title}</h1>
        </div>
      </div>
      {right ? <div className="shrink-0">{right}</div> : null}
    </header>
  );
}

