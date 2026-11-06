import { ProfileCollectionManager } from "@/features/career-profile/components/ProfileCollectionManager";

export function EducationManager() {
  return (
    <ProfileCollectionManager
      title="Education"
      collection="education"
      fields={[
        { name: "institution", label: "Institution", required: true },
        { name: "degree", label: "Degree" },
        { name: "field_of_study", label: "Field of study" },
        { name: "start_date", label: "Start date", type: "date" },
        { name: "end_date", label: "End date", type: "date" },
        { name: "description", label: "Description", type: "textarea" },
      ]}
    />
  );
}