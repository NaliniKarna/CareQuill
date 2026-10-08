import { Check, Circle } from "lucide-react";

import { cn } from "@/lib/utils";
import { PASSWORD_RULES, passwordProblem, passwordStrength } from "@/lib/password";

const LEVELS = [
  { label: "Too weak", bar: "bg-destructive", text: "text-destructive" },
  { label: "Weak", bar: "bg-warning", text: "text-warning-foreground" },
  { label: "Good", bar: "bg-primary/70", text: "text-primary" },
  { label: "Strong", bar: "bg-success", text: "text-success" },
];

/** Live strength bar and checklist shown under a "new password" field. */
export function PasswordStrength({ password, email }: { password: string; email?: string }) {
  const level = passwordStrength(password, email);
  const problem = password ? passwordProblem(password, email) : null;
  const info = LEVELS[level];

  return (
    <div className="flex flex-col gap-2" aria-live="polite">
      <div className="flex items-center gap-2">
        <div className="flex flex-1 gap-1" aria-hidden>
          {[1, 2, 3].map((segment) => (
            <span
              key={segment}
              className={cn("h-1.5 flex-1 rounded-full bg-muted transition-colors", level >= segment && info.bar)}
            />
          ))}
        </div>
        <span className={cn("w-16 text-right text-xs font-medium", password ? info.text : "text-muted-foreground")}>
          {password ? info.label : "Strength"}
        </span>
      </div>
      <ul className="grid gap-1 text-xs sm:grid-cols-2">
        {PASSWORD_RULES.map((rule) => {
          const ok = rule.test(password);
          return (
            <li key={rule.id} className={cn("flex items-center gap-1.5", ok ? "text-success" : "text-muted-foreground")}>
              {ok ? <Check className="size-3.5" aria-hidden /> : <Circle className="size-3" aria-hidden />}
              <span>{rule.label}</span>
              <span className="sr-only">{ok ? "(done)" : "(missing)"}</span>
            </li>
          );
        })}
      </ul>
      {problem && password.length >= 4 && PASSWORD_RULES.every((r) => r.test(password)) && (
        <p role="alert" className="text-xs text-destructive">
          {problem}
        </p>
      )}
    </div>
  );
}
