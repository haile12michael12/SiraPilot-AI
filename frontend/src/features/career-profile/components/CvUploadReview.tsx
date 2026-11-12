import { useEffect, useState } from "react";
import { FileUp, Trash2 } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { apiRequest } from "@/features/auth/services/auth-api";

type Proposal = {
  id: string;
  category: string;
  title: string;
  organization: string | null;
  confidence: number;
};

type CvDocument = {
  id: string;
  original_filename: string;
  status: string;
  items: Proposal[];
};

export function CvUploadReview() {
  const [documents, setDocuments] = useState<CvDocument[]>([]);
  const [selected, setSelected] = useState<Record<string, string[]>>({});
  const [error, setError] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [busyDocument, setBusyDocument] = useState("");

  async function loadDocuments() {
    setDocuments(await apiRequest<CvDocument[]>("/career-profile/cv"));
  }

  useEffect(() => {
    let active = true;
    void apiRequest<CvDocument[]>("/career-profile/cv")
      .then((result) => {
        if (active) setDocuments(result);
      })
      .catch(() => {
        if (active) setError("CV documents could not be loaded.");
      });
    return () => {
      active = false;
    };
  }, []);

  async function upload(file?: File) {
    if (!file) return;
    setError("");
    setIsUploading(true);
    try {
      const body = new FormData();
      body.append("file", file);
      const document = await apiRequest<CvDocument>("/career-profile/cv", {
        method: "POST",
        body,
      });
      setDocuments((current) => [document, ...current]);
      setSelected((current) => ({
        ...current,
        [document.id]: document.items.map((item) => item.id),
      }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The CV could not be uploaded.");
    } finally {
      setIsUploading(false);
    }
  }

  async function reviewAction(document: CvDocument, action: "approve" | "reject") {
    setError("");
    setBusyDocument(document.id);
    try {
      if (action === "approve") {
        const itemIds = selected[document.id] ?? [];
        if (itemIds.length === 0) {
          setError("Select at least one proposal to approve.");
          return;
        }
        await apiRequest(`/career-profile/cv/${document.id}/approve`, {
          method: "POST",
          body: JSON.stringify({ item_ids: itemIds }),
        });
      } else {
        await apiRequest(`/career-profile/cv/${document.id}/reject`, { method: "POST" });
      }
      await loadDocuments();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The CV review could not be saved.");
    } finally {
      setBusyDocument("");
    }
  }

  async function removeDocument(document: CvDocument) {
    setBusyDocument(document.id);
    try {
      await apiRequest(`/career-profile/cv/${document.id}`, { method: "DELETE" });
      setDocuments((current) => current.filter((entry) => entry.id !== document.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The document could not be removed.");
    } finally {
      setBusyDocument("");
    }
  }

  return (
    <section className="space-y-4 border-b border-border pb-7">
      <div>
        <h2 className="text-lg font-semibold">CV import</h2>
        <p className="mt-1 text-sm text-muted-foreground">Extracted details stay in review until you choose what to add.</p>
      </div>
      <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-border px-3 py-2 text-sm font-medium hover:bg-accent">
        <FileUp size={16} aria-hidden="true" />
        {isUploading ? "Uploading…" : "Upload PDF or DOCX"}
        <input className="sr-only" type="file" accept="application/pdf,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx" disabled={isUploading} onChange={(event) => { void upload(event.target.files?.[0]); event.currentTarget.value = ""; }} />
      </label>
      {error && <p className="text-sm text-destructive" role="alert">{error}</p>}
      <div className="space-y-4">
        {documents.map((document) => (
          <article key={document.id} className="border-t border-border pt-4">
            <header className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-medium">{document.original_filename}</h3>
                <p className="mt-0.5 text-xs capitalize text-muted-foreground">{document.status} · {document.items.length} proposed items</p>
              </div>
              <Button type="button" variant="ghost" size="icon" aria-label={`Delete ${document.original_filename}`} title="Delete document" onClick={() => void removeDocument(document)} disabled={busyDocument === document.id}>
                <Trash2 size={16} aria-hidden="true" />
              </Button>
            </header>
            {document.status === "review" && (
              <>
                <ul className="mt-3 divide-y divide-border">
                  {document.items.map((item) => {
                    const checked = (selected[document.id] ?? []).includes(item.id);
                    return (
                      <li key={item.id} className="flex items-start gap-3 py-2.5">
                        <input className="mt-1" type="checkbox" checked={checked} aria-label={`Approve ${item.title}`} onChange={(event) => setSelected((current) => {
                          const existing = current[document.id] ?? [];
                          return { ...current, [document.id]: event.target.checked ? [...existing, item.id] : existing.filter((id) => id !== item.id) };
                        })} />
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium">{item.title}</p>
                          <p className="text-xs capitalize text-muted-foreground">{item.category}{item.organization ? ` · ${item.organization}` : ""} · {item.confidence}% match</p>
                        </div>
                      </li>
                    );
                  })}
                </ul>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button type="button" size="sm" disabled={busyDocument === document.id} onClick={() => void reviewAction(document, "approve")}>Approve selected</Button>
                  <Button type="button" size="sm" variant="outline" disabled={busyDocument === document.id} onClick={() => void reviewAction(document, "reject")}>Discard proposals</Button>
                </div>
              </>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}