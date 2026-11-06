import { ProfileCollectionManager } from "@/features/career-profile/components/ProfileCollectionManager";

export function CertificationManager() {
  return (
    <ProfileCollectionManager
      title="Certifications"
      collection="certifications"
      fields={[
        { name: "name", label: "Certification", required: true },
        { name: "issuer", label: "Issuer" },
        { name: "issued_on", label: "Issue date", type: "date" },
        { name: "expires_on", label: "Expiration date", type: "date" },
        { name: "credential_id", label: "Credential ID" },
        { name: "credential_url", label: "Credential URL", type: "url" },
      ]}
    />
  );
}