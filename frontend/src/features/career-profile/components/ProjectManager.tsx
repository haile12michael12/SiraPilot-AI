import { ProfileCollectionManager } from "@/features/career-profile/components/ProfileCollectionManager";

export function ProjectManager() {
  return (
    <ProfileCollectionManager
      title="Projects"
      collection="projects"
      fields={[
        { name: "name", label: "Project name", required: true },
        { name: "role", label: "Your role" },
        { name: "project_url", label: "Project URL", type: "url" },
        { name: "start_date", label: "Start date", type: "date" },
        { name: "end_date", label: "End date", type: "date" },
        { name: "description", label: "Description", type: "textarea" },
      ]}
    />
  );
}