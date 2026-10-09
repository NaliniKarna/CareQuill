/**
 * Phone number rule, kept identical to backend/app/schemas/phone.py:
 * optional leading "+", then digits with spaces, dashes, dots or brackets,
 * and 7 to 15 digits in total. Nepali mobile (98XXXXXXXX), landline
 * (01-XXXXXXX) and +977 numbers all pass. An empty value is allowed.
 */
export const PHONE_MAX_LENGTH = 30;
const MIN_DIGITS = 7;
const MAX_DIGITS = 15;
const ALLOWED = /^\+?[0-9\s\-().]+$/;

export const PHONE_ERROR = "Enter a valid phone number, for example +977 9812345678 (7 to 15 digits).";

export function isValidPhone(value: string | undefined | null): boolean {
  const phone = (value ?? "").trim();
  if (phone === "") return true;
  if (phone.length > PHONE_MAX_LENGTH || !ALLOWED.test(phone)) return false;
  const digits = phone.replace(/\D/g, "").length;
  return digits >= MIN_DIGITS && digits <= MAX_DIGITS;
}
