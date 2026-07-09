import { redirect } from "next/navigation";
import { DashboardNav } from "@/components/dashboard-nav";
import { StatsClient } from "@/components/stats/stats-client";
import { getSessionUser } from "@/lib/session";

export default async function StatsPage() {
  const user = await getSessionUser();
  if (!user) {
    redirect("/login");
  }

  return (
    <div className="flex flex-col h-screen">
      <DashboardNav email={user.email} activePath="/stats" />
      <div className="flex-1 min-h-0">
        <StatsClient />
      </div>
    </div>
  );
}
