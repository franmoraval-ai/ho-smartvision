import { createClient } from "@/lib/supabase/client";

/**
 * Utilidades de Web Push (VAPID) para el panel — sin Firebase.
 *
 * Flujo:
 *   1) Registrar el Service Worker `/sw.js`.
 *   2) Pedir permiso de notificaciones.
 *   3) Suscribirse con la clave pública VAPID.
 *   4) Guardar la suscripción en la tabla `push_subscriptions` (Supabase).
 */

const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY ?? "";

export type PushState =
  | "unsupported"
  | "denied"
  | "subscribed"
  | "default"
  | "loading";

/** ¿El navegador soporta Web Push? */
export function pushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

/** Convierte la clave VAPID (base64url) al Uint8Array que exige PushManager. */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) output[i] = raw.charCodeAt(i);
  return output;
}

async function getRegistration(): Promise<ServiceWorkerRegistration> {
  const existing = await navigator.serviceWorker.getRegistration("/sw.js");
  if (existing) return existing;
  return navigator.serviceWorker.register("/sw.js");
}

/** Devuelve el estado actual de la suscripción. */
export async function getPushState(): Promise<PushState> {
  if (!pushSupported()) return "unsupported";
  if (Notification.permission === "denied") return "denied";
  try {
    const reg = await navigator.serviceWorker.getRegistration("/sw.js");
    const sub = await reg?.pushManager.getSubscription();
    if (sub) return "subscribed";
  } catch {
    /* noop */
  }
  return Notification.permission === "granted" ? "default" : "default";
}

/** Registra SW, pide permiso, se suscribe y guarda en Supabase. */
export async function subscribeToPush(): Promise<PushState> {
  if (!pushSupported()) return "unsupported";
  if (!VAPID_PUBLIC_KEY) {
    throw new Error("Falta NEXT_PUBLIC_VAPID_PUBLIC_KEY");
  }

  const permission = await Notification.requestPermission();
  if (permission !== "granted") return "denied";

  const reg = await getRegistration();
  await navigator.serviceWorker.ready;

  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
  });

  const json = sub.toJSON();
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) throw new Error("No hay sesión activa");

  const { error } = await supabase.from("push_subscriptions").upsert(
    {
      user_id: user.id,
      endpoint: sub.endpoint,
      p256dh: json.keys?.p256dh ?? "",
      auth: json.keys?.auth ?? "",
      user_agent: navigator.userAgent,
    },
    { onConflict: "endpoint" },
  );
  if (error) throw error;

  return "subscribed";
}

/** Cancela la suscripción local y la borra de Supabase. */
export async function unsubscribeFromPush(): Promise<PushState> {
  if (!pushSupported()) return "unsupported";
  const reg = await navigator.serviceWorker.getRegistration("/sw.js");
  const sub = await reg?.pushManager.getSubscription();
  if (sub) {
    const endpoint = sub.endpoint;
    await sub.unsubscribe();
    const supabase = createClient();
    await supabase.from("push_subscriptions").delete().eq("endpoint", endpoint);
  }
  return "default";
}
