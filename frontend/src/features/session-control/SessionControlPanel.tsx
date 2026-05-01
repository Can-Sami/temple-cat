import { Button } from "@/components/ui/button";

interface Props {
  readonly isActive: boolean;
  readonly onStart: () => void;
  readonly onStop: () => void;
}

export function SessionControlPanel({ isActive, onStart, onStop }: Props) {
  return (
    <div className="flex justify-end">
      {isActive ? (
        <Button type="button" variant="destructive" onClick={onStop}>
          Stop Session
        </Button>
      ) : (
        <Button type="button" onClick={onStart}>
          Start Session
        </Button>
      )}
    </div>
  );
}
