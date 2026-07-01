"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  api,
  type OnvifDevice,
  type Property,
} from "@/lib/api";

export default function AddCameraPage() {
  const router = useRouter();
  const [properties, setProperties] = useState<Property[]>([]);

  // Estado del formulario de cámara.
  const [propertyId, setPropertyId] = useState("");
  const [name, setName] = useState("");
  const [rtspUrl, setRtspUrl] = useState("");
  const [onvifIp, setOnvifIp] = useState("");
  const [onvifUser, setOnvifUser] = useState("");
  const [onvifPassword, setOnvifPassword] = useState("");

  // Descubrimiento ONVIF.
  const [discovering, setDiscovering] = useState(false);
  const [devices, setDevices] = useState<OnvifDevice[]>([]);
  const [simulated, setSimulated] = useState(false);

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const p = await api.properties.list();
        if (!active) return;
        setProperties(p);
        if (p.length > 0) setPropertyId(p[0].id);
      } catch (e) {
        if (active) setError((e as Error).message);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function discover() {
    setDiscovering(true);
    setError(null);
    setDevices([]);
    try {
      const res = await api.onvif.discover();
      setDevices(res.devices);
      setSimulated(res.simulated);
      if (res.devices.length === 0) {
        setError("No se encontraron cámaras ONVIF en la red local.");
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDiscovering(false);
    }
  }

  /** Rellena el formulario con los datos de un dispositivo descubierto. */
  function useDevice(device: OnvifDevice) {
    setName(
      device.name ??
        ([device.manufacturer, device.model].filter(Boolean).join(" ") ||
          `Cámara ${device.ip}`),
    );
    setOnvifIp(device.ip);
    if (device.rtsp_hint) setRtspUrl(device.rtsp_hint);
    setSuccess(`Datos de ${device.ip} cargados. Completa credenciales y guarda.`);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await api.cameras.create({
        property_id: propertyId,
        name,
        rtsp_url: rtspUrl || undefined,
        onvif_ip: onvifIp || undefined,
        onvif_username: onvifUser || undefined,
        onvif_password: onvifPassword || undefined,
      });
      router.push("/dashboard/cameras");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  const noProperties = properties.length === 0;

  return (
    <div className="mx-auto max-w-3xl">
      <header className="mb-6">
        <h2 className="text-2xl font-bold">Agregar cámara</h2>
        <p className="text-sm text-[var(--color-muted-foreground)]">
          Descubre cámaras ONVIF en la red o configúralas manualmente.
        </p>
      </header>

      {/* Botón grande de descubrimiento ONVIF */}
      <Card className="mb-6">
        <CardContent className="flex flex-col items-center gap-4 p-8 text-center">
          <Button
            type="button"
            size="lg"
            onClick={discover}
            disabled={discovering}
            className="w-full max-w-md"
          >
            {discovering
              ? "Buscando cámaras…"
              : "📡 Descubrir cámaras ONVIF en red local"}
          </Button>
          <p className="text-xs text-[var(--color-muted-foreground)]">
            El descubrimiento real requiere que el backend o el Gateway estén en
            la misma red que las cámaras.
          </p>

          {devices.length > 0 && (
            <div className="w-full">
              <div className="mb-2 flex items-center justify-center gap-2">
                <p className="text-sm font-medium">
                  {devices.length} dispositivo(s) encontrado(s)
                </p>
                {simulated && <Badge variant="muted">simulado</Badge>}
              </div>
              <ul className="flex flex-col gap-2 text-left">
                {devices.map((d) => (
                  <li
                    key={d.ip}
                    className="flex items-center justify-between gap-3 rounded-[var(--radius)] border border-[var(--color-border)] p-3"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">
                        {d.name ??
                          [d.manufacturer, d.model]
                            .filter(Boolean)
                            .join(" ") ??
                          d.ip}
                      </p>
                      <p className="text-xs text-[var(--color-muted-foreground)]">
                        {d.ip}:{d.port}
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => useDevice(d)}
                    >
                      Usar
                    </Button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Formulario de configuración */}
      <Card>
        <CardHeader>
          <CardTitle>Datos de la cámara</CardTitle>
          <CardDescription>
            Asigna la cámara a una propiedad y define su acceso.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {noProperties ? (
            <p className="text-sm text-[var(--color-destructive)]">
              No tienes propiedades. Crea un cliente y una propiedad antes de
              añadir cámaras.
            </p>
          ) : (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="property">Propiedad</Label>
                <Select
                  id="property"
                  required
                  value={propertyId}
                  onChange={(e) => setPropertyId(e.target.value)}
                >
                  {properties.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </Select>
              </div>

              <div className="flex flex-col gap-2">
                <Label htmlFor="name">Nombre de la cámara</Label>
                <Input
                  id="name"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Entrada principal"
                />
              </div>

              <div className="flex flex-col gap-2">
                <Label htmlFor="rtsp">URL RTSP</Label>
                <Input
                  id="rtsp"
                  value={rtspUrl}
                  onChange={(e) => setRtspUrl(e.target.value)}
                  placeholder="rtsp://192.168.1.50:554/Streaming/Channels/101"
                />
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div className="flex flex-col gap-2">
                  <Label htmlFor="onvif_ip">IP ONVIF</Label>
                  <Input
                    id="onvif_ip"
                    value={onvifIp}
                    onChange={(e) => setOnvifIp(e.target.value)}
                    placeholder="192.168.1.50"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <Label htmlFor="onvif_user">Usuario ONVIF</Label>
                  <Input
                    id="onvif_user"
                    value={onvifUser}
                    onChange={(e) => setOnvifUser(e.target.value)}
                    placeholder="admin"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <Label htmlFor="onvif_pass">Contraseña ONVIF</Label>
                  <Input
                    id="onvif_pass"
                    type="password"
                    value={onvifPassword}
                    onChange={(e) => setOnvifPassword(e.target.value)}
                    placeholder="••••••••"
                  />
                </div>
              </div>

              <p className="text-xs text-[var(--color-muted-foreground)]">
                La contraseña ONVIF se cifra en el backend antes de guardarse.
              </p>

              {error && (
                <p className="text-sm text-[var(--color-destructive)]">{error}</p>
              )}
              {success && (
                <p className="text-sm text-emerald-600">{success}</p>
              )}

              <div className="flex gap-2">
                <Button type="submit" disabled={saving}>
                  {saving ? "Guardando…" : "Guardar cámara"}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => router.push("/dashboard/cameras")}
                >
                  Cancelar
                </Button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
