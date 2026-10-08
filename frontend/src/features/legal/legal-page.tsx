import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { BrandLogo } from "@/components/shared/brand";
import { CONTACT_EMAIL, LEGAL_UPDATED } from "@/lib/site";

export interface LegalSection {
  title: string;
  body: string[];
  list?: string[];
}

export function LegalPage({
  title,
  intro,
  sections,
}: {
  title: string;
  intro: string;
  sections: LegalSection[];
}) {
  return (
    <div className="min-h-svh bg-gradient-to-b from-accent/40 to-background">
      <header className="border-b bg-card/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-3xl items-center justify-between px-4">
          <Link href="/" aria-label="CareQuill home">
            <BrandLogo markClassName="h-8" />
          </Link>
          <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="size-4" /> Back to home
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">Last updated {LEGAL_UPDATED}</p>
        <p className="mt-6 text-lg leading-relaxed text-muted-foreground">{intro}</p>

        <div className="mt-10 flex flex-col gap-8">
          {sections.map((section, index) => (
            <section key={section.title} aria-labelledby={`legal-${index}`}>
              <h2 id={`legal-${index}`} className="text-xl font-semibold tracking-tight">
                {index + 1}. {section.title}
              </h2>
              {section.body.map((paragraph) => (
                <p key={paragraph} className="mt-2 leading-relaxed text-foreground/90">
                  {paragraph}
                </p>
              ))}
              {section.list && (
                <ul className="mt-2 list-disc space-y-1 pl-6 text-foreground/90">
                  {section.list.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              )}
            </section>
          ))}
        </div>

        <p className="mt-12 rounded-xl border bg-card p-4 text-sm text-muted-foreground">
          Questions about this page? Email{" "}
          <a href={`mailto:${CONTACT_EMAIL}`} className="font-medium text-primary hover:underline">
            {CONTACT_EMAIL}
          </a>
          .
        </p>
      </main>
    </div>
  );
}
