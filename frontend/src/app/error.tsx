"use client";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex justify-center py-10">
      <Card className="w-full max-w-xl">
        <CardHeader className="border-b">
          <CardTitle>Something went wrong</CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <Alert variant="destructive">
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error.message}</AlertDescription>
          </Alert>
        </CardContent>
        <CardFooter className="justify-end">
          <Button type="button" onClick={reset}>
            Try again
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
