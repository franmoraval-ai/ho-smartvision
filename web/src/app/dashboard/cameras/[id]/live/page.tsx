"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api, type Camera, type CameraStream } from "@/lib/api";

/**
 * Visor en vivo de una cámara.
 *
 * - Cámaras `local`: iframe a go2rtc (`NEXT_PUBLIC_STREAM_BASE_URL`).
 * - Cámaras de cloud de fabricante (ezviz/imou/reolink/tapo): el backend
 *   resuelve una URL fresca en `/cameras/{id}/stream` y se reproduce HLS/FLV.
 */
const STREAM_BASE_URL = process.env.NEXT_PUBLIC_STREAM_BASE_URL ?? "";

const HLS_CDN = "https://cdn.jsdelivr.net/npm/hls.js@1.5.17/dist/hls.min.js";
const FLV_CDN = "https://cdn.jsdelivr.net/npm/mpegts.js@1.7.3/dist/mpegts.js";

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) return resolve();
    const s = document.createElement("script");
    s.src = src;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`No se pudo cargar ${src}`));
    document.head.appendChild(s);
  });
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyWindow = typeof window & { Hls?: any; mpegts?: any };

export default function CameraLivePage() {
  const params = useParams<{ id: string }>();
  const cameraId = params.id;
  const [camera, setCamera] = useState<Camera | null>(null);
  const [stream, setStream] = useState<CameraStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.cameras
      .list()
      .then((cams) => {
        if (cancelled) return null;
        const cam = cams.find((c) => c.id === cameraId) ?? null;
        setCamera(cam);
        return cam;
      })
      .then((cam) => {
        if (!cam || cam.provider === "local") {
          if (!cancelled) setLoading(false);
          return;
        }
        return api.cameras
          .stream(cameraId)
          .then((s) => {
            if (!cancelled) setStream(s);
          })
          .catch((e: Error) => {
            if (!cancelled) setError(e.message);
          })
          .finally(() => {
            if (!cancelled) setLoading(false);
          });
      })
      .catch((e: Error) => {
        if (!cancelled) {
          setError(e.message);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [cameraId]);

  // Reproduce el stream cloud (HLS/FLV) en el elemento <video>.
  useEffect(() => {
    const video = videoRef.current;
    if (!stream || !stream.browser_playable || !video) return;
    const w = window as AnyWindow;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let player: any = null;

    (async () => {
      try {
        if (stream.protocol === "hls") {
          if (video.canPlayType("application/vnd.apple.mpegurl")) {
            video.src = stream.url;
          } else {
            await loadScript(HLS_CDN);
            if (w.Hls?.isSupported()) {
              player = new w.Hls();
              player.loadSource(stream.url);
              player.attachMedia(video);
            } else {
              video.src = stream.url;
            }
          }
        } else if (stream.protocol === "flv") {
          await loadScript(FLV_CDN);
          if (w.mpegts?.isSupported()) {
            player = w.mpegts.createPlayer({ type: "flv", url: stream.url });
            player.attachMediaElement(video);
            player.load();
          }
        }
        video.play().catch(() => {});
      } catch (e) {
        setError((e as Error).message);
      }
    })();

    return () => {
      if (player?.destroy) player.destroy();
    };
  }, [stream]);

  const localStreamUrl =
    camera?.provider === "local" && STREAM_BASE_URL
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
            {camera && camera.provider !== "local"
              ? `Fuente: cloud ${camera.provider}`
              : "Transmisión WebRTC/HLS vía go2rtc."}
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
          {/* Cámara local -> go2rtc */}
          {camera?.provider === "local" && localStreamUrl && (
            <div className="aspect-video w-full overflow-hidden rounded-[var(--radius)] bg-black">
              <iframe
                src={localStreamUrl}
                title={`Live ${camera?.name ?? cameraId}`}
                className="h-full w-full border-0"
                allow="autoplay; fullscreen; picture-in-picture"
                allowFullScreen
              />
            </div>
          )}

          {/* Cámara cloud reproducible -> <video> */}
          {stream?.browser_playable && (
            <div className="aspect-video w-full overflow-hidden rounded-[var(--radius)] bg-black">
              <video
                ref={videoRef}
                className="h-full w-full"
                controls
                autoPlay
                muted
                playsInline
              />
            </div>
          )}

          {/* Cloud NO reproducible en navegador (RTSP/RTMP o FLV sobre HTTP) */}
          {stream && !stream.browser_playable && (
            <div className="flex aspect-video w-full flex-col items-center justify-center gap-2 rounded-[var(--radius)] bg-[var(--color-muted)] text-center">
              <span className="text-3xl">🔒</span>
              <p className="font-medium">
                Stream {stream.protocol.toUpperCase()} no reproducible en el
                navegador
              </p>
              <p className="max-w-md text-sm text-[var(--color-muted-foreground)]">
                Las cámaras {stream.provider} entregan {stream.protocol} y
                requieren un gateway (go2rtc) que lo transcodifique a HLS/WebRTC
                sobre HTTPS.
              </p>
            </div>
          )}

          {/* Estados de carga / error / sin configurar */}
          {loading && !stream && (
            <div className="flex aspect-video w-full items-center justify-center rounded-[var(--radius)] bg-[var(--color-muted)]">
              <p className="text-sm text-[var(--color-muted-foreground)]">
                Cargando transmisión…
              </p>
            </div>
          )}

          {!loading && error && (
            <div className="flex aspect-video w-full flex-col items-center justify-center gap-2 rounded-[var(--radius)] bg-[var(--color-muted)] text-center">
              <span className="text-3xl">⚠️</span>
              <p className="font-medium">No se pudo obtener el vídeo</p>
              <p className="max-w-md text-sm text-[var(--color-muted-foreground)]">
                {error}
              </p>
            </div>
          )}

          {!loading &&
            !error &&
            camera?.provider === "local" &&
            !localStreamUrl && (
              <div className="flex aspect-video w-full flex-col items-center justify-center gap-2 rounded-[var(--radius)] bg-[var(--color-muted)] text-center">
                <span className="text-3xl">📺</span>
                <p className="font-medium">Streaming no configurado</p>
                <p className="text-sm text-[var(--color-muted-foreground)]">
                  Define <code>NEXT_PUBLIC_STREAM_BASE_URL</code> o asigna un
                  proveedor cloud a la cámara.
                </p>
              </div>
            )}
        </CardContent>
      </Card>
    </div>
  );
}
