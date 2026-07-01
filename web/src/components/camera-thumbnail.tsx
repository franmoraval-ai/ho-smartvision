"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Miniatura tipo Ring: muestra un snapshot JPEG de la cámara servido por go2rtc
 * (`/api/frame.jpeg?src=<id>`) y lo refresca cada `refreshMs`.
 *
 * Si no hay `NEXT_PUBLIC_STREAM_BASE_URL` o la imagen falla, muestra un
 * marcador de posición con degradado.
 */
const STREAM_BASE_URL = (
  process.env.NEXT_PUBLIC_STREAM_BASE_URL ?? ""
).replace(/\/+$/, "");

export function CameraThumbnail({
  cameraId,
  active,
  refreshMs = 10_000,
  className = "",
}: {
  cameraId: string;
  active?: boolean;
  refreshMs?: number;
  className?: string;
}) {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    if (!STREAM_BASE_URL || !active) {
      setSrc(null);
      return;
    }

    const base = `${STREAM_BASE_URL}/api/frame.jpeg?src=${encodeURIComponent(
      cameraId,
    )}`;
    const tick = () => {
      if (!mounted.current) return;
      // Reintentamos en cada ciclo: el productor de go2rtc puede tardar
      // unos segundos en arrancar (cold start) y abortar la primera carga.
      setFailed(false);
      // cache-buster para forzar un fotograma nuevo.
      setSrc(`${base}&t=${Date.now()}`);
    };
    tick();
    const id = setInterval(tick, refreshMs);
    return () => {
      mounted.current = false;
      clearInterval(id);
    };
  }, [cameraId, active, refreshMs]);

  const showImage = src && !failed;

  return (
    <div
      className={`relative aspect-video w-full overflow-hidden rounded-[var(--radius)] bg-[var(--color-muted)] ${className}`}
    >
      {showImage ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt="Vista de la cámara"
          className="h-full w-full object-cover transition-opacity duration-300"
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="flex h-full w-full flex-col items-center justify-center gap-2 bg-gradient-to-br from-[var(--color-muted)] to-[var(--color-border)] text-[var(--color-muted-foreground)]">
          <span className="text-3xl">{active ? "📷" : "🚫"}</span>
          <span className="text-xs font-medium">
            {active ? "Sin vista previa" : "Cámara inactiva"}
          </span>
        </div>
      )}

      {/* Badge EN VIVO */}
      {active && (
        <span className="absolute left-2 top-2 inline-flex items-center gap-1.5 rounded-full bg-black/55 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-white backdrop-blur">
          <span className="live-dot" />
          En vivo
        </span>
      )}
    </div>
  );
}
