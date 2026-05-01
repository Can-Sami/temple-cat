"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main style={{ padding: "2rem", maxWidth: "560px", margin: "0 auto", fontFamily: "sans-serif" }}>
      <h1>Something went wrong</h1>
      <p role="alert" style={{ color: "#b00020" }}>
        {error.message}
      </p>
      <button type="button" onClick={() => reset()}>
        Try again
      </button>
    </main>
  );
}
