"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { redirectOnUnauthenticated } from "@/lib/api-errors";

async function saveCvMeta(lang: "fr" | "en", summary: string): Promise<void> {
  const res = await fetch(`/api/profile/cv/meta?lang=${lang}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ summary }),
  });
  redirectOnUnauthenticated(res);
  if (!res.ok) throw new Error("failed to save CV summary");
}

export function CvMetaSection({ summary, lang }: { summary: string; lang: "fr" | "en" }) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(summary);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (value: string) => saveCvMeta(lang, value),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profile"] }),
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <p className="text-sm font-semibold">Résumé</p>
        <div className="flex items-center gap-2">
          {mutation.isSuccess && !isEditing && (
            <span className="text-xs text-primary">✓ Enregistré</span>
          )}
          <button
            type="button"
            onClick={() => {
              mutation.reset();
              if (!isEditing) setDraft(summary);
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
            rows={4}
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
          {summary || "Aucun résumé."}
        </p>
      )}
    </div>
  );
}
