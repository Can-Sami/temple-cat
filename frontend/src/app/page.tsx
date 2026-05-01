"use client";

import { DailyTransport } from "@pipecat-ai/daily-transport";
import { LogLevel, PipecatClient, RTVIEvent } from "@pipecat-ai/client-js";
import { PipecatClientAudio, PipecatClientProvider, usePipecatClient, useRTVIClientEvent } from "@pipecat-ai/client-react";
import { useState, useEffect } from "react";
import { SessionConfigForm, SessionConfigPayload } from "../features/session-config/SessionConfigForm";
import { SessionControlPanel } from "../features/session-control/SessionControlPanel";
import { BotStateBadge, BotState } from "../features/dashboard/BotStateBadge";
import { LatencyPanel } from "../features/dashboard/LatencyPanel";
import { useVoiceSession } from "@/hooks/useVoiceSession";

// Component inside the RTVIProvider
function InterviewDashboard() {
  const client = usePipecatClient();
  const { createSession, purgeCredentials, resetVoiceSession } = useVoiceSession();
  const [sessionActive, setSessionActive] = useState(false);
  const [botState, setBotState] = useState<BotState>("Listening");
  const [latencyMs, setLatencyMs] = useState(0);
  const [userSilenceStartTime, setUserSilenceStartTime] = useState<number | null>(null);
  const [transportError, setTransportError] = useState<string | null>(null);

  // RTVI Event listeners to drive state machine deterministically based on pipeline emitted frames
  useRTVIClientEvent(RTVIEvent.BotStartedSpeaking, () => {
    setBotState("Speaking");
    // Calculate round trip latency if we were tracking user silence
    if (userSilenceStartTime) {
      setLatencyMs(Math.round(performance.now() - userSilenceStartTime));
      setUserSilenceStartTime(null);
    }
  });

  useRTVIClientEvent(RTVIEvent.BotStoppedSpeaking, () => {
    setBotState("Listening");
  });

  useRTVIClientEvent(RTVIEvent.UserStartedSpeaking, () => {
    setBotState("Listening");
    setUserSilenceStartTime(null); // Interruption cancels the timer
  });

  useRTVIClientEvent(RTVIEvent.UserStoppedSpeaking, () => {
    setBotState("Thinking");
    setUserSilenceStartTime(performance.now());
  });

  useRTVIClientEvent(RTVIEvent.Disconnected, () => {
    setSessionActive(false);
    setBotState("Listening");
    setLatencyMs(0);
    resetVoiceSession();
  });

  async function handleStartSession(payload: SessionConfigPayload) {
    setTransportError(null);
    try {
      const creds = await createSession.mutateAsync(payload);
      try {
        await client?.connect({ url: creds.room_url, token: creds.token });
        setSessionActive(true);
      } catch (connectErr) {
        purgeCredentials();
        const message =
          connectErr instanceof Error
            ? connectErr.message
            : "Could not connect to the voice room.";
        setTransportError(message);
        console.error(connectErr);
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function handleStopSession() {
    await client?.disconnect();
    setSessionActive(false);
    resetVoiceSession();
    setTransportError(null);
  }

  const apiErrorMessage =
    createSession.error instanceof Error ? createSession.error.message : null;
  const sessionError = transportError ?? apiErrorMessage;

  return (
    <main style={{ padding: "2rem", maxWidth: "800px", margin: "0 auto", fontFamily: "sans-serif" }}>
      <h1>Temple-cat Voice AI Interview</h1>
      
      {!sessionActive ? (
        <section>
          <h2>Configure Session</h2>
          {sessionError ? (
            <div role="alert" style={{ color: "#b00020", marginBottom: "1rem" }}>
              {sessionError}
            </div>
          ) : null}
          <SessionConfigForm
            onSubmit={handleStartSession}
            submitting={createSession.isPending}
          />
        </section>
      ) : (
        <section>
          <h2>Live Session</h2>
          <div style={{ display: "flex", gap: "1rem", alignItems: "center", marginBottom: "1rem" }}>
            <BotStateBadge state={botState} />
            <LatencyPanel latencyMs={latencyMs} />
          </div>
          <SessionControlPanel isActive={true} onStart={() => {}} onStop={handleStopSession} />
        </section>
      )}
      <PipecatClientAudio />
    </main>
  );
}

// Wrapper to provide the client
export default function Page() {
  const [client, setClient] = useState<PipecatClient | null>(null);

  useEffect(() => {
    const transport = new DailyTransport();
    const rtviClient = new PipecatClient({
      transport,
      enableMic: true,
    });
    // Server emits `user-llm-text` per RTVI; client-js 1.7 has no handler branch yet (DEBUG fallback).
    rtviClient.setLogLevel(LogLevel.INFO);
    setClient(rtviClient);
  }, []);

  if (!client) return null;

  return (
    <PipecatClientProvider client={client}>
      <InterviewDashboard />
    </PipecatClientProvider>
  );
}
