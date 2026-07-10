"use client";

export function TextEditBody({
  isEditing,
  draft,
  setDraft,
  value,
  emptyLabel,
  rows,
  onSave,
  onCancel,
}: {
  isEditing: boolean;
  draft: string;
  setDraft: (value: string) => void;
  value: string;
  emptyLabel: string;
  rows: number;
  onSave: () => void;
  onCancel: () => void;
}) {
  if (!isEditing) {
    return (
      <p className="text-sm text-muted-foreground whitespace-pre-wrap">
        {value || emptyLabel}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        rows={rows}
        className="w-full text-sm rounded-lg px-3 py-2 bg-background border border-border text-foreground focus:outline-none focus:border-primary"
      />
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onSave}
          className="text-xs px-3 py-1.5 rounded-lg font-medium bg-primary text-primary-foreground hover:opacity-90"
        >
          Enregistrer
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="text-xs px-3 py-1.5 rounded-lg font-medium bg-background border border-border text-foreground hover:bg-card"
        >
          Annuler
        </button>
      </div>
    </div>
  );
}
