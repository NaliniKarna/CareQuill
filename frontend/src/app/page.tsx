import type { Metadata } from "next";

import { LandingPage } from "@/features/landing/landing-page";

export const metadata: Metadata = {
  title: "My Medical Records by CareQuill",
  description:
    "Keep your medical reports, medicines, allergies, conditions, doctors and appointments in one secure place. AI helps organise your records and you approve every change.",
};

export default function HomePage() {
  return <LandingPage />;
}
