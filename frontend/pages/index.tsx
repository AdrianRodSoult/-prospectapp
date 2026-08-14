import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { api, saveToken } from "../lib/api";

export default function Home() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sessionExpiredNotice, setSessionExpiredNotice] = useState(false);

  useEffect(() => {
    if (window.sessionStorage.getItem("session_expired")) {
      setSessionExpiredNotice(true);
      window.sessionStorage.removeItem("session_expired");
    }
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "register") {
        await api.post("/api/auth/register", { email, password, full_name: fullName });
      }
      const form = new URLSearchParams();
      form.set("username", email);
      form.set("password", password);
      const resp = await api.post("/api/auth/login", form, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      saveToken(resp.data.access_token);
      router.push("/onboarding");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Ha ocurrido un error. Inténtalo de nuevo.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-paper flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="inline-block tag-stamp text-moss text-xs px-2 py-0.5 mb-3">MODO DEMO · GRATIS</div>
          <h1 className="font-display text-3xl text-ink">ProspectApp</h1>
          <p className="mt-2 text-sm text-ink/60">
            Encuentra negocios locales con oportunidad real de mejorar su web.
          </p>
        </div>

        <form onSubmit={submit} className="space-y-3 bg-white border border-line rounded-2xl p-5 shadow-sm">
          {sessionExpiredNotice && (
            <div className="rounded-xl bg-clay/10 border border-clay/30 text-clay text-sm px-4 py-2.5">
              Tu sesión ha caducado. Vuelve a iniciar sesión para continuar.
            </div>
          )}
          {mode === "register" && (
            <input
              className="w-full rounded-xl border border-line px-4 py-3 text-base"
              placeholder="Tu nombre"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          )}
          <input
            className="w-full rounded-xl border border-line px-4 py-3 text-base"
            placeholder="Email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            className="w-full rounded-xl border border-line px-4 py-3 text-base"
            placeholder="Contraseña"
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <p className="text-sm text-clay">{error}</p>}
          <button
            disabled={loading}
            className="w-full rounded-xl bg-moss text-white py-3 font-medium disabled:opacity-60"
          >
            {loading ? "Un momento…" : mode === "login" ? "Entrar" : "Crear cuenta"}
          </button>
        </form>

        <button
          onClick={() => setMode(mode === "login" ? "register" : "login")}
          className="w-full text-center text-sm text-ink/60 mt-4"
        >
          {mode === "login" ? "¿No tienes cuenta? Regístrate" : "¿Ya tienes cuenta? Inicia sesión"}
        </button>

        <p className="text-xs text-ink/40 text-center mt-6">
          Funciona sin coste en modo demostración. Puedes conectar Google Places, Claude/GPT
          y Gmail más adelante desde el servidor.
        </p>
      </div>
    </div>
  );
}
