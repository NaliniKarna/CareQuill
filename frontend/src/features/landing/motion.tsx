"use client";

import { useEffect, useRef, useState, type CSSProperties, type PointerEvent, type ReactNode } from "react";

import { cn } from "@/lib/utils";

/** Fades and lifts its children into view once, when they scroll on screen. */
export function Reveal({
  children,
  className,
  delay = 0,
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
  as?: "div" | "li" | "article";
}) {
  const ref = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <Tag
      ref={ref as never}
      data-visible={visible}
      style={{ "--reveal-delay": `${delay}ms` } as CSSProperties}
      className={cn("landing-reveal", className)}
    >
      {children}
    </Tag>
  );
}

/**
 * A 3D stage: the child leans toward the pointer. Pure CSS variables, so
 * there is no re-render on move. Touch devices and reduced-motion users get
 * the static resting angle.
 */
export function TiltStage({
  children,
  className,
  direction = "left",
}: {
  children: ReactNode;
  className?: string;
  direction?: "left" | "right";
}) {
  const inner = useRef<HTMLDivElement | null>(null);

  function onMove(e: PointerEvent<HTMLDivElement>) {
    if (e.pointerType !== "mouse" || !inner.current) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width - 0.5;
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    const base = direction === "left" ? -9 : 9;
    inner.current.style.setProperty("--tilt-y", `${base + px * 10}deg`);
    inner.current.style.setProperty("--tilt-x", `${4 - py * 8}deg`);
  }

  function onLeave() {
    inner.current?.style.removeProperty("--tilt-y");
    inner.current?.style.removeProperty("--tilt-x");
  }

  return (
    <div className={cn("landing-stage", className)} onPointerMove={onMove} onPointerLeave={onLeave}>
      <div ref={inner} className={cn("landing-tilt", direction === "right" && "landing-tilt-right")}>
        {children}
      </div>
    </div>
  );
}
