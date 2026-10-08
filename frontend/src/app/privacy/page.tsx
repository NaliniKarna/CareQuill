import type { Metadata } from "next";

import { LegalPage } from "@/features/legal/legal-page";

export const metadata: Metadata = { title: "Privacy Policy · CareQuill" };

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy Policy"
      intro="CareQuill keeps your health records in one place. This page explains what we collect, why, who can see it, and how you stay in control. We treat all health information as highly sensitive."
      sections={[
        {
          title: "What we collect",
          body: ["We collect only what you give us or what is needed to run your account."],
          list: [
            "Account details: your email address and a securely hashed password (we never store your password in readable form).",
            "Health information you add: profile details, conditions, allergies, medicines, appointments, journal entries and doctor contacts.",
            "Documents you upload, such as lab reports, prescriptions and scans. We keep the original file unchanged.",
            "Family profiles and documents you add for relatives.",
            "Your consent record: when you agreed to these terms and which version.",
            "Basic technical logs needed for security, such as sign-in and sharing events. These never contain the content of your records.",
          ],
        },
        {
          title: "Why we use it",
          body: [
            "We use your information only to provide CareQuill to you: to store and show your records, send the reminders and notifications you ask for, and create the reports you choose to share.",
            "We do not sell your data, and we do not use it for advertising.",
          ],
        },
        {
          title: "AI and document reading",
          body: [
            "When you upload a document, OCR and AI may read it and suggest details such as medicines or allergies. These are only suggestions. Nothing is added to your record until you review and approve it.",
            "AI summaries are drafts that you edit and approve before they can be shared. CareQuill does not diagnose conditions or recommend treatment. AI processing runs on the infrastructure that hosts CareQuill using a self-hosted model; your document text is not sent to third-party AI providers.",
            "You can turn off AI processing of your documents in Settings.",
          ],
        },
        {
          title: "Who can see your information",
          body: ["By default, only you."],
          list: [
            "Doctors and others see information only when you choose to send or share it, by email or by a QR link. You can stop a QR link at any time.",
            "Family: if you add a relative, you control their profile until they join. When a relative claims a profile, they decide whether you stay on as a helper. A helper can view, add and share documents, but can never edit or delete them, and the relative can end that access at any time.",
            "CareQuill staff do not browse your records. Access for support or security is limited and logged.",
          ],
        },
        {
          title: "How we protect it",
          body: [
            "Passwords are hashed. We require strong passwords. Access to every record is checked on the server so one account can never open another's data. Shared links use long random tokens and expire. Uploaded files are validated and stored separately from the database.",
            "No system is perfectly secure. If a breach affecting your data occurs, we will tell you without undue delay.",
          ],
        },
        {
          title: "Your choices and rights",
          body: ["You are in control of your data."],
          list: [
            "Download a full copy of your records from Settings.",
            "Correct or delete any record or document at any time.",
            "Delete your account and all associated data permanently from Settings.",
            "Withdraw consent by deleting your account.",
          ],
        },
        {
          title: "How long we keep it",
          body: [
            "We keep your information while your account is open. When you delete your account, your records and uploaded files are removed. Short-lived security logs may remain briefly for abuse prevention.",
          ],
        },
        {
          title: "Children",
          body: [
            "CareQuill is for adults. A parent or guardian may add a child's records as a family profile and is responsible for them.",
          ],
        },
        {
          title: "Changes to this policy",
          body: [
            "If we make a significant change, we will update the date above and, where needed, ask you to agree again.",
          ],
        },
      ]}
    />
  );
}
