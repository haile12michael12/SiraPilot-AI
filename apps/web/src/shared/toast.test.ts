import { expect, it } from "vitest";
import { ApiError } from "@job-tracker/shared/api";
import { describeError } from "./toast";

it("uses a safe authentication message for account and API-key failures", () => {
  expect(
    describeError(new ApiError(401, "Invalid email or password.", { code: "unauthorized" })),
  ).toBe("Request failed (401): Authentication failed. Check your sign-in details or API key.");
});
