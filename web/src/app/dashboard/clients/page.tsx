"use client";

import { useCallback, useEffect, useState } from "react";
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
import { api, type Client, type Property } from "@/lib/api";

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Formulario de nuevo cliente.
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [c, p] = await Promise.all([
        api.clients.list(),
        api.properties.list(),
      ]);
      setClients(c);
      setProperties(p);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.clients.create({
        full_name: fullName,
        email,
        phone: phone || null,
      });
      setFullName("");
      setEmail("");
      setPhone("");
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-6">
        <h2 className="text-2xl font-bold">Clientes</h2>
        <p className="text-sm text-[var(--color-muted-foreground)]">
          Gestiona clientes y sus propiedades.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Formulario de alta */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Nuevo cliente</CardTitle>
            <CardDescription>Registra un cliente residencial o comercial.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="full_name">Nombre completo</Label>
                <Input
                  id="full_name"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Juan Pérez"
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="juan@ejemplo.com"
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="phone">Teléfono</Label>
                <Input
                  id="phone"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+34 600 000 000"
                />
              </div>
              <Button type="submit" disabled={saving}>
                {saving ? "Guardando…" : "Crear cliente"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Listado */}
        <div className="flex flex-col gap-4 lg:col-span-2">
          {error && (
            <p className="text-sm text-[var(--color-destructive)]">{error}</p>
          )}
          {loading && (
            <p className="text-sm text-[var(--color-muted-foreground)]">
              Cargando…
            </p>
          )}
          {!loading && clients.length === 0 && (
            <Card>
              <CardContent className="p-6 text-sm text-[var(--color-muted-foreground)]">
                Aún no hay clientes. Crea el primero con el formulario.
              </CardContent>
            </Card>
          )}
          {clients.map((client) => (
            <ClientCard
              key={client.id}
              client={client}
              properties={properties.filter((p) => p.client_id === client.id)}
              onChanged={load}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function ClientCard({
  client,
  properties,
  onChanged,
}: {
  client: Client;
  properties: Property[];
  onChanged: () => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function addProperty(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.properties.create({
        client_id: client.id,
        name,
        address: address || undefined,
      });
      setName("");
      setAddress("");
      await onChanged();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{client.full_name}</CardTitle>
        <CardDescription>
          {client.email}
          {client.phone ? ` · ${client.phone}` : ""}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div>
          <p className="mb-1 text-xs font-medium uppercase text-[var(--color-muted-foreground)]">
            Propiedades ({properties.length})
          </p>
          {properties.length === 0 ? (
            <p className="text-sm text-[var(--color-muted-foreground)]">
              Sin propiedades.
            </p>
          ) : (
            <ul className="flex flex-col gap-1">
              {properties.map((p) => (
                <li
                  key={p.id}
                  className="rounded-[var(--radius)] bg-[var(--color-muted)] px-3 py-2 text-sm"
                >
                  <span className="font-medium">{p.name}</span>
                  {p.address && (
                    <span className="text-[var(--color-muted-foreground)]">
                      {" "}
                      — {p.address}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        <form
          onSubmit={addProperty}
          className="flex flex-col gap-2 border-t border-[var(--color-border)] pt-3 sm:flex-row"
        >
          <Input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nombre de propiedad"
          />
          <Input
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="Dirección (opcional)"
          />
          <Button type="submit" variant="outline" disabled={saving}>
            {saving ? "…" : "Añadir"}
          </Button>
        </form>
        {error && (
          <p className="text-sm text-[var(--color-destructive)]">{error}</p>
        )}
      </CardContent>
    </Card>
  );
}
