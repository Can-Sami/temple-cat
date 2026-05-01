"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import type { SessionConfigPayload } from "@/features/session-config/SessionConfigForm";
import { createVoiceSession } from "@/lib/api/sessions";
import { voiceSessionKeys } from "@/lib/query-keys";

function credentialsNeverFetched(): Promise<never> {
  return Promise.reject(
    new Error("Voice session credentials are set via createVoiceSession only")
  );
}

/**
 * Server-backed voice session: POST result is written to the query cache so
 * credentials survive incidental rerenders and can be read consistently.
 */
export function useVoiceSession() {
  const queryClient = useQueryClient();

  const credentialsQuery = useQuery({
    queryKey: voiceSessionKeys.credentials(),
    queryFn: credentialsNeverFetched,
    enabled: false,
    staleTime: Infinity,
    gcTime: 60 * 60_000,
  });

  const createSession = useMutation({
    mutationFn: (payload: SessionConfigPayload) => createVoiceSession(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(voiceSessionKeys.credentials(), data);
    },
  });

  /** Drop cached room/token only (keeps mutation error state for API failures). */
  const purgeCredentials = useCallback(() => {
    queryClient.removeQueries({ queryKey: voiceSessionKeys.all });
  }, [queryClient]);

  /** Full reset: cache + mutation state (e.g. explicit stop or disconnect). */
  const resetVoiceSession = useCallback(() => {
    queryClient.removeQueries({ queryKey: voiceSessionKeys.all });
    createSession.reset();
  }, [queryClient, createSession]);

  return {
    /** Latest credentials from cache (after a successful mutation). */
    credentials: credentialsQuery.data,
    createSession,
    purgeCredentials,
    resetVoiceSession,
  };
}
