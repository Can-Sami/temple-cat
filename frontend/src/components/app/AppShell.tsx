"use client";

import * as React from "react";

import { AppHeader } from "@/components/app/AppHeader";

import { PageContainer } from "./PageContainer";

export function AppShell({
  title,
  headerRight,
  children,
}: {
  title: string;
  headerRight?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-svh flex-col bg-background">
      <AppHeader title={title} right={headerRight} />
      <PageContainer className="flex-1">{children}</PageContainer>
    </div>
  );
}

