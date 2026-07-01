import { redirect } from "next/navigation";

/** La raíz redirige al dashboard; el middleware fuerza login si no hay sesión. */
export default function Home() {
  redirect("/dashboard");
}
