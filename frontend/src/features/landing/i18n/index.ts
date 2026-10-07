"use client";

import { useEffect } from "react";

import { useLanguageStore, type Language } from "@/store/language-store";

import { en, type LandingCopy } from "./en";
import { ne } from "./ne";

const COPY: Record<Language, LandingCopy> = { en, ne };

/** Returns the landing copy for the visitor's language and keeps <html lang> in sync. */
export function useLandingCopy(): { t: LandingCopy; language: Language } {
  const language = useLanguageStore((s) => s.language);

  useEffect(() => {
    document.documentElement.lang = language;
    return () => {
      document.documentElement.lang = "en";
    };
  }, [language]);

  return { t: COPY[language], language };
}

export type { LandingCopy };
