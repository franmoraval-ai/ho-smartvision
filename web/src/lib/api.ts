import { createClient } from "@/lib/supabase/client";

/**
 * Cliente tipado para el backend FastAPI. Adjunta automáticamente el JWT de
 * Supabase de la sesión actual como `Authorization: Bearer <token>`.
 */
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function authHeaders(): Promise<HeadersInit> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const token = session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(await authHeaders()),
    ...(init.headers ?? {}),
  };

  const res = await fetch(`${API_URL}${path}`, { ...init, headers });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new Error(detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// --- Tipos compartidos con el backend ---
export interface Client {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  created_at: string;
}

export interface Property {
  id: string;
  client_id: string;
  name: string;
  address: string | null;
  created_at: string;
}

export interface Camera {
  id: string;
  property_id: string;
  gateway_id: string | null;
  name: string;
  rtsp_url: string | null;
  onvif_ip: string | null;
  onvif_username: string | null;
  is_active: boolean;
  created_at: string;
}

export interface OnvifDevice {
  ip: string;
  port: number;
  name: string | null;
  manufacturer: string | null;
  model: string | null;
  xaddrs: string[];
  rtsp_hint: string | null;
}

export interface OnvifDiscoveryResponse {
  simulated: boolean;
  devices: OnvifDevice[];
}

export interface CameraEvent {
  id: string;
  camera_id: string;
  event_type: string;
  timestamp: string;
  thumbnail_url: string | null;
  video_clip_url: string | null;
  metadata: Record<string, unknown>;
}

// --- API tipada ---
export const api = {
  clients: {
    list: () => request<Client[]>("/clients"),
    create: (body: Partial<Client>) =>
      request<Client>("/clients", { method: "POST", body: JSON.stringify(body) }),
  },
  properties: {
    list: (clientId?: string) =>
      request<Property[]>(
        `/properties${clientId ? `?client_id=${clientId}` : ""}`,
      ),
    create: (body: { client_id: string; name: string; address?: string }) =>
      request<Property>("/properties", {
        method: "POST",
        body: JSON.stringify(body),
      }),
  },
  cameras: {
    list: (propertyId?: string) =>
      request<Camera[]>(
        `/cameras${propertyId ? `?property_id=${propertyId}` : ""}`,
      ),
    create: (body: {
      property_id: string;
      name: string;
      rtsp_url?: string;
      onvif_ip?: string;
      onvif_username?: string;
      onvif_password?: string;
      gateway_id?: string;
    }) =>
      request<Camera>("/cameras", {
        method: "POST",
        body: JSON.stringify(body),
      }),
  },
  onvif: {
    discover: (simulate = false) =>
      request<OnvifDiscoveryResponse>(
        `/discover-onvif${simulate ? "?simulate=true" : ""}`,
      ),
  },
  events: {
    list: (cameraId?: string, limit = 50) => {
      const params = new URLSearchParams();
      if (cameraId) params.set("camera_id", cameraId);
      params.set("limit", String(limit));
      return request<CameraEvent[]>(`/events?${params.toString()}`);
    },
  },
};
