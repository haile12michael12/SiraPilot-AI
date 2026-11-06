import { ProfileCollectionManager } from "@/features/career-profile/components/ProfileCollectionManager";

export function SkillsManager() {
  return (
    <ProfileCollectionManager
      title="Skills"
      collection="skills"
      fields={[
        { name: "name", label: "Skill", required: true },
        {
          name: "proficiency_level",
          label: "Proficiency",
          type: "select",
          required: true,
          options: ["beginner", "intermediate", "advanced", "expert"],
        },
      ]}
    />
  );
}