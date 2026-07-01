"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api, type Camera } from "@/lib/api";

interface Stats {
  clients: number;
  properties: number;
  cameras: number;
  activeCameras: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [clients, properties, cameras] = await Promise.all([
          api.clients.list(),
          api.properties.list(),
          api.cameras.list(),
        ]);
        if (!active) return;
        setStats({
          clients: clients.length,
          properties: properties.length,
          cameras: cameras.length,
          activeCameras: cameras.filter((c: Camera) => c.is_active).length,
        });
      } catch (e) {
        if (active) setError((e as Error).message);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const cards: { label: string; value: number | undefined; hint: string }[] = [
    { label: "Clientes", value: stats?.clients, hint: "registrados" },
    { label: "Propiedades", value: stats?.properties, hint: "gestionadas" },
    { label: "Cámaras", value: stats?.cameras, hint: "en total" },
    {
      label: "Cámaras activas",
      value: stats?.activeCameras,
      hint: "transmitiendo",
    },
  ];

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Dashboard</h2>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Resumen general del sistema.
          </p>
        </div>
        <Link href="/dashboard/cameras/new">
          <Button>＋ Agregar cámara</Button>
        </Link>
      </header>

      {error && (
        <p className="mb-4 text-sm text-[var(--color-destructive)]">
          No se pudo cargar la información: {error}
        </p>
      )}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((c) => (
          <Card key={c.label}>
            <CardHeader>
              <CardDescription>{c.label}</CardDescription>
              <CardTitle className="text-3xl">
                {c.value ?? "—"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-[var(--color-muted-foreground)]">
                {c.hint}
              </p>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Acciones rápidas</CardTitle>
            <CardDescription>Tareas frecuentes de instalación.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <Link href="/dashboard/cameras/new">
              <Button variant="outline" className="w-full justify-start">
                📷 Descubrir y agregar cámaras ONVIF
              </Button>
            </Link>
            <Link href="/dashboard/clients">
              <Button variant="outline" className="w-full justify-start">
                👥 Registrar un nuevo cliente
              </Button>
            </Link>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
