"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Language = "en" | "ne";

interface LanguageState {
  language: Language;
  setLanguage: (language: Language) => void;
}

/**
 * Remembers the visitor's chosen language for the public pages. This only
 * holds a UI preference (never health data), so localStorage is fine.
 */
export const useLanguageStore = create<LanguageState>()(
  persist(
    (set) => ({
      language: "en",
      setLanguage: (language) => set({ language }),
    }),
    { name: "carequill-language" }
  )
);
