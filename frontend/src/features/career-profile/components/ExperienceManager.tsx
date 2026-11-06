import { ProfileCollectionManager } from "@/features/career-profile/components/ProfileCollectionManager";

export function ExperienceManager() {
  return (
    <ProfileCollectionManager
      title="Experience"
      collection="experience"
      fields={[
        { name: "title", label: "Job title", required: true },
        { name: "company", label: "Company", required: true },
        { name: "location", label: "Location" },
        { name: "start_date", label: "Start date", type: "date" },
        { name: "end_date", label: "End date", type: "date" },
        { name: "description", label: "Description", type: "textarea" },
      ]}
    />
  );
}