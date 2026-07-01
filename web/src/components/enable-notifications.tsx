"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  getPushState,
  pushSupported,
  subscribeToPush,
  unsubscribeFromPush,
  type PushState,
} from "@/lib/push";

/** Botón para activar/desactivar las notificaciones push del panel. */
export function EnableNotifications() {
  const [mounted, setMounted] = useState(false);
  const [state, setState] = useState<PushState>("loading");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
    getPushState().then(setState);
  }, []);

  // Evita el mismatch de hidratación: en el servidor no hay `navigator`.
  if (!mounted) return null;
  if (state === "unsupported" || !pushSupported()) return null;

  const toggle = async () => {
    setBusy(true);
    setError(null);
    try {
      if (state === "subscribed") {
        setState(await unsubscribeFromPush());
      } else {
        setState(await subscribeToPush());
      }
    } catch (e) {
      // Mensajes amigables para los fallos más comunes.
      const raw = (e as Error).message ?? "";
      if (/incognito|permission denied|Registration failed/i.test(raw)) {
        setError("No disponible en modo incógnito.");
      } else if (/VAPID/i.test(raw)) {
        setError("Falta configurar la clave VAPID.");
      } else {
        setError("No se pudieron activar los avisos.");
      }
    } finally {
      setBusy(false);
    }
  };

  if (state === "denied") {
    return (
      <span
        title="Habilita las notificaciones en los ajustes del navegador"
        className="text-xs text-[var(--color-muted-foreground)]"
      >
        🔕 Notificaciones bloqueadas
      </span>
    );
  }

  const subscribed = state === "subscribed";
  return (
    <div className="flex flex-col items-end gap-1">
      <Button
        variant={subscribed ? "outline" : "default"}
        size="sm"
        onClick={toggle}
        disabled={busy || state === "loading"}
        title={
          subscribed
            ? "Desactivar notificaciones"
            : "Recibir avisos de eventos en este dispositivo"
        }
      >
        {busy ? "…" : subscribed ? "🔔 Activadas" : "🔔 Activar avisos"}
      </Button>
      {error && (
        <span className="text-[11px] text-[var(--color-muted-foreground)]">
          {error}
        </span>
      )}
    </div>
  );
}
