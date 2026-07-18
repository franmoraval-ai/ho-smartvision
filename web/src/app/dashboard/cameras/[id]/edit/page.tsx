"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
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
import { api, type Camera, type CameraProviderName } from "@/lib/api";

export default function EditCameraPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const cameraId = params.id;

  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [rtspUrl, setRtspUrl] = useState("");
  const [onvifIp, setOnvifIp] = useState("");
  const [onvifUser, setOnvifUser] = useState("");
  const [onvifPassword, setOnvifPassword] = useState("");

  const [provider, setProvider] = useState<CameraProviderName>("local");
  const [providerSerial, setProviderSerial] = useState("");
  const [providerChannel, setProviderChannel] = useState("1");
  const [providerVerifyCode, setProviderVerifyCode] = useState("");

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const cam: Camera = await api.cameras.get(cameraId);
        if (!active) return;
        setName(cam.name);
        setIsActive(cam.is_active);
        setRtspUrl(cam.rtsp_url ?? "");
        setOnvifIp(cam.onvif_ip ?? "");
        setOnvifUser(cam.onvif_username ?? "");
        setProvider(cam.provider);
        setProviderSerial(cam.provider_device_serial ?? "");
        setProviderChannel(String(cam.provider_channel ?? 1));
      } catch (e) {
        if (active) setError((e as Error).message);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [cameraId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.cameras.update(cameraId, {
        name,
        is_active: isActive,
        rtsp_url: rtspUrl || undefined,
        onvif_ip: onvifIp || undefined,
        onvif_username: onvifUser || undefined,
        // Solo envía la contraseña si el usuario escribió una nueva.
        onvif_password: onvifPassword || undefined,
        provider,
        provider_device_serial: providerSerial || undefined,
        provider_channel: Number(providerChannel) || 1,
        // Solo envía el código si el usuario escribió uno nuevo.
        provider_verify_code: providerVerifyCode || undefined,
      });
      router.push("/dashboard/cameras");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <header className="mb-6">
        <h2 className="text-2xl font-bold">Editar cámara</h2>
        <p className="text-sm text-[var(--color-muted-foreground)]">
          Actualiza el acceso y el proveedor de vídeo de la cámara.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Datos de la cámara</CardTitle>
          <CardDescription>
            Deja la contraseña o el código de verificación en blanco para
            conservar los actuales.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-[var(--color-muted-foreground)]">
              Cargando…
            </p>
          ) : (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
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

              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                />
                Cámara activa
              </label>

              <div className="flex flex-col gap-2">
                <Label htmlFor="provider">Proveedor de vídeo</Label>
                <Select
                  id="provider"
                  value={provider}
                  onChange={(e) =>
                    setProvider(e.target.value as CameraProviderName)
                  }
                >
                  <option value="local">Local (gateway / go2rtc)</option>
                  <option value="ezviz">Ezviz / Hikvision (cloud)</option>
                  <option value="imou">Imou / Dahua (cloud)</option>
                  <option value="reolink">Reolink (directo HTTP-FLV)</option>
                  <option value="tapo">Tapo / TP-Link (directo RTSP)</option>
                </Select>
                <p className="text-xs text-[var(--color-muted-foreground)]">
                  Ezviz/Imou usan el cloud del fabricante (sin gateway).
                  Reolink/Tapo requieren IP/usuario/contraseña alcanzables.
                </p>
              </div>

              {(provider === "ezviz" || provider === "imou") && (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <div className="flex flex-col gap-2 sm:col-span-2">
                    <Label htmlFor="serial">Número de serie / deviceId</Label>
                    <Input
                      id="serial"
                      value={providerSerial}
                      onChange={(e) => setProviderSerial(e.target.value)}
                      placeholder="Ej. BA1234567"
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="channel">Canal</Label>
                    <Input
                      id="channel"
                      type="number"
                      min={0}
                      value={providerChannel}
                      onChange={(e) => setProviderChannel(e.target.value)}
                    />
                  </div>
                  {provider === "ezviz" && (
                    <div className="flex flex-col gap-2 sm:col-span-3">
                      <Label htmlFor="verify">
                        Código de verificación (cámaras cifradas)
                      </Label>
                      <Input
                        id="verify"
                        value={providerVerifyCode}
                        onChange={(e) => setProviderVerifyCode(e.target.value)}
                        placeholder="Dejar en blanco para conservar el actual"
                      />
                    </div>
                  )}
                </div>
              )}

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
                    placeholder="Dejar en blanco para conservar la actual"
                  />
                </div>
              </div>

              {error && (
                <p className="text-sm text-[var(--color-destructive)]">
                  {error}
                </p>
              )}

              <div className="flex gap-2">
                <Button type="submit" disabled={saving}>
                  {saving ? "Guardando…" : "Guardar cambios"}
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
