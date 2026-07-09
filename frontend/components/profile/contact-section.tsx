"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { ProfileContact } from "@/lib/types";
import { redirectOnUnauthenticated } from "@/lib/api-errors";
import { ContactEditForm } from "@/components/profile/contact-edit-form";

async function saveContact(contact: ProfileContact): Promise<void> {
  const res = await fetch("/api/profile/contact", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(contact),
  });
  redirectOnUnauthenticated(res);
  if (!res.ok) throw new Error("failed to save contact");
}

function withProtocol(url: string): string {
  return url.startsWith("http") ? url : `https://${url}`;
}

export function ContactSection({ contact }: { contact: ProfileContact }) {
  const [isEditing, setIsEditing] = useState(false);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: saveContact,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profile"] }),
  });

  return (
    <div className="rounded-xl p-5 mb-4 bg-card border border-border">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-semibold">Coordonnées</p>
        <div className="flex items-center gap-2">
          {mutation.isSuccess && !isEditing && (
            <span className="text-xs text-primary">✓ Enregistré</span>
          )}
          <button
            type="button"
            onClick={() => {
              mutation.reset();
              setIsEditing((v) => !v);
            }}
            className="text-xs text-primary hover:underline"
          >
            {isEditing ? "Annuler" : "Modifier"}
          </button>
        </div>
      </div>
      {isEditing ? (
        <ContactEditForm
          contact={contact}
          onSave={(fields) => {
            mutation.mutate(fields);
            setIsEditing(false);
          }}
          onCancel={() => setIsEditing(false)}
        />
      ) : (
        <div className="grid grid-cols-2 gap-2 text-sm">
          {contact.email && <p>✉ {contact.email}</p>}
          {contact.phone && <p>☎ {contact.phone}</p>}
          {contact.location && <p>📍 {contact.location}</p>}
          {contact.linkedin && (
            <a href={withProtocol(contact.linkedin)} className="text-primary hover:underline">
              in {contact.linkedin}
            </a>
          )}
          {contact.github && (
            <a href={withProtocol(contact.github)} className="text-primary hover:underline">
              ⌥ {contact.github}
            </a>
          )}
        </div>
      )}
    </div>
  );
}
