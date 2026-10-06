"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FlipHorizontal2, Minus, Plus, RotateCw, SunMedium } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { documentService } from "@/services/document-service";
import type { MedicalDocument } from "@/types/api";

/**
 * In-app viewer for the ORIGINAL uploaded file (X-ray, scan, photo, PDF).
 * The bytes come through the authorized API route as a blob; the controls
 * (zoom, rotate, brightness/contrast, invert) are purely visual and never
 * alter the stored file. This is for looking at a record, not for diagnosis.
 */
export function DocumentViewer({ document: doc }: { document: MedicalDocument }) {
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [brightness, setBrightness] = useState(100);
  const [contrast, setContrast] = useState(100);
  const [invert, setInvert] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["document-preview", doc.id],
    queryFn: () => documentService.preview(doc.id),
    staleTime: Infinity,
    gcTime: 0,
    retry: false,
  });

  // The object URL is owned by this component: release it when it unmounts.
  const url = data?.url;
  useEffect(() => {
    return () => {
      if (url) window.URL.revokeObjectURL(url);
    };
  }, [url]);

  if (isLoading) return <Skeleton className="h-72" />;
  if (isError || !data) {
    return <p className="text-sm text-muted-foreground">The file could not be loaded for preview.</p>;
  }

  const isImage = data.mimeType.startsWith("image/");
  const isPdf = data.mimeType === "application/pdf";

  if (!isImage && !isPdf) {
    return (
      <p className="text-sm text-muted-foreground">
        This file type cannot be previewed. Use the download button to open it.
      </p>
    );
  }

  if (isPdf) {
    return (
      <iframe
        src={data.url}
        title={`Preview of ${doc.title}`}
        className="h-[32rem] w-full rounded-md border border-border"
      />
    );
  }

  const reset = () => {
    setZoom(1);
    setRotation(0);
    setBrightness(100);
    setContrast(100);
    setInvert(false);
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <Button type="button" size="sm" variant="outline" aria-label="Zoom out"
          onClick={() => setZoom((z) => Math.max(0.5, +(z - 0.25).toFixed(2)))}>
          <Minus className="size-4" />
        </Button>
        <span className="w-12 text-center text-xs text-muted-foreground">{Math.round(zoom * 100)}%</span>
        <Button type="button" size="sm" variant="outline" aria-label="Zoom in"
          onClick={() => setZoom((z) => Math.min(4, +(z + 0.25).toFixed(2)))}>
          <Plus className="size-4" />
        </Button>
        <Button type="button" size="sm" variant="outline" aria-label="Rotate"
          onClick={() => setRotation((r) => (r + 90) % 360)}>
          <RotateCw className="size-4" />
        </Button>
        <Button type="button" size="sm" variant={invert ? "default" : "outline"} aria-pressed={invert}
          onClick={() => setInvert((v) => !v)}>
          <FlipHorizontal2 className="size-4" />
          Invert
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={reset}>
          Reset
        </Button>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          <SunMedium className="size-4" />
          Brightness
          <input type="range" min={40} max={200} value={brightness} className="flex-1"
            onChange={(e) => setBrightness(Number(e.target.value))} aria-label="Brightness" />
        </label>
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          <SunMedium className="size-4" />
          Contrast
          <input type="range" min={40} max={250} value={contrast} className="flex-1"
            onChange={(e) => setContrast(Number(e.target.value))} aria-label="Contrast" />
        </label>
      </div>
      <div className="max-h-[32rem] overflow-auto rounded-md border border-border bg-black/90 p-2">
        {/* eslint-disable-next-line @next/next/no-img-element -- blob URL, not optimizable */}
        <img
          src={data.url}
          alt={`Uploaded image: ${doc.title}`}
          className="mx-auto block max-w-none origin-center transition-transform"
          style={{
            width: `${zoom * 100}%`,
            transform: `rotate(${rotation}deg)`,
            filter: `brightness(${brightness}%) contrast(${contrast}%)${invert ? " invert(1)" : ""}`,
          }}
        />
      </div>
    </div>
  );
}
