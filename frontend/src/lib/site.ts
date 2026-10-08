/** Public contact address. Override with NEXT_PUBLIC_CONTACT_EMAIL per deployment. */
export const CONTACT_EMAIL =
  process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "supportcarequill@gmail.com";

/** Shown on the legal pages. Bump with `TERMS_VERSION` in the backend settings. */
export const LEGAL_UPDATED = "8 October 2026";
