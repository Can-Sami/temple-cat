interface Props {
  isActive: boolean;
  onStart: () => void;
  onStop: () => void;
}

export function SessionControlPanel({ isActive, onStart, onStop }: Props) {
  return (
    <div>
      {isActive ? (
        <button onClick={onStop}>Stop Session</button>
      ) : (
        <button onClick={onStart}>Start Session</button>
      )}
    </div>
  );
}
