// ============================================================================
// Ho smartvision — Edge Function: notify-event
// ----------------------------------------------------------------------------
// Recibe un evento recién insertado (vía trigger pg_net o Database Webhook),
// calcula los destinatarios (staff + usuarios del cliente dueño de la cámara),
// y les envía una notificación Web Push (VAPID, sin Firebase).
//
// Despliegue:
//   supabase functions deploy notify-event --no-verify-jwt
//
// Secrets requeridos (supabase secrets set ...):
//   VAPID_PUBLIC_KEY   Clave pública VAPID
//   VAPID_PRIVATE_KEY  Clave privada VAPID
//   VAPID_SUBJECT      p. ej. mailto:admin@tudominio.com
//   WEBHOOK_SECRET     Debe coincidir con app.settings.webhook_secret
//   (SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY los inyecta Supabase.)
// ============================================================================

import { createClient } from "jsr:@supabase/supabase-js@2";
import webpush from "npm:web-push@3.6.7";

interface EventRow {
  id: string;
  camera_id: string;
  event_type: string;
  timestamp: string;
  thumbnail_url: string | null;
  video_clip_url: string | null;
  metadata: Record<string, unknown>;
}

const EVENT_LABELS: Record<string, string> = {
  person: "🚶 Persona detectada",
  motion: "🏃 Movimiento detectado",
  online: "🟢 Cámara conectada",
  offline: "🔴 Cámara desconectada",
};

const supabase = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);

webpush.setVapidDetails(
  Deno.env.get("VAPID_SUBJECT") ?? "mailto:admin@example.com",
  Deno.env.get("VAPID_PUBLIC_KEY")!,
  Deno.env.get("VAPID_PRIVATE_KEY")!,
);

// ---------------------------------------------------------------------------
// FCM (Firebase Cloud Messaging) HTTP v1 — push nativo para la app móvil.
// Requiere el secret FCM_SERVICE_ACCOUNT (JSON de la cuenta de servicio de
// Firebase). Si no está definido, se omite el envío FCM sin error.
// ---------------------------------------------------------------------------
interface ServiceAccount {
  client_email: string;
  private_key: string;
  project_id: string;
}

function getServiceAccount(): ServiceAccount | null {
  const raw = Deno.env.get("FCM_SERVICE_ACCOUNT");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as ServiceAccount;
  } catch {
    return null;
  }
}

function base64url(data: Uint8Array | string): string {
  const bytes =
    typeof data === "string" ? new TextEncoder().encode(data) : data;
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/** Importa la clave privada PEM (PKCS#8) de la cuenta de servicio. */
async function importPrivateKey(pem: string): Promise<CryptoKey> {
  const body = pem
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\s+/g, "");
  const der = Uint8Array.from(atob(body), (c) => c.charCodeAt(0));
  return crypto.subtle.importKey(
    "pkcs8",
    der,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"],
  );
}

/** Obtiene un access token OAuth2 para la API de FCM v1. */
async function getFcmAccessToken(sa: ServiceAccount): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  const header = base64url(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const claim = base64url(
    JSON.stringify({
      iss: sa.client_email,
      scope: "https://www.googleapis.com/auth/firebase.messaging",
      aud: "https://oauth2.googleapis.com/token",
      iat: now,
      exp: now + 3600,
    }),
  );
  const key = await importPrivateKey(sa.private_key);
  const signature = new Uint8Array(
    await crypto.subtle.sign(
      "RSASSA-PKCS1-v1_5",
      key,
      new TextEncoder().encode(`${header}.${claim}`),
    ),
  );
  const jwt = `${header}.${claim}.${base64url(signature)}`;

  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: jwt,
    }),
  });
  const json = await res.json();
  return json.access_token as string;
}


