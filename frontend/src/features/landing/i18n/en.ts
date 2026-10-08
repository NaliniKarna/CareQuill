/**
 * English copy for the public landing page. `ne.ts` must match this shape
 * exactly (enforced by the `LandingCopy` type).
 */
export const en = {
  meta: { langLabel: "Language", switchTo: "नेपालीमा हेर्नुहोस्" },
  nav: {
    skip: "Skip to content",
    home: "Home",
    features: "Features",
    howItWorks: "How it works",
    faq: "FAQ",
    contact: "Contact Us",
    login: "Log in",
    signup: "Sign up",
    openMenu: "Open menu",
    closeMenu: "Close menu",
  },
  hero: {
    badge: "Patient-first health records for Nepal and beyond",
    titleTop: "My Medical Records",
    titleBy: "by CareQuill",
    description:
      "Keep your reports, medicines, allergies, conditions, doctors and appointments in one secure place, and walk into every consultation prepared.",
    bullets: [
      "Your whole health story in one secure place: every report, medicine, allergy and doctor",
      "Walk into every consultation prepared, with a clear summary and PDF report for your doctor",
      "AI and OCR do the organising, but nothing is saved until you approve it",
      "Private by design: you own your data and it is never sold",
    ],
    ctaTitle: "Create your account",
    ctaText: "Free to start. Takes less than a minute.",
    signup: "Sign up",
    haveAccount: "Already have an account?",
    login: "Log in",
    imageAlt: "A smiling patient and doctor using the CareQuill app",
    labels: {
      records: "Medical records",
      family: "Family care",
      appointments: "Appointments",
      summary: "Record Summary",
      share: "Share with doctor",
      secure: "Private and secure",
    },
  },
  why: {
    eyebrow: "Why CareQuill",
    title: "Why do we need CareQuill?",
    description:
      "Our mission is simple: every patient should be able to walk into any consultation with their complete, accurate health story, and stay in control of who sees it. Today that story is scattered across paper files, phone galleries and memory. CareQuill brings it together, keeps it accurate, and shares only what you choose.",
    problemsTitle: "Without a health record of your own",
    problems: [
      {
        title: "Scattered records",
        text: "Lab reports, prescriptions and scans live in different files, phones and hospitals.",
      },
      {
        title: "Repeated history",
        text: "You explain the same conditions and medicines to every new doctor.",
      },
      {
        title: "Missed details",
        text: "Allergies, doses and past results are easy to forget when time is short.",
      },
      {
        title: "Family left behind",
        text: "Parents' and children's papers are in someone else's bag, or nowhere at all.",
      },
    ],
    solutionTitle: "With CareQuill",
    solutions: [
      "One secure place for every report, prescription and scan, originals kept untouched",
      "Your conditions, allergies and medicines recorded once, always up to date",
      "A clear summary and PDF report ready before the appointment starts",
      "A family circle to manage records for people you care for",
    ],
    principlesTitle: "What we promise",
    principles: [
      {
        title: "You stay in control",
        text: "Your records belong to you. Export or delete them at any time.",
      },
      {
        title: "AI suggests, you decide",
        text: "OCR and AI only propose. Nothing joins your record until you approve it.",
      },
      {
        title: "No diagnosis, ever",
        text: "CareQuill organises your information. It never diagnoses or recommends treatment.",
      },
      {
        title: "Private by design",
        text: "Your data is never sold and never used for advertising. You choose who sees what.",
      },
    ],
    featuresEyebrow: "Features",
    featuresTitle: "Everything your health record needs",
    featuresText:
      "Each part of CareQuill is built around one idea: your information, organised, accurate and under your control.",
  },
  features: {
    tryIt: "Get started",
    items: {
      dashboard: {
        tag: "Dashboard",
        title: "Your health at a glance",
        text: "The dashboard shows what matters today, so you can see your health in one look.",
        points: [
          "Active medicines, upcoming reminders and appointments in one view",
          "Profile completion bar shows what is still missing",
          "Quick actions to add records, book visits or write a summary",
        ],
      },
      documents: {
        tag: "Medical documents",
        title: "Upload reports, let OCR read them",
        text: "Store lab reports, prescriptions and scans safely. CareQuill reads the text and suggests what to add.",
        points: [
          "Upload PDF, JPG or PNG files; the original is always preserved",
          "OCR and AI suggest medicines, allergies and lab values",
          "Nothing is added until you review and approve it",
        ],
        float: "Suggestion pending your review",
      },
      medications: {
        tag: "Medications",
        title: "Medicines and reminders",
        text: "Keep an accurate list of what you take and get reminded at the right time.",
        points: [
          "Dose, frequency and instructions for every medicine",
          "Daily or custom-day reminders for each dose",
          "Active and past medicines kept separately",
        ],
      },
      conditions: {
        tag: "Conditions and allergies",
        title: "Conditions and allergies, always ready",
        text: "The details every doctor asks first, recorded once and kept up to date.",
        points: [
          "Track conditions as active, managed or resolved",
          "Record allergy severity and your reaction",
          "Included automatically in your summaries and reports",
        ],
      },
      appointments: {
        tag: "Doctors and appointments",
        title: "Doctors and appointments in one place",
        text: "Save your doctors' contacts and keep every visit organised.",
        points: [
          "Doctor profiles with specialisation, clinic and contact details",
          "Upcoming and past appointments with reasons and notes",
          "See every report you have shared with each doctor",
        ],
      },
      summary: {
        tag: "Record Summary",
        title: "A clear summary you approve",
        text: "AI drafts a short, readable summary of your record. You edit it and approve it before anyone sees it.",
        points: [
          "Built only from records you have confirmed",
          "Clear Draft, Reviewed and Shared steps",
          "Never diagnoses or recommends treatment",
        ],
        float: "Draft → Reviewed → Shared",
      },
      share: {
        tag: "Share with your doctor",
        title: "Professional reports, sent securely",
        text: "Choose what to include, preview it, then email the PDF or share it with a QR code.",
        points: [
          "Pick conditions, allergies, medicines and documents to include",
          "Email the PDF with your documents attached as the original files",
          "Or show a QR code that opens the report, and stop it any time",
        ],
        float: "Share by email or QR code",
      },
      family: {
        tag: "Family circle",
        title: "Care for the whole family",
        text: "Keep health records for parents, children and relatives in one circle, and hand them over when they are ready to manage their own.",
        points: [
          "Add family members and upload their reports and prescriptions",
          "Share a family member's report with their doctor in a few taps",
          "Invite code transfers a profile to their own account, and they decide what you keep",
        ],
        float: "You manage, they stay in control",
      },
      journal: {
        tag: "Health journal",
        title: "A private daily journal",
        text: "Note how you feel each day and look back before a visit.",
        points: [
          "Mood, date, title and notes for every entry",
          "Search entries and filter by date",
          "Private: never used by AI and never shared",
        ],
        float: "Only you can see your journal",
      },
      notifications: {
        tag: "Notifications",
        title: "Stay informed",
        text: "Get notified about reminders, processed documents and shared reports.",
        points: [
          "Inbox for reminders and document updates",
          "Choose which notifications you receive",
          "Mark items read when you are done",
        ],
      },
      profile: {
        tag: "Health profile",
        title: "Your health profile",
        text: "Basic details and emergency contacts that make every summary more accurate.",
        points: [
          "Blood group, height, weight and date of birth",
          "Emergency contact details",
          "Used in summaries and reports only when you choose",
        ],
      },
      privacy: {
        tag: "Privacy and data control",
        title: "Your data, your control",
        text: "Health data is sensitive. CareQuill keeps you in charge of it.",
        points: [
          "Download a full copy of your records at any time",
          "Delete your account and data permanently",
          "Your data is never sold or used for advertising",
        ],
        float: "Export or delete anytime",
      },
    },
  },
  how: {
    eyebrow: "How it works",
    title: "How does CareQuill work?",
    text: "Four simple steps from scattered papers to a record your doctor can trust.",
    steps: [
      {
        title: "Create your account",
        text: "Sign up with your email and fill in your basic health profile.",
      },
      {
        title: "Add your records",
        text: "Upload reports and add medicines, allergies, conditions and doctors.",
      },
      {
        title: "Review AI suggestions",
        text: "AI and OCR suggest details. You check them and approve what is correct.",
      },
      {
        title: "Share with your doctor",
        text: "Create a summary or PDF report and email it to your doctor.",
      },
    ],
  },
  faq: {
    eyebrow: "FAQ",
    title: "Frequently asked questions",
    items: [
      {
        q: "Is CareQuill free to use?",
        a: "Yes. You can create an account and start organising your records for free.",
      },
      {
        q: "Does CareQuill diagnose illness or suggest treatment?",
        a: "No. CareQuill organises and summarises the information you provide. It never diagnoses conditions or prescribes treatment. Always consult a qualified doctor for medical decisions.",
      },
      {
        q: "Can AI change my records without asking me?",
        a: "No. Anything AI or OCR extracts is only a suggestion. It becomes part of your record only after you review and approve it.",
      },
      {
        q: "Who can see my health information?",
        a: "Only you. A doctor sees your information only when you choose to send them a report or summary.",
      },
      {
        q: "Which files can I upload?",
        a: "PDF, JPG and PNG files such as lab reports, prescriptions and scans. Your original file is always kept unchanged. X-rays and other images are stored for viewing and are never interpreted by AI.",
      },
      {
        q: "Can I download or delete my data?",
        a: "Yes. From Settings you can download a full copy of your records, or permanently delete your account and data.",
      },
      {
        q: "Is the app available in Nepali?",
        a: "This website is available in English and Nepali. The app itself is in English today, with Nepali support planned.",
      },
    ],
  },
  contact: {
    eyebrow: "Contact Us",
    title: "We are here to help",
    text: "Questions, feedback or partnership ideas? Send us a message.",
    emailLabel: "Email",
    locationLabel: "Location",
    location: "Kathmandu, Nepal",
    hoursLabel: "Response time",
    hours: "Usually within 1–2 working days",
    form: {
      name: "Your name",
      email: "Your email",
      message: "Message",
      messagePlaceholder: "How can we help?",
      submit: "Send message",
      note: "Your message is sent straight to our support team. Please do not include medical details.",
      sending: "Sending…",
      success: "Thank you. Your message has been sent. We will reply by email.",
      failed: "We could not send your message. Please try again, or email us directly at",
      tooMany: "Too many messages from this device. Please try again later.",
      errors: {
        name: "Please enter your name.",
        email: "Please enter a valid email address.",
        message: "Please write a message (at least 10 characters).",
      },
      subject: "CareQuill enquiry from",
    },
  },
  cta: {
    title: "Bring every consultation up to speed",
    text: "Create your free account and start organising your health records today.",
    signup: "Create your account",
    login: "I already have an account",
  },
  footer: {
    tagline: "Your health records, organised and under your control.",
    product: "Product",
    company: "Help",
    account: "Account",
    disclaimer:
      "CareQuill is an organisational and communication tool. It does not diagnose conditions, prescribe treatment or replace professional medical advice. In an emergency, contact your nearest hospital.",
    rights: "All rights reserved.",
    privacy: "Privacy Policy",
    terms: "Terms of Use",
  },
};

export type LandingCopy = typeof en;
