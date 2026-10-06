import { Suspense } from "react";

import { RecordsHub } from "@/features/medical-records/records-hub";

export default function MedicalRecordsPage() {
  return (
    <Suspense fallback={null}>
      <RecordsHub />
    </Suspense>
  );
}
