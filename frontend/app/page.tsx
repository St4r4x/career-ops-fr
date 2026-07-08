import type { Metadata } from "next";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ThemeToggle } from "@/components/theme-toggle";

export const metadata: Metadata = {
  title: "Diggo — Candidatures IA pour le marché français",
  description:
    "Diggo scanne les offres, les note selon ton profil et prépare ton dossier de candidature complet en un clic, grâce à l'IA.",
};

async function isAuthenticated(): Promise<boolean> {
  const headersList = await headers();
  const cookie = headersList.get("cookie") ?? "";
  const apiUrl = process.env.INTERNAL_API_URL ?? "http://api:8000";
  try {
    const res = await fetch(`${apiUrl}/api/me`, {
      headers: { cookie },
      cache: "no-store",
    });
    return res.ok;
  } catch {
    return false;
  }
}

const FEATURES = [
  {
    icon: "✦",
    title: "Dossier de candidature IA",
    body: "CV recentré, lettre de motivation et fiche d'entretien générés automatiquement pour chaque offre, en français ou en anglais.",
  },
  {
    icon: "🔍",
    title: "Scan automatique des offres",
    body: "APEC, LinkedIn, Welcome to the Jungle et les principales plateformes de recrutement — les offres arrivent directement dans ton tableau de bord.",
  },
  {
    icon: "📊",
    title: "Scoring des offres",
    body: "Chaque offre est notée A–F selon ton profil, tes critères de recherche et la qualité de l'annonce. Les meilleures remontent en tête.",
  },
  {
    icon: "📅",
    title: "Suivi des statuts et relances",
    body: 'Chaque candidature passe de "À envoyer" à "Offre reçue". Les relances en retard remontent automatiquement.',
  },
];

const STEPS = [
  {
    label: "Connecte ton profil",
    body: "Renseigne ton CV, tes expériences et tes critères de recherche une seule fois.",
  },
  {
    label: "Scan automatique",
    body: "Diggo cherche les offres qui correspondent à ton profil sur les principaux portails français.",
  },
  {
    label: "Prépare ta candidature en un clic",
    body: "L'IA génère ton dossier complet adapté à l'offre. Tu télécharges, tu envoies.",
  },
];

export default async function LandingPage() {
  if (await isAuthenticated()) {
    redirect("/candidatures");
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <nav className="flex items-center px-6 py-3 border-b border-border">
        <span className="font-bold text-lg">Diggo</span>
        <div className="ml-auto flex items-center gap-3">
          <ThemeToggle />
          <Link
            href="/login"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Se connecter
          </Link>
          <Link href="/signup" className={buttonVariants({ size: "sm" })}>
            Créer un compte
          </Link>
        </div>
      </nav>

      <section className="max-w-3xl mx-auto px-6 py-20 text-center">
        <h1 className="text-4xl font-bold leading-tight mb-4">
          <span className="text-primary">
            CV, lettre de motivation et fiche d&apos;entretien
          </span>
          <br />
          générés sur mesure pour chaque offre
        </h1>
        <p className="text-muted-foreground text-lg mb-10">
          Diggo scanne les offres, les note selon ton profil et prépare ton
          dossier de candidature complet en un clic — grâce à l&apos;IA.
        </p>
        <div className="flex items-center justify-center gap-4">
          <Link href="/signup" className={buttonVariants({ size: "lg" })}>
            Créer un compte
          </Link>
          <Link
            href="/login"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Se connecter →
          </Link>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 pb-16 grid grid-cols-1 sm:grid-cols-2 gap-4">
        {FEATURES.map((f) => (
          <Card key={f.title}>
            <CardContent>
              <div className="text-2xl mb-3">{f.icon}</div>
              <h3 className="font-semibold mb-1">{f.title}</h3>
              <p className="text-sm text-muted-foreground">{f.body}</p>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="max-w-3xl mx-auto px-6 pb-20 text-center">
        <h2 className="text-2xl font-bold mb-10">Comment ça marche</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {STEPS.map((s, i) => (
            <div key={s.label}>
              <div className="text-3xl font-bold text-primary mb-2">
                {i + 1}
              </div>
              <p className="text-sm font-medium mb-1">{s.label}</p>
              <p className="text-xs text-muted-foreground">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-border py-12 text-center">
        <p className="text-muted-foreground mb-6 text-sm">
          Prêt à optimiser ta recherche d&apos;emploi ?
        </p>
        <Link href="/signup" className={buttonVariants({ size: "lg" })}>
          Créer un compte gratuitement
        </Link>
      </footer>
    </main>
  );
}
