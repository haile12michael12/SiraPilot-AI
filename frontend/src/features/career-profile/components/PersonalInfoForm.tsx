export function PersonalInfoForm() {
  return (
    <section className="space-y-4 border-b border-border pb-6">
      <div>
        <h2 className="text-lg font-semibold">Personal information</h2>
        <p className="mt-1 text-sm text-muted-foreground">The basics that help shape your career profile.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="space-y-1.5 text-sm font-medium">
          Full name
          <input className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" type="text" autoComplete="name" />
        </label>
        <label className="space-y-1.5 text-sm font-medium">
          Professional headline
          <input className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" type="text" />
        </label>
        <label className="space-y-1.5 text-sm font-medium sm:col-span-2">
          About
          <textarea className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 font-normal" rows={4} />
        </label>
      </div>
    </section>
  );
}