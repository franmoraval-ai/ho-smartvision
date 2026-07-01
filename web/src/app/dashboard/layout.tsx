import { redirect } from "next/navigation";
import { Sidebar } from "@/components/sidebar";
import { createClient } from "@/lib/supabase/server";

/**
 * Layout protegido del panel de técnicos. Verifica la sesión en el servidor
 * y renderiza la navegación lateral persistente.
 */
export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar email={user.email ?? null} />
      <main className="flex-1 overflow-y-auto bg-[var(--color-muted)] p-8">
        {children}
      </main>
    </div>
  );
}
