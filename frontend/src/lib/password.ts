/**
 * Password strength rules. These mirror `backend/app/core/password_policy.py`
 * so the user gets instant feedback; the server is the one that enforces them.
 */
export const PASSWORD_MIN_LENGTH = 10;

export interface PasswordRule {
  id: string;
  label: string;
  test: (password: string) => boolean;
}

const COMMON_WORDS = [
  "password", "passw0rd", "passcode", "letmein", "welcome", "admin", "administrator",
  "qwerty", "qwertyuiop", "asdfgh", "asdfghjkl", "zxcvbn", "zxcvbnm", "iloveyou",
  "monkey", "dragon", "football", "baseball", "master", "sunshine", "princess",
  "superman", "batman", "shadow", "trustno", "login", "secret", "changeme",
  "carequill", "medqueue", "health", "doctor", "patient", "hospital", "nepal",
  "kathmandu", "namaste", "abcdef", "abcdefgh", "test", "testing", "default",
  "guest", "hello", "freedom", "whatever", "starwars", "cricket", "ronaldo",
];

const SEQUENCES = [
  "0123456789",
  "9876543210",
  "abcdefghijklmnopqrstuvwxyz",
  "zyxwvutsrqponmlkjihgfedcba",
  "qwertyuiopasdfghjklzxcvbnm",
  "mnbvcxzlkjhgfdsapoiuytrewq",
];

function hasSequence(value: string, size = 5): boolean {
  const lowered = value.toLowerCase();
  return SEQUENCES.some((seq) => {
    for (let i = 0; i + size <= seq.length; i += 1) {
      if (lowered.includes(seq.slice(i, i + size))) return true;
    }
    return false;
  });
}

function core(value: string): string {
  const map: Record<string, string> = { "@": "a", $: "s", "0": "o", "!": "i", "1": "i", "|": "i", "3": "e" };
  const swapped = value
    .toLowerCase()
    .split("")
    .map((c) => map[c] ?? c)
    .join("");
  return swapped.replace(/[^a-z]/g, "");
}

function isCommon(value: string): boolean {
  const c = core(value);
  return COMMON_WORDS.some((word) => c.includes(word) && c.length - word.length <= 3);
}

function hasLongRun(value: string): boolean {
  return /(.)\1{3,}/.test(value) || new Set(value).size < 5;
}

/** The checklist shown under the password field. */
export const PASSWORD_RULES: PasswordRule[] = [
  { id: "length", label: `At least ${PASSWORD_MIN_LENGTH} characters`, test: (p) => p.length >= PASSWORD_MIN_LENGTH },
  { id: "lower", label: "A lowercase letter", test: (p) => /[a-z]/.test(p) },
  { id: "upper", label: "An uppercase letter", test: (p) => /[A-Z]/.test(p) },
  { id: "number", label: "A number", test: (p) => /\d/.test(p) },
  { id: "symbol", label: "A symbol, like ! @ # ?", test: (p) => /[^A-Za-z0-9]/.test(p) },
];

/** Returns the first problem with `password`, or null when it is strong. */
export function passwordProblem(password: string, email?: string): string | null {
  const missing = PASSWORD_RULES.find((rule) => !rule.test(password));
  if (missing) return `Password needs: ${missing.label.toLowerCase()}.`;
  if (password.length > 128) return "Password is too long (128 characters at most).";
  if (hasLongRun(password)) return "Avoid repeated characters such as 1111 or aaaa.";
  if (hasSequence(password)) return "Avoid sequences such as 12345, abcde or qwerty.";
  if (isCommon(password)) return "This password is too common or easy to guess.";
  if (email) {
    const local = email.split("@")[0]?.toLowerCase().replace(/[^a-z]/g, "") ?? "";
    if (local.length >= 4 && core(password).includes(local)) {
      return "Do not use your email address in your password.";
    }
  }
  return null;
}

export type StrengthLevel = 0 | 1 | 2 | 3;

/** 0 = empty/too weak, 1 = weak, 2 = good, 3 = strong. */
export function passwordStrength(password: string, email?: string): StrengthLevel {
  if (!password) return 0;
  const passed = PASSWORD_RULES.filter((r) => r.test(password)).length;
  if (passed < PASSWORD_RULES.length || passwordProblem(password, email)) return passed >= 4 ? 1 : 0;
  if (password.length >= 16) return 3;
  return password.length >= 13 ? 3 : 2;
}
