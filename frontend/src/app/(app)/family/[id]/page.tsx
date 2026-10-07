import { Suspense } from "react";

import { FamilyMemberView } from "@/features/family/family-member-view";

export default function FamilyMemberPage() {
  return (
    <Suspense fallback={null}>
      <FamilyMemberView />
    </Suspense>
  );
}
