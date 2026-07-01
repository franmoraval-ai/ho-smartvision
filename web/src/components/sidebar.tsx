"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: "▦" },
  { href: "/dashboard/clients", label: "Clientes", icon: "👥" },
  { href: "/dashboard/cameras", label: "Cámaras", icon: "📷" },
  { href: "/dashboard/cameras/new", label: "Agregar cámara", icon: "＋" },
  { href: "/dashboard/events", label: "Eventos", icon: "🔔" },
] as const;

export function Sidebar({ email }: { email: string | null }) {
  const pathname = usePathname();
  const router = useRouter();

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.replace("/login");
    router.refresh();
  }

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-card)] p-4">
      <div className="mb-6 flex items-center gap-3 px-1">
        <div className="bg-brand-gradient flex h-10 w-10 items-center justify-center rounded-xl text-lg shadow-md shadow-[oklch(0.55_0.2_262_/_0.35)]">
          👁️
        </div>
        <div>
          <h1 className="text-lg font-bold leading-tight text-brand-gradient">
            Ho smartvision
          </h1>
          <p className="text-xs text-[var(--color-muted-foreground)]">
            Panel de técnicos
          </p>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1">
        {NAV_ITEMS.map((item) => {
          // "/dashboard" debe coincidir exacto; el resto por prefijo.
          const active =
            item.href === "/dashboard"
              ? pathname === item.href
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-[var(--radius)] px-3 py-2 text-sm font-medium transition-all",
                active
                  ? "bg-brand-gradient text-[var(--color-primary-foreground)] shadow-md shadow-[oklch(0.55_0.2_262_/_0.3)]"
                  : "text-[var(--color-foreground)] hover:bg-[var(--color-muted)]",
              )}
            >
              <span aria-hidden>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-4 border-t border-[var(--color-border)] pt-4">
        {email && (
          <p
            className="mb-2 truncate px-2 text-xs text-[var(--color-muted-foreground)]"
            title={email}
          >
            {email}
          </p>
        )}
        <button
          onClick={handleSignOut}
          className="w-full rounded-[var(--radius)] px-3 py-2 text-left text-sm font-medium text-[var(--color-destructive)] transition-colors hover:bg-[var(--color-muted)]"
        >
          Cerrar sesión
        </button>
      </div>
    </aside>
  );
}
