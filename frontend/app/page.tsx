"use client";

import { useEffect, useState } from "react";
import { ThemeToggle } from "@/components/theme-toggle";

type Me = { sub: string; email: string };

export default function Home() {
  const [me, setMe] = useState<Me | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    fetch("/api/me", { credentials: "include" })
      .then((res) => (res.ok ? res.json() : null))
      .then(setMe)
      .finally(() => setChecked(true));
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-2xl font-bold">Diggo — fondations</h1>
      <p className="text-sm opacity-70">
        {!checked
          ? "Vérification de la session..."
          : me
            ? `Connecté en tant que ${me.email}`
            : "Non connecté"}
      </p>
      <ThemeToggle />
    </main>
  );
}