Deno.serve(async (req) => {
  // Verificación del secreto compartido.
  const secret = req.headers.get("x-webhook-secret");
  if (secret !== Deno.env.get("WEBHOOK_SECRET")) {
    return new Response("Unauthorized", { status: 401 });
  }

  let event: EventRow | undefined;
  try {
    const payload = await req.json();
    // Acepta tanto { event: {...} } (trigger pg_net) como { record: {...} }
    // (Database Webhook del dashboard).
    event = payload.event ?? payload.record;
  } catch {
    return new Response("Bad Request", { status: 400 });
  }
  if (!event?.camera_id) {
    return new Response("No event", { status: 400 });
  }

  // 1) Cámara -> propiedad -> cliente.
  const { data: camera } = await supabase
    .from("cameras")
    .select("id, name, property_id, properties(client_id)")
    .eq("id", event.camera_id)
    .single();

  if (!camera) return new Response("Camera not found", { status: 404 });

  const clientId = (camera.properties as { client_id: string } | null)
    ?.client_id;

  // 2) Destinatarios: usuarios de la app del cliente + todo el staff activo.
  const recipients = new Set<string>();

  if (clientId) {
    const { data: appUsers } = await supabase
      .from("app_users")
      .select("id")
      .eq("client_id", clientId);
    appUsers?.forEach((u) => recipients.add(u.id));
  }

  const { data: staff } = await supabase
    .from("staff")
    .select("id")
    .eq("is_active", true);
  staff?.forEach((s) => recipients.add(s.id));

  if (recipients.size === 0) {
    return new Response(JSON.stringify({ sent: 0 }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  // 3) Suscripciones de esos usuarios: Web Push (navegador) y FCM (móvil).
  const { data: subs } = await supabase
    .from("push_subscriptions")
    .select("id, endpoint, p256dh, auth")
    .in("user_id", [...recipients]);

  const { data: tokens } = await supabase
    .from("device_tokens")
    .select("id, fcm_token")
    .in("user_id", [...recipients]);

  // 4) Construir el contenido de la notificación (compartido).
  const title = EVENT_LABELS[event.event_type] ?? "📡 Evento de cámara";
  const body = `${camera.name} · ${new Date(event.timestamp).toLocaleString("es-ES")}`;
  const url = "/dashboard/events";
  const tag = `event-${event.id}`;

  // 4a) Web Push (VAPID).
  const notification = JSON.stringify({
    title,
    body,
    url,
    tag,
    icon: event.thumbnail_url ?? undefined,
  });

  const staleSubIds: string[] = [];
  const webResults = await Promise.allSettled(
    (subs ?? []).map((s) =>
      webpush
        .sendNotification(
          { endpoint: s.endpoint, keys: { p256dh: s.p256dh, auth: s.auth } },
          notification,
        )
        .catch((err: { statusCode?: number }) => {
          if (err?.statusCode === 404 || err?.statusCode === 410) {
            staleSubIds.push(s.id);
          }
          throw err;
        }),
    ),
  );
  if (staleSubIds.length > 0) {
    await supabase.from("push_subscriptions").delete().in("id", staleSubIds);
  }

  // 4b) FCM (Firebase) para la app móvil.
  let fcmSent = 0;
  const sa = getServiceAccount();
  if (sa && tokens && tokens.length > 0) {
    const accessToken = await getFcmAccessToken(sa);
    const endpoint = `https://fcm.googleapis.com/v1/projects/${sa.project_id}/messages:send`;
    const staleTokenIds: string[] = [];

    await Promise.allSettled(
      tokens.map(async (t) => {
        const res = await fetch(endpoint, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: {
              token: t.fcm_token,
              notification: { title, body },
              data: { url, tag, event_type: event.event_type },
              android: { priority: "HIGH" },
            },
          }),
        });
        if (res.ok) {
          fcmSent++;
        } else if (res.status === 404 || res.status === 400) {
          // Token inválido o no registrado: borrar.
          staleTokenIds.push(t.id);
        }
      }),
    );

    if (staleTokenIds.length > 0) {
      await supabase.from("device_tokens").delete().in("id", staleTokenIds);
    }
  }

  const webSent = webResults.filter((r) => r.status === "fulfilled").length;
  return new Response(
    JSON.stringify({
      web_sent: webSent,
      web_total: subs?.length ?? 0,
      fcm_sent: fcmSent,
      fcm_total: tokens?.length ?? 0,
    }),
    { headers: { "Content-Type": "application/json" } },
  );
});
