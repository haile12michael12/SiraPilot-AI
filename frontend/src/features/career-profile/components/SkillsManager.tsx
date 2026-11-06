export function SkillsManager() {
  return <ProfileSection title="Skills" description="Capture the strengths and tools you bring to your work." />;
}

function ProfileSection({ title, description }: { title: string; description: string }) {
  return (
    <section className="space-y-1 border-b border-border pb-6">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="text-sm text-muted-foreground">{description}</p>
    </section>
  );
}