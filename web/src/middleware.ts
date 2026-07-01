import { type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

/** Middleware global: refresca la sesión y protege rutas privadas. */
export async function middleware(request: NextRequest) {
  return await updateSession(request);
}

export const config = {
  // Aplica a todo excepto assets estáticos e imágenes.
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
