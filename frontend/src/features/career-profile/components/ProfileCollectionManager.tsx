import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/shared/ui/button";
import { apiRequest } from "@/features/auth/services/auth-api";

export type ProfileField = {
  name: string;
  label: string;
  type?: "text" | "date" | "url" | "textarea" | "select";
  required?: boolean;
  options?: string[];
};

type ProfileItem = {
  id: string;
  name?: string;
  title?: string;
  institution?: string;
  company?: string;
  issuer?: string | null;
  field_of_study?: string | null;
  role?: string | null;
  label?: string;
  [key: string]: string | boolean | null | undefined;
};

export function ProfileCollectionManager({
  title,
  collection,
  fields,
}: {
  title: string;
  collection: string;
  fields: ProfileField[];
}) {
  const [items, setItems] = useState<ProfileItem[]>([]);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  async function loadItems() {
    setItems(await apiRequest<ProfileItem[]>(`/career-profile/entries/${collection}`));
  }

  useEffect(() => {
    let active = true;
    void apiRequest<ProfileItem[]>(`/career-profile/entries/${collection}`)
      .then((result) => {
        if (active) setItems(result);
      })
      .catch(() => {
        if (active) setError(`${title} could not be loaded.`);
      });
    return () => {
      active = false;
    };
  }, [collection, title]);

  function resetForm() {
    setDraft({});
    setEditingId(null);
  }

  function editItem(item: ProfileItem) {
    setDraft(
      Object.fromEntries(
        fields.map(({ name }) => [name, item[name] == null ? "" : String(item[name])]),
      ),
    );
    setEditingId(item.id);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSaving(true);
    const body = Object.fromEntries(
      fields.map(({ name }) => [name, draft[name]?.trim() || null]),
    );
    try {
      const path = `/career-profile/entries/${collection}${editingId ? `/${editingId}` : ""}`;
      await apiRequest(path, {
        method: editingId ? "PATCH" : "POST",
        body: JSON.stringify(body),
      });
      await loadItems();
      resetForm();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : `${title} could not be saved.`);
    } finally {
      setIsSaving(false);
    }
  }

  async function removeItem(id: string) {
    setError("");
    try {
      await apiRequest(`/career-profile/entries/${collection}/${id}`, { method: "DELETE" });
      setItems((current) => current.filter((item) => item.id !== id));
      if (editingId === id) resetForm();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : `${title} could not be removed.`);
    }
  }

  return (
    <section className="space-y-4 border-b border-border pb-7">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold">{title}</h2>
        <span className="text-xs text-muted-foreground">{items.length} {items.length === 1 ? "entry" : "entries"}</span>
      </div>
      {items.length > 0 && (
        <ul className="divide-y divide-border">
          {items.map((item) => {
            const primary = item.name ?? item.title ?? item.institution ?? item.label ?? "Profile entry";
            const secondary = item.company ?? item.issuer ?? item.field_of_study ?? item.role;
            return (
              <li key={item.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{primary}</p>
                  {secondary && <p className="mt-0.5 truncate text-xs text-muted-foreground">{secondary}</p>}
                </div>
                <div className="flex items-center gap-1">
                  <Button type="button" variant="ghost" size="sm" onClick={() => editItem(item)}>Edit</Button>
                  <Button type="button" variant="ghost" size="sm" onClick={() => void removeItem(item.id)}>Remove</Button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
      <form className="grid gap-3 sm:grid-cols-2" onSubmit={(event) => void save(event)}>
        {fields.map((field) => (
          <label key={field.name} className={`block space-y-1.5 text-xs font-medium ${field.type === "textarea" ? "sm:col-span-2" : ""}`}>
            {field.label}
            {field.type === "textarea" ? (
              <textarea className="min-h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-normal" value={draft[field.name] ?? ""} required={field.required} onChange={(event) => setDraft((current) => ({ ...current, [field.name]: event.target.value }))} />
            ) : field.type === "select" ? (
              <select className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm font-normal" value={draft[field.name] ?? ""} required={field.required} onChange={(event) => setDraft((current) => ({ ...current, [field.name]: event.target.value }))}>
                <option value="">Choose a level</option>
                {field.options?.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            ) : (
              <input className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm font-normal" type={field.type ?? "text"} value={draft[field.name] ?? ""} required={field.required} onChange={(event) => setDraft((current) => ({ ...current, [field.name]: event.target.value }))} />
            )}
          </label>
        ))}
        {error && <p className="text-sm text-destructive sm:col-span-2" role="alert">{error}</p>}
        <div className="flex gap-2 sm:col-span-2">
          <Button type="submit" size="sm" disabled={isSaving}>{isSaving ? "Saving…" : editingId ? "Save changes" : `Add ${title.toLowerCase()}`}</Button>
          {editingId && <Button type="button" size="sm" variant="outline" onClick={resetForm}>Cancel</Button>}
        </div>
      </form>
    </section>
  );
}