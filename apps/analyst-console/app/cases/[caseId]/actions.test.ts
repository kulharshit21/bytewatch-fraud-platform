import { revalidatePath } from "next/cache";

import { submitFeedback } from "@/app/cases/[caseId]/actions";
import { postJson } from "@/lib/api";

vi.mock("next/cache", () => ({
  revalidatePath: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  postJson: vi.fn().mockResolvedValue({
    data: { status: "recorded" },
    error: null,
  }),
}));

describe("submitFeedback", () => {
  it("posts analyst feedback and revalidates affected routes", async () => {
    const formData = new FormData();
    formData.set("analystId", "analyst_42");
    formData.set("notes", "confirmed mule account behavior");

    await submitFeedback("case-123", "fraud", formData);

    expect(postJson).toHaveBeenCalledWith("/cases/case-123/feedback", {
      analyst_id: "analyst_42",
      feedback_label: "fraud",
      notes: "confirmed mule account behavior",
    });
    expect(revalidatePath).toHaveBeenCalledWith("/cases");
    expect(revalidatePath).toHaveBeenCalledWith("/cases/case-123");
    expect(revalidatePath).toHaveBeenCalledWith("/overview");
  });
});
