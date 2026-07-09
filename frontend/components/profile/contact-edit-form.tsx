"use client";

import { useState } from "react";
import type { ProfileContact } from "@/lib/types";

const FIELD_LABEL: Record<keyof ProfileContact, string> = {
  name: "Nom",
  title: "Titre",
  email: "Email",
  phone: "Téléphone",
  location: "Localisation",
  linkedin: "LinkedIn",
  github: "GitHub",
};

export function ContactEditForm({
  contact,
  onSave,
  onCancel,
}: {
  contact: ProfileContact;
  onSave: (contact: ProfileContact) => void;
  onCancel: () => void;
}) {
  const [fields, setFields] = useState<ProfileContact>(contact);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSave(fields);
      }}
      className="grid grid-cols-2 gap-3"
    >
      {(Object.keys(FIELD_LABEL) as (keyof ProfileContact)[]).map((key) => (
        <label key={key} className="text-xs text-primary">
          {FIELD_LABEL[key]}
          <input
            value={fields[key]}
            onChange={(e) => setFields((f) => ({ ...f, [key]: e.target.value }))}
            className="mt-1 w-full text-sm rounded-lg px-3 py-2 bg-background border border-border text-foreground focus:outline-none focus:border-primary"
          />
        </label>
      ))}
      <div className="flex gap-2 mt-1 col-span-2">
        <button
          type="submit"
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
    </form>
  );
}
