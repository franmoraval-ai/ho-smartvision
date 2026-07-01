"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CameraThumbnail } from "@/components/camera-thumbnail";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api, type Camera, type Property } from "@/lib/api";

export default function CamerasPage() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [c, p] = await Promise.all([
          api.cameras.list(),
          api.properties.list(),
        ]);
        if (!active) return;
        setCameras(c);
        setProperties(p);
      } catch (e) {
        if (active) setError((e as Error).message);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const propertyName = useMemo(() => {
    const map = new Map(properties.map((p) => [p.id, p.name]));
    return (id: string) => map.get(id) ?? "Sin propiedad";
  }, [properties]);

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-brand-gradient">Cámaras</h2>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Todas las cámaras configuradas y su estado.
          </p>
        </div>
        <Link href="/dashboard/cameras/new">
          <Button>＋ Agregar cámara</Button>
        </Link>
      </header>

      {error && (
        <p className="mb-4 text-sm text-[var(--color-destructive)]">{error}</p>
      )}
      {loading && (
        <p className="text-sm text-[var(--color-muted-foreground)]">Cargando…</p>
      )}

      {!loading && cameras.length === 0 && (
        <Card>
          <CardContent className="p-6 text-sm text-[var(--color-muted-foreground)]">
            No hay cámaras todavía. Usa{" "}
            <Link
              href="/dashboard/cameras/new"
              className="font-medium text-[var(--color-primary)] underline"
            >
              Agregar cámara
            </Link>{" "}
            para descubrir dispositivos ONVIF o configurar una por RTSP.
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cameras.map((cam, i) => (
          <Card
            key={cam.id}
            className="card-hover animate-in overflow-hidden"
            style={{ animationDelay: `${i * 60}ms` }}
          >
            <Link href={`/dashboard/cameras/${cam.id}/live`} className="block">
              <CameraThumbnail cameraId={cam.id} active={cam.is_active} />
            </Link>
            <CardHeader>
              <div className="flex items-start justify-between gap-2">
                <CardTitle className="text-base">{cam.name}</CardTitle>
                <Badge variant={cam.is_active ? "success" : "muted"}>
                  {cam.is_active ? "Activa" : "Inactiva"}
                </Badge>
              </div>
              <CardDescription>{propertyName(cam.property_id)}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-1 text-xs text-[var(--color-muted-foreground)]">
              {cam.onvif_ip && <p>ONVIF: {cam.onvif_ip}</p>}
              {cam.rtsp_url && (
                <p className="truncate" title={cam.rtsp_url}>
                  RTSP: {cam.rtsp_url}
                </p>
              )}
              {cam.gateway_id && <p>Gateway vinculado</p>}
              <Link href={`/dashboard/cameras/${cam.id}/live`} className="mt-3">
                <Button variant="outline" size="sm" className="w-full">
                  ▶ Ver en vivo
                </Button>
              </Link>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
