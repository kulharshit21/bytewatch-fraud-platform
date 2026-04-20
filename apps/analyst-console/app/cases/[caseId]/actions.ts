"use server";

import { revalidatePath } from "next/cache";

import { postJson } from "@/lib/api";

export async function submitFeedback(
  caseId: string,
  feedbackLabel: string,
  formData: FormData,
) {
  const notes = formData.get("notes");
  const analystId = formData.get("analystId");

  await postJson(`/cases/${caseId}/feedback`, {
    analyst_id: typeof analystId === "string" && analystId.trim() ? analystId : "analyst_demo",
    feedback_label: feedbackLabel,
    notes: typeof notes === "string" && notes.trim() ? notes : null,
  });

  revalidatePath("/cases");
  revalidatePath(`/cases/${caseId}`);
  revalidatePath("/overview");
}
