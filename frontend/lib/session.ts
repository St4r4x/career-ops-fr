import { headers } from "next/headers";

export async function getSessionUser(): Promise<{ email: string } | null> {
  const headersList = await headers();
  const cookie = headersList.get("cookie") ?? "";
  const apiUrl = process.env.INTERNAL_API_URL ?? "http://api:8000";
  try {
    const res = await fetch(`${apiUrl}/api/me`, {
      headers: { cookie },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
