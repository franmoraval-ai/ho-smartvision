"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api, type Camera } from "@/lib/api";

/**
 * Visor en vivo de una cámara mediante go2rtc (WebRTC/HLS) embebido en iframe.
 *
 * Requiere `NEXT_PUBLIC_STREAM_BASE_URL` apuntando al go2rtc del gateway
 * (idealmente tras un reverse proxy con HTTPS). El stream debe llamarse igual
 * que el `id` de la cámara.
 */
const STREAM_BASE_URL = process.env.NEXT_PUBLIC_STREAM_BASE_URL ?? "";

export default function CameraLivePage() {
  const params = useParams<{ id: string }>();
  const cameraId = params.id;
  const [camera, setCamera] = useState<Camera | null>(null);

  useEffect(() => {
    api.cameras
      .list()
      .then((cams) => setCamera(cams.find((c) => c.id === cameraId) ?? null))
      .catch(() => {});
  }, [cameraId]);

  const streamUrl = STREAM_BASE_URL
    ? `${STREAM_BASE_URL.replace(/\/+$/, "")}/stream.html?src=${encodeURIComponent(cameraId)}`
    : null;

  return (
    <div className="mx-auto max-w-4xl">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">
            {camera?.name ?? "Cámara"} — En vivo
          </h2>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Transmisión WebRTC/HLS vía go2rtc.
          </p>
        </div>
        <Link href="/dashboard/cameras">
          <Button variant="outline">← Volver</Button>
        </Link>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Reproductor</CardTitle>
        </CardHeader>
        <CardContent>
          {streamUrl ? (
            <div className="aspect-video w-full overflow-hidden rounded-[var(--radius)] bg-black">
              <iframe
                src={streamUrl}
                title={`Live ${camera?.name ?? cameraId}`}
                className="h-full w-full border-0"
                allow="autoplay; fullscreen; picture-in-picture"
                allowFullScreen
              />
            </div>
          ) : (
            <div className="flex aspect-video w-full flex-col items-center justify-center gap-2 rounded-[var(--radius)] bg-[var(--color-muted)] text-center">
              <span className="text-3xl">📺</span>
              <p className="font-medium">Streaming no configurado</p>
              <p className="text-sm text-[var(--color-muted-foreground)]">
                Define <code>NEXT_PUBLIC_STREAM_BASE_URL</code> con la URL pública
                de go2rtc.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
