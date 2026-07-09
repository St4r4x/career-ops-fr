"use client";

import { useState } from "react";

type FieldConfig = { key: string; label: string; type?: "text" | "number" };
type Row = Record<string, string>;

export function EditableListForm({
  entries,
  fields,
  emptyEntry,
  onSave,
  onCancel,
}: {
  entries: Row[];
  fields: FieldConfig[];
  emptyEntry: Row;
  onSave: (rows: Row[]) => void;
  onCancel: () => void;
}) {
  const [rows, setRows] = useState<Row[]>(entries);

  function updateRow(index: number, key: string, value: string) {
    setRows((prev) => prev.map((row, i) => (i === index ? { ...row, [key]: value } : row)));
  }

  return (
    <div className="flex flex-col gap-2">
      {rows.map((row, i) => (
        <div
          key={i}
          className="flex gap-2 items-end rounded-lg p-2 bg-background border border-border"
        >
          {fields.map((f) => (
            <label key={f.key} className="text-xs text-primary flex-1">
              {f.label}
              <input
                type={f.type ?? "text"}
                value={row[f.key] ?? ""}
                onChange={(e) => updateRow(i, f.key, e.target.value)}
                className="mt-1 w-full text-sm rounded px-2 py-1 bg-card border border-border text-foreground"
              />
            </label>
          ))}
          <button
            type="button"
            onClick={() => setRows((prev) => prev.filter((_, idx) => idx !== i))}
            className="text-xs text-destructive px-2 py-1.5"
          >
            🗑
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={() => setRows((prev) => [...prev, { ...emptyEntry }])}
        className="text-xs px-3 py-1.5 rounded-lg border border-dashed border-border text-muted-foreground hover:text-foreground self-start"
      >
        + Ajouter
      </button>
      <div className="flex gap-2 mt-1">
        <button
          type="button"
          onClick={() => onSave(rows)}
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
