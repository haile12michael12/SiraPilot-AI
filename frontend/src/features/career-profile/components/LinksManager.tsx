import { ProfileCollectionManager } from "@/features/career-profile/components/ProfileCollectionManager";

export function LinksManager() {
  return (
    <ProfileCollectionManager
      title="Professional links"
      collection="links"
      fields={[
        { name: "label", label: "Label", required: true },
        { name: "url", label: "URL", type: "url", required: true },
      ]}
    />
  );
}