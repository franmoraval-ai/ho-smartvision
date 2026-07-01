"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EnableNotifications } from "@/components/enable-notifications";
import { Select } from "@/components/ui/select";
import { api, type Camera, type CameraEvent } from "@/lib/api";

/** Metadatos visuales por tipo de evento (icono, etiqueta y color). */
function eventMeta(type: string): {
  icon: string;
  label: string;
  variant: "default" | "muted" | "success" | "destructive";
  color: string;
} {
  switch (type) {
    case "person":
      return {
        icon: "🚶",
        label: "Persona",
        variant: "destructive",
        color: "var(--color-destructive)",
      };
    case "motion":
      return {
        icon: "🏃",
        label: "Movimiento",
        variant: "default",
        color: "var(--color-primary)",
      };
    case "online":
      return {
        icon: "🟢",
        label: "Conectada",
        variant: "success",
        color: "var(--color-success)",
      };
    case "offline":
      return {
        icon: "🔴",
        label: "Desconectada",
        variant: "muted",
        color: "var(--color-muted-foreground)",
      };
    default:
      return {
        icon: "📡",
        label: type,
        variant: "muted",
        color: "var(--color-muted-foreground)",
      };
  }
}

/** Etiqueta legible para el encabezado del grupo de un día. */
function dayLabel(date: Date): string {
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  const sameDay = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();
  if (sameDay(date, today)) return "Hoy";
  if (sameDay(date, yesterday)) return "Ayer";
  return date.toLocaleDateString("es-ES", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

/** Miniatura del evento con fallback a icono si la imagen no carga. */
function EventThumb({ url, icon }: { url: string | null; icon: string }) {
  const [failed, setFailed] = useState(false);
  if (url && !failed) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={url}
        alt="Miniatura del evento"
        onError={() => setFailed(true)}
        className="h-16 w-16 shrink-0 rounded-[var(--radius)] object-cover"
      />
    );
  }
  return (
    <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-[var(--radius)] bg-gradient-to-br from-[var(--color-muted)] to-[var(--color-border)] text-2xl">
      {icon}
    </div>
  );
}

export default function EventsPage() {
  const [events, setEvents] = useState<CameraEvent[]>([]);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [cameraId, setCameraId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [clip, setClip] = useState<{ url: string; title: string } | null>(null);

  const cameraName = useMemo(() => {
    const map = new Map(cameras.map((c) => [c.id, c.name]));
    return (id: string) => map.get(id) ?? "Cámara desconocida";
  }, [cameras]);

  // Agrupa los eventos por día conservando el orden (más recientes primero).
  const groups = useMemo(() => {
    const byDay = new Map<string, CameraEvent[]>();
    for (const ev of events) {
      const d = new Date(ev.timestamp);
      const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
      const list = byDay.get(key) ?? [];
      list.push(ev);
      byDay.set(key, list);
    }
    return Array.from(byDay.entries()).map(([, list]) => ({
      label: dayLabel(new Date(list[0].timestamp)),
      events: list,
    }));
  }, [events]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const ev = await api.events.list(cameraId || undefined, 100);
      setEvents(ev);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [cameraId]);

  // Carga inicial de cámaras (para el filtro y los nombres).
  useEffect(() => {
    api.cameras
      .list()
      .then(setCameras)
      .catch(() => {});
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="mx-auto max-w-4xl">
      <header className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-brand-gradient">Eventos</h2>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Línea de tiempo de la actividad detectada por tus cámaras.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <EnableNotifications />
          <Select
            value={cameraId}
            onChange={(e) => setCameraId(e.target.value)}
            className="w-56"
          >
            <option value="">Todas las cámaras</option>
            {cameras.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
          <Button variant="outline" onClick={load} title="Actualizar">
            ↻
          </Button>
        </div>
      </header>

      {error && (
        <p className="mb-4 text-sm text-[var(--color-destructive)]">{error}</p>
      )}
      {loading && (
        <p className="text-sm text-[var(--color-muted-foreground)]">Cargando…</p>
      )}

      {!loading && events.length === 0 && (
        <Card className="animate-in">
          <CardContent className="flex flex-col items-center gap-2 p-10 text-center text-[var(--color-muted-foreground)]">
            <span className="text-4xl">🔕</span>
            <p className="text-sm">
              No hay eventos para el filtro seleccionado.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-col gap-6">
        {groups.map((group, gi) => (
          <section
            key={group.label}
            className="animate-in"
            style={{ animationDelay: `${gi * 60}ms` }}
          >
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-[var(--color-muted-foreground)]">
              <span className="bg-brand-gradient h-2 w-2 rounded-full" />
              {group.label}
              <span className="text-xs font-normal normal-case">
                · {group.events.length} evento
                {group.events.length !== 1 ? "s" : ""}
              </span>
            </h3>

            {/* Línea de tiempo con borde vertical. */}
            <div className="flex flex-col gap-2 border-l-2 border-[var(--color-border)] pl-4">
              {group.events.map((ev) => {
                const meta = eventMeta(ev.event_type);
                return (
                  <div
                    key={ev.id}
                    className="card-hover relative flex items-center gap-3 rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-card)] p-3 shadow-sm"
                  >
                    {/* Punto sobre la línea de tiempo. */}
                    <span
                      className="absolute -left-[22px] top-1/2 h-3 w-3 -translate-y-1/2 rounded-full ring-4 ring-[var(--color-background)]"
                      style={{ backgroundColor: meta.color }}
                    />

                    {ev.thumbnail_url ? (
                      <EventThumb url={ev.thumbnail_url} icon={meta.icon} />
                    ) : (
                      <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-[var(--radius)] bg-gradient-to-br from-[var(--color-muted)] to-[var(--color-border)] text-2xl">
                        {meta.icon}
                      </div>
                    )}

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant={meta.variant}>
                          {meta.icon} {meta.label}
                        </Badge>
                        <span className="truncate text-sm font-medium">
                          {cameraName(ev.camera_id)}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-[var(--color-muted-foreground)]">
                        {new Date(ev.timestamp).toLocaleTimeString("es-ES", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>

                    {ev.video_clip_url && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          setClip({
                            url: ev.video_clip_url!,
                            title: `${meta.label} · ${cameraName(ev.camera_id)}`,
                          })
                        }
                      >
                        ▶ Clip
                      </Button>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        ))}
      </div>

      {/* Reproductor de clip en modal. */}
      {clip && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
          onClick={() => setClip(null)}
        >
          <div
            className="w-full max-w-2xl overflow-hidden rounded-2xl bg-[var(--color-card)] shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between gap-4 px-4 py-3">
              <p className="truncate text-sm font-semibold">{clip.title}</p>
              <button
                onClick={() => setClip(null)}
                className="rounded-full px-2 text-lg text-[var(--color-muted-foreground)] hover:bg-[var(--color-muted)]"
                aria-label="Cerrar"
              >
                ✕
              </button>
            </div>
            {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
            <video
              src={clip.url}
              controls
              autoPlay
              className="aspect-video w-full bg-black"
            />
          </div>
        </div>
      )}
    </div>
  );
}
