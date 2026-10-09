"use client";

import Image from "next/image";
import Link from "next/link";
import axios from "axios";
import { useState, type FormEvent } from "react";
import {
  Bot,
  Check,
  ChevronDown,
  Eye,
  HeartHandshake,
  Lock,
  ShieldCheck,
  Users,
  X,
  Loader2,
  CheckCircle2,
  Clock,
  ClipboardCheck,
  FolderOpen,
  Mail,
  MapPin,
  Repeat,
  Send,
  Sparkles,
  TriangleAlert,
  UserPlus,
  FileWarning,
} from "lucide-react";

import { BrandLogo } from "@/components/shared/brand";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { apiClient } from "@/lib/api-client";
import { CONTACT_EMAIL } from "@/lib/site";

import { FeatureShowcase } from "./feature-showcase";
import { CROSS_PATTERN } from "./hero-section";
import type { LandingCopy } from "./i18n";
import { Reveal } from "./motion";

function SectionHeading({
  eyebrow,
  title,
  text,
  id,
}: {
  eyebrow: string;
  title: string;
  text?: string;
  id: string;
}) {
  return (
    <div className="mx-auto mb-12 flex max-w-2xl flex-col items-center gap-3 text-center lg:mb-16">
      <span className="rounded-full bg-accent px-3 py-1 text-xs font-semibold tracking-wide text-primary uppercase">
        {eyebrow}
      </span>
      <h2 id={id} className="text-3xl font-bold tracking-tight text-balance text-foreground sm:text-4xl">
        {title}
      </h2>
      {text && <p className="text-base leading-relaxed text-muted-foreground sm:text-lg">{text}</p>}
    </div>
  );
}

const PROBLEM_ICONS = [FolderOpen, Repeat, FileWarning, Users];
const PRINCIPLE_ICONS = [HeartHandshake, Bot, ShieldCheck, Lock];

