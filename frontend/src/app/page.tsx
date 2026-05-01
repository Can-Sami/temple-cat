"use client";

import { useQuery } from "@tanstack/react-query";
import { DailyTransport } from "@pipecat-ai/daily-transport";
import { PipecatClient, RTVIEvent } from "@pipecat-ai/client-js";
import { PipecatClientAudio, PipecatClientProvider, usePipecatClient, useRTVIClientEvent } from "@pipecat-ai/client-react";
import { useState, useEffect } from "react";
import { SessionConfigForm, SessionConfigPayload } from "../features/session-config/SessionConfigForm";
import { SessionControlPanel } from "../features/session-control/SessionControlPanel";
import { BotStateBadge, BotState } from "../features/dashboard/BotStateBadge";
import { LatencyPanel } from "../features/dashboard/LatencyPanel";

// Component inside the RTVIProvider
function InterviewDashboard() {
  const client = usePipecatClient();
  const [sessionActive, setSessionActive] = useState(false);
  const [botState, setBotState] = useState<BotState>("Listening");
  const [latencyMs, setLatencyMs] = useState(0);
  const [userSilenceStartTime, setUserSilenceStartTime] = useState<number | null>(null);

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
  });

  async function handleStartSession(payload: SessionConfigPayload) {
    try {
      const response = await fetch(`/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error("Failed to start session");
      
      const { room_url, token } = await response.json();
      
      // Connect RTVI client
      await client?.connect({ url: room_url, token });
      setSessionActive(true);
    } catch (err) {
      console.error(err);
      alert("Failed to connect");
    }
  }

  async function handleStopSession() {
    await client?.disconnect();
    setSessionActive(false);
  }

  return (
    <main style={{ padding: "2rem", maxWidth: "800px", margin: "0 auto", fontFamily: "sans-serif" }}>
      <h1>Temple-cat Voice AI Interview</h1>
      
      {!sessionActive ? (
        <section>
          <h2>Configure Session</h2>
          <SessionConfigForm onSubmit={handleStartSession} />
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
    setClient(rtviClient);
  }, []);

  if (!client) return null;

  return (
    <PipecatClientProvider client={client}>
      <InterviewDashboard />
    </PipecatClientProvider>
  );
}
