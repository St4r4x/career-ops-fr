"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { redirectOnUnauthenticated } from "@/lib/api-errors";

async function saveText(profileMd: string): Promise<void> {
  const res = await fetch("/api/profile/text", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile_md: profileMd }),
  });
  redirectOnUnauthenticated(res);
  if (!res.ok) throw new Error("failed to save résumé");
}

export function SummarySection({ profileMd }: { profileMd: string }) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(profileMd);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: saveText,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profile"] }),
  });

  return (
    <div className="rounded-xl p-5 mb-4 bg-card border border-border">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-semibold">Résumé</p>
        <div className="flex items-center gap-2">
          {mutation.isSuccess && !isEditing && (
            <span className="text-xs text-primary">✓ Enregistré</span>
          )}
          <button
            type="button"
            onClick={() => {
              mutation.reset();
              if (!isEditing) setDraft(profileMd);
              setIsEditing((v) => !v);
            }}
            className="text-xs text-primary hover:underline"
          >
            {isEditing ? "Annuler" : "Modifier"}
          </button>
        </div>
      </div>
      {isEditing ? (
        <div className="flex flex-col gap-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={6}
            className="w-full text-sm rounded-lg px-3 py-2 bg-background border border-border text-foreground focus:outline-none focus:border-primary"
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                mutation.mutate(draft);
                setIsEditing(false);
              }}
              className="text-xs px-3 py-1.5 rounded-lg font-medium bg-primary text-primary-foreground hover:opacity-90"
            >
              Enregistrer
            </button>
            <button
              type="button"
              onClick={() => setIsEditing(false)}
              className="text-xs px-3 py-1.5 rounded-lg font-medium bg-background border border-border text-foreground hover:bg-card"
            >
              Annuler
            </button>
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground whitespace-pre-wrap">
          {profileMd || "Aucun résumé."}
        </p>
      )}
    </div>
  );
}
