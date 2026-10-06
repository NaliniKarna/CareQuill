"use client";

// Root-level fallback: catches errors thrown outside every other error
// boundary (e.g. in the root layout itself). Must render its own <html>/
// <body> since it replaces the root layout entirely when triggered.
export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col items-center justify-center gap-4 bg-background px-4 text-center text-foreground">
        <h1 className="text-2xl font-semibold tracking-tight">Something went wrong</h1>
        <p className="max-w-sm text-muted-foreground">
          CareQuill hit an unexpected error. Your data is safe -- please try again.
        </p>
        <button
          type="button"
          onClick={() => reset()}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Try again
        </button>
      </body>
    </html>
  );
}
