import type { Metadata } from "next";

import { LegalPage } from "@/features/legal/legal-page";

export const metadata: Metadata = { title: "Terms of Use · CareQuill" };

export default function TermsPage() {
  return (
    <LegalPage
      title="Terms of Use"
      intro="These terms describe how you may use CareQuill. By creating an account you agree to them and to our Privacy Policy."
      sections={[
        {
          title: "What CareQuill is",
          body: [
            "CareQuill is a tool to organise and share your health information. It is not a medical service. It does not diagnose conditions, prescribe treatment or replace professional medical advice. Always consult a qualified doctor for medical decisions. In an emergency, contact your nearest hospital.",
          ],
        },
        {
          title: "Your account",
          body: [
            "You must give accurate information and keep your password private. Choose a strong, unique password. You are responsible for activity on your account, so tell us at once if you think it was accessed without your permission.",
          ],
        },
        {
          title: "Your information",
          body: [
            "You own your information. You give CareQuill permission to store and process it only to provide the service to you, as described in the Privacy Policy. Only upload records you have the right to hold, and only add a relative's information if you are entitled to manage it.",
          ],
        },
        {
          title: "AI suggestions",
          body: [
            "OCR and AI can make mistakes. Their output is a suggestion for you to check. You are responsible for reviewing it before you approve it or share it with anyone.",
          ],
        },
        {
          title: "Sharing",
          body: [
            "When you email a report or create a QR link, you decide who receives it. Anyone with a link can open what it contains until it expires or you stop it, so share links carefully.",
          ],
        },
        {
          title: "Acceptable use",
          body: ["Do not misuse CareQuill. In particular, do not:"],
          list: [
            "try to access another person's account or data;",
            "upload unlawful content or malware;",
            "overload or interfere with the service, or bypass its security.",
          ],
        },
        {
          title: "Availability and changes",
          body: [
            "We work to keep CareQuill available but cannot promise it will always be uninterrupted or error free. Keep your own copy of anything critical; you can download your data at any time. We may improve or change features, and we will update these terms when needed.",
          ],
        },
        {
          title: "Ending your account",
          body: [
            "You can delete your account at any time from Settings. We may suspend accounts that break these terms or put others at risk.",
          ],
        },
        {
          title: "Liability",
          body: [
            "To the extent the law allows, CareQuill is provided as is, and we are not liable for decisions made using information in the app or for indirect losses. Nothing here limits rights you have under the law.",
          ],
        },
      ]}
    />
  );
}
