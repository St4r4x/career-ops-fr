"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { CvEducation } from "@/lib/types";
import { redirectOnUnauthenticated } from "@/lib/api-errors";
import { EditableListForm } from "@/components/profile/editable-list-form";

async function saveEducation(
  lang: "fr" | "en",
  entries: { degree: string; school: string; year: number | null }[],
): Promise<void> {
  const res = await fetch(`/api/profile/cv/education?lang=${lang}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(entries),
  });
  redirectOnUnauthenticated(res);
  if (!res.ok) throw new Error("failed to save education");
}

export function CvEducationSection({
  education,
  lang,
}: {
  education: CvEducation[];
  lang: "fr" | "en";
}) {
  const [isEditing, setIsEditing] = useState(false);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (entries: { degree: string; school: string; year: number | null }[]) =>
      saveEducation(lang, entries),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profile"] }),
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-semibold">Formation</p>
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
        <EditableListForm
          entries={education.map((e) => ({
            degree: e.degree,
            school: e.school,
            year: e.year != null ? String(e.year) : "",
          }))}
          fields={[
            { key: "degree", label: "Diplôme" },
            { key: "school", label: "École" },
            { key: "year", label: "Année", type: "number" },
          ]}
          emptyEntry={{ degree: "", school: "", year: "" }}
          onSave={(rows) => {
            mutation.mutate(
              rows
                .filter((r) => r.degree.trim())
                .map((r) => ({
                  degree: r.degree,
                  school: r.school,
                  year: r.year ? Number(r.year) : null,
                })),
            );
            setIsEditing(false);
          }}
          onCancel={() => setIsEditing(false)}
        />
      ) : education.length === 0 ? (
        <p className="text-sm text-muted-foreground">Aucune formation.</p>
      ) : (
        <div className="space-y-1">
          {education.map((e) => (
            <p key={e.id} className="text-sm">
              {e.degree} — {e.school} {e.year ? `(${e.year})` : ""}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