export function WhySection({ t }: { t: LandingCopy }) {
  return (
    <section id="features" aria-labelledby="why-title" className="relative scroll-mt-20 overflow-hidden py-20 lg:py-28">
      <div
        aria-hidden
        className="landing-orb pointer-events-none absolute -top-24 -right-24 size-96 rounded-full bg-[oklch(0.92_0.06_195)] opacity-50 blur-3xl"
      />
      <div className="relative mx-auto max-w-7xl px-4 sm:px-6">
        <Reveal>
          <SectionHeading id="why-title" eyebrow={t.why.eyebrow} title={t.why.title} />
        </Reveal>
        <Reveal className="mx-auto -mt-6 max-w-3xl rounded-2xl border border-primary/15 bg-accent/50 p-6 text-center shadow-xs sm:p-8">
          <p className="text-base leading-relaxed text-foreground sm:text-lg">{t.why.description}</p>
        </Reveal>

        {/* Without vs with CareQuill */}
        <div className="mt-14 grid gap-6 lg:grid-cols-2">
          <Reveal className="rounded-3xl border border-destructive/20 bg-card p-6 shadow-xs sm:p-8">
            <h3 className="mb-5 flex items-center gap-2 text-lg font-semibold text-foreground">
              <span className="flex size-8 items-center justify-center rounded-full bg-destructive/10 text-destructive">
                <X className="size-4" aria-hidden />
              </span>
              {t.why.problemsTitle}
            </h3>
            <ul className="grid gap-4">
              {t.why.problems.map((p, i) => {
                const Icon = PROBLEM_ICONS[i] ?? TriangleAlert;
                return (
                  <li key={p.title} className="flex gap-3">
                    <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
                      <Icon className="size-5" aria-hidden />
                    </span>
                    <div>
                      <p className="font-semibold text-foreground">{p.title}</p>
                      <p className="text-sm leading-relaxed text-muted-foreground">{p.text}</p>
                    </div>
                  </li>
                );
              })}
            </ul>
          </Reveal>

          <Reveal
            delay={120}
            className="relative overflow-hidden rounded-3xl bg-primary p-6 text-primary-foreground shadow-xl sm:p-8"
          >
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 opacity-60 invert"
              style={{ backgroundImage: CROSS_PATTERN }}
            />
            <div className="relative">
              <h3 className="mb-5 flex items-center gap-2 text-lg font-semibold">
                <span className="flex size-8 items-center justify-center rounded-full bg-primary-foreground/15">
                  <Check className="size-4" aria-hidden />
                </span>
                {t.why.solutionTitle}
              </h3>
              <ul className="grid gap-4">
                {t.why.solutions.map((text) => (
                  <li key={text} className="flex gap-3 rounded-xl bg-primary-foreground/10 p-4 backdrop-blur-sm">
                    <CheckCircle2 className="mt-0.5 size-5 shrink-0" aria-hidden />
                    <span className="text-sm leading-relaxed sm:text-base">{text}</span>
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>
        </div>

        {/* Principles */}
        <div className="mt-16">
          <Reveal>
            <h3 className="mb-6 flex items-center justify-center gap-2 text-center text-xl font-semibold text-foreground">
              <Eye className="size-5 text-primary" aria-hidden />
              {t.why.principlesTitle}
            </h3>
          </Reveal>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {t.why.principles.map((p, i) => {
              const Icon = PRINCIPLE_ICONS[i] ?? ShieldCheck;
              return (
                <Reveal key={p.title} delay={i * 90}>
                  <div className="group h-full rounded-2xl border border-border bg-card p-6 shadow-xs transition duration-300 hover:-translate-y-1.5 hover:border-primary/40 hover:shadow-xl">
                    <span className="mb-4 flex size-12 items-center justify-center rounded-2xl bg-accent text-primary transition group-hover:scale-110 group-hover:bg-primary group-hover:text-primary-foreground">
                      <Icon className="size-6" aria-hidden />
                    </span>
                    <h4 className="mb-1.5 font-semibold text-foreground">{p.title}</h4>
                    <p className="text-sm leading-relaxed text-muted-foreground">{p.text}</p>
                  </div>
                </Reveal>
              );
            })}
          </div>
        </div>

        <div className="mt-24 lg:mt-32">
          <Reveal>
            <SectionHeading
              id="features-title"
              eyebrow={t.why.featuresEyebrow}
              title={t.why.featuresTitle}
              text={t.why.featuresText}
            />
          </Reveal>
          <FeatureShowcase t={t} />
        </div>
      </div>
    </section>
  );
}

const STEP_ICONS = [UserPlus, FolderOpen, ClipboardCheck, Send];

export function HowItWorksSection({ t }: { t: LandingCopy }) {
  return (
    <section
      id="how-it-works"
      aria-labelledby="how-title"
      className="scroll-mt-20 border-y border-border bg-muted/50 py-20 lg:py-28"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <SectionHeading id="how-title" eyebrow={t.how.eyebrow} title={t.how.title} text={t.how.text} />
        <ol className="relative grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <span
            aria-hidden
            className="absolute top-8 right-[12%] left-[12%] hidden h-0.5 bg-gradient-to-r from-primary/10 via-primary/40 to-primary/10 lg:block"
          />
          {t.how.steps.map((s, i) => {
            const Icon = STEP_ICONS[i] ?? Sparkles;
            return (
              <li
                key={s.title}
                className="relative flex flex-col items-center gap-3 rounded-2xl border border-border bg-card p-6 text-center shadow-xs"
              >
                <span className="relative flex size-16 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg ring-8 ring-muted">
                  <Icon className="size-7" aria-hidden />
                  <span className="absolute -top-1 -right-1 flex size-6 items-center justify-center rounded-full bg-card text-xs font-bold text-primary shadow">
                    {i + 1}
                  </span>
                </span>
                <h3 className="mt-2 font-semibold text-foreground">{s.title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">{s.text}</p>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}

export function FaqSection({ t }: { t: LandingCopy }) {
  return (
    <section id="faq" aria-labelledby="faq-title" className="scroll-mt-20 py-20 lg:py-28">
      <div className="mx-auto max-w-3xl px-4 sm:px-6">
        <SectionHeading id="faq-title" eyebrow={t.faq.eyebrow} title={t.faq.title} />
        <div className="flex flex-col gap-3">
          {t.faq.items.map((item, i) => (
            <details
              key={item.q}
              open={i === 0}
              className="group rounded-xl border border-border bg-card shadow-xs open:shadow-sm"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 rounded-xl px-5 py-4 font-medium text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none [&::-webkit-details-marker]:hidden">
                {item.q}
                <ChevronDown
                  className="size-5 shrink-0 text-primary transition-transform group-open:rotate-180"
                  aria-hidden
                />
              </summary>
              <p className="px-5 pb-5 text-sm leading-relaxed text-muted-foreground">{item.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

type FieldErrors = Partial<Record<"name" | "email" | "message", string>>;

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type SendState = "idle" | "sending" | "sent" | "failed" | "limited";

function ContactForm({ t }: { t: LandingCopy }) {
  const f = t.contact.form;
  const [values, setValues] = useState({ name: "", email: "", message: "" });
  const [honeypot, setHoneypot] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [state, setState] = useState<SendState>("idle");

  function validate(): FieldErrors {
    const e: FieldErrors = {};
    if (!values.name.trim()) e.name = f.errors.name;
    if (!EMAIL_RE.test(values.email.trim())) e.email = f.errors.email;
    if (values.message.trim().length < 10) e.message = f.errors.message;
    return e;
  }

  async function onSubmit(ev: FormEvent) {
    ev.preventDefault();
    if (state === "sending") return;
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length) return;
    setState("sending");
    try {
      await apiClient.post("/public/contact", {
        name: values.name.trim(),
        email: values.email.trim(),
        message: values.message.trim(),
        website: honeypot,
      });
      setState("sent");
      setValues({ name: "", email: "", message: "" });
    } catch (err) {
      setState(axios.isAxiosError(err) && err.response?.status === 429 ? "limited" : "failed");
    }
  }

  const field = (key: keyof typeof values) => ({
    id: `contact-${key}`,
    value: values[key],
    "aria-invalid": Boolean(errors[key]) || undefined,
    "aria-describedby": errors[key] ? `contact-${key}-error` : undefined,
    onChange: (e: { target: { value: string } }) => {
      setValues((v) => ({ ...v, [key]: e.target.value }));
      if (errors[key]) setErrors((er) => ({ ...er, [key]: undefined }));
    },
  });

  const err = (key: keyof FieldErrors) =>
    errors[key] ? (
      <p id={`contact-${key}-error`} className="text-xs text-destructive">
        {errors[key]}
      </p>
    ) : null;

  return (
    <form noValidate onSubmit={onSubmit} className="relative flex flex-col gap-4 overflow-hidden rounded-2xl border border-border bg-card p-6 shadow-sm">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="contact-name">{f.name}</Label>
          <Input autoComplete="name" maxLength={100} {...field("name")} />
          {err("name")}
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="contact-email">{f.email}</Label>
          <Input type="email" autoComplete="email" maxLength={200} {...field("email")} />
          {err("email")}
        </div>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="contact-message">{f.message}</Label>
        <Textarea rows={5} maxLength={2000} placeholder={f.messagePlaceholder} {...field("message")} />
        {err("message")}
      </div>
      {/* Honeypot: hidden from people, filled in by simple bots */}
      <div aria-hidden className="absolute -left-[9999px] h-0 w-0 overflow-hidden">
        <label htmlFor="contact-website">Website</label>
        <input
          id="contact-website"
          name="website"
          tabIndex={-1}
          autoComplete="off"
          value={honeypot}
          onChange={(e) => setHoneypot(e.target.value)}
        />
      </div>
      <p className="text-xs text-muted-foreground">{f.note}</p>
      <div aria-live="polite">
        {state === "sent" && (
          <p className="flex items-start gap-2 rounded-lg bg-success/10 px-3 py-2 text-sm text-success">
            <CheckCircle2 className="mt-0.5 size-4 shrink-0" aria-hidden />
            {f.success}
          </p>
        )}
        {state === "limited" && (
          <p role="alert" className="rounded-lg bg-warning/15 px-3 py-2 text-sm text-foreground">
            {f.tooMany}
          </p>
        )}
        {state === "failed" && (
          <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {f.failed}{" "}
            <a href={`mailto:${CONTACT_EMAIL}`} className="font-medium underline">
              {CONTACT_EMAIL}
            </a>
          </p>
        )}
      </div>
      <Button type="submit" size="lg" className="w-full sm:w-fit" disabled={state === "sending"}>
        {state === "sending" ? <Loader2 className="animate-spin" /> : <Send />}
        {state === "sending" ? f.sending : f.submit}
      </Button>
    </form>
  );
}

export function ContactSection({ t }: { t: LandingCopy }) {
  const items = [
    {
      icon: Mail,
      label: t.contact.emailLabel,
      value: (
        <a href={`mailto:${CONTACT_EMAIL}`} className="text-primary hover:underline">
          {CONTACT_EMAIL}
        </a>
      ),
    },
    { icon: MapPin, label: t.contact.locationLabel, value: t.contact.location },
    { icon: Clock, label: t.contact.hoursLabel, value: t.contact.hours },
  ];
  return (
    <section
      id="contact"
      aria-labelledby="contact-title"
      className="scroll-mt-20 border-t border-border bg-muted/50 py-20 lg:py-28"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <SectionHeading id="contact-title" eyebrow={t.contact.eyebrow} title={t.contact.title} text={t.contact.text} />
        <div className="grid gap-8 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
          <ul className="flex flex-col gap-4">
            {items.map((it) => (
              <li key={it.label} className="flex items-start gap-4 rounded-2xl border border-border bg-card p-5 shadow-xs">
                <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-accent text-primary">
                  <it.icon className="size-5" aria-hidden />
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-foreground">{it.label}</p>
                  <p className="text-sm break-words text-muted-foreground">{it.value}</p>
                </div>
              </li>
            ))}
          </ul>
          <ContactForm t={t} />
        </div>
      </div>
    </section>
  );
}

export function CtaBand({ t }: { t: LandingCopy }) {
  return (
    <section aria-labelledby="cta-title" className="px-4 py-20 sm:px-6">
      <div className="relative mx-auto max-w-5xl overflow-hidden rounded-3xl bg-primary px-6 py-14 text-center text-primary-foreground shadow-xl sm:px-12">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-60 invert"
          style={{ backgroundImage: CROSS_PATTERN }}
        />
        <div className="relative flex flex-col items-center gap-4">
          <h2 id="cta-title" className="text-3xl font-bold tracking-tight text-balance sm:text-4xl">
            {t.cta.title}
          </h2>
          <p className="max-w-xl text-primary-foreground/85">{t.cta.text}</p>
          <div className="mt-2 flex flex-col gap-3 sm:flex-row">
            <Button asChild size="lg" variant="secondary">
              <Link href="/register">{t.cta.signup}</Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="border-primary-foreground/40 bg-transparent text-primary-foreground hover:bg-primary-foreground/10 hover:text-primary-foreground"
            >
              <Link href="/login">{t.cta.login}</Link>
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}

export function LandingFooter({ t }: { t: LandingCopy }) {
  const columns = [
    {
      title: t.footer.product,
      links: [
        { href: "#features", label: t.nav.features },
        { href: "#how-it-works", label: t.nav.howItWorks },
      ],
    },
    {
      title: t.footer.company,
      links: [
        { href: "#faq", label: t.nav.faq },
        { href: "#contact", label: t.nav.contact },
      ],
    },
    {
      title: t.footer.account,
      links: [
        { href: "/login", label: t.nav.login },
        { href: "/register", label: t.nav.signup },
        { href: "/privacy", label: t.footer.privacy },
        { href: "/terms", label: t.footer.terms },
      ],
    },
  ];
  return (
    <footer className="border-t border-border bg-[oklch(0.22_0.03_235)] text-[oklch(0.85_0.01_230)]">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-[minmax(0,2fr)_repeat(3,minmax(0,1fr))]">
        <div className="flex flex-col gap-4">
          <span className="w-fit rounded-xl bg-white px-3 py-2">
            <BrandLogo markClassName="h-8" />
          </span>
          <p className="max-w-xs text-sm">{t.footer.tagline}</p>
          <a href={`mailto:${CONTACT_EMAIL}`} className="inline-flex items-center gap-2 text-sm hover:text-white">
            <Mail className="size-4" aria-hidden />
            {CONTACT_EMAIL}
          </a>
        </div>
        {columns.map((c) => (
          <div key={c.title}>
            <h3 className="mb-3 text-sm font-semibold text-white">{c.title}</h3>
            <ul className="flex flex-col gap-2 text-sm">
              {c.links.map((l) => (
                <li key={l.href}>
                  {l.href.startsWith("/") ? (
                    <Link href={l.href} className="hover:text-white">
                      {l.label}
                    </Link>
                  ) : (
                    <a href={l.href} className="hover:text-white">
                      {l.label}
                    </a>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="mx-auto flex max-w-7xl justify-end px-4 pb-5 sm:px-6">
        <span className="rounded-md bg-[#f7f7f7] px-2 py-1">
          <Image
            src="/brand/zinob-logo.png"
            alt="Zinob Inc. Pvt. Ltd."
            width={338}
            height={107}
            unoptimized
            className="h-7 w-auto"
          />
        </span>
      </div>
      <div className="border-t border-white/10">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-6 text-xs sm:px-6 md:flex-row md:items-center md:justify-between">
          <p className="max-w-3xl leading-relaxed">{t.footer.disclaimer}</p>
          <p className="shrink-0">
            &copy; {new Date().getFullYear()} CareQuill. {t.footer.rights}
          </p>
        </div>
      </div>
    </footer>
  );
}
