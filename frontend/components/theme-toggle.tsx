"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

const STORAGE_KEY = "diggo-theme";

export function ThemeToggle() {
  const [isLight, setIsLight] = useState(false);

  useEffect(() => {
    // ponytail: syncing from an external system (DOM class set by the
    // pre-hydration bootstrap script in layout.tsx), not derived state.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsLight(document.documentElement.classList.contains("light"));
  }, []);

  function toggle() {
    const next = !isLight;
    document.documentElement.classList.toggle("light", next);
    localStorage.setItem(STORAGE_KEY, next ? "light" : "dark");
    setIsLight(next);
  }

  return (
    <Button variant="outline" size="sm" onClick={toggle}>
      {isLight ? "Mode sombre" : "Mode clair"}
    </Button>
  );
}
