import { useEffect, useState } from "react";
import Link from "next/link";
import NavBar from "../../components/NavBar";
import { api } from "../../lib/api";

export default function Team() {
  const [org, setOrg] = useState<any>(null);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [inviting, setInviting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { load(); }, []);

  function load() {
    api.get("/api/organizations/me").then((r) => setOrg(r.data)).catch(() => {});
  }

  async function invite(e: React.FormEvent) {
    e.preventDefault();
    setInviting(true);
    setMessage(null);
    setError(null);
    try {
      const resp = await api.post("/api/organizations/invite", { email, role });
      setMessage(
        resp.data.status === "activo"
          ? `${email} se ha unido al equipo.`
          : `Invitación enviada a ${email}. Se unirá automáticamente cuando se registre.`
      );
      setEmail("");
      load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudo invitar. Inténtalo de nuevo.");
    } finally {
      setInviting(false);
    }
  }

  const canInvite = org?.my_role === "owner" || org?.my_role === "admin";

  return (
    <div className="min-h-screen bg-paper pb-24 md:pt-20 md:pb-10">
      <NavBar />
      <div className="mx-auto max-w-xl px-4 pt-6 md:pt-0">
        <h1 className="font-display text-2xl mb-1">Tu equipo</h1>
        <p className="text-sm text-ink/60 mb-6">
          Todos los miembros de tu equipo ven los mismos negocios, perfiles y CRM.
        </p>
        <Link href="/settings/api-keys" className="text-sm text-moss underline block mb-6">
          ⚙ Ir a tus claves de API →
        </Link>

        {org && (
          <div className="bg-white border border-line rounded-2xl p-4 mb-4">
            <h2 className="font-medium mb-3">{org.name}</h2>
            <div className="space-y-2">
              {org.members.map((m: any, i: number) => (
                <div key={i} className="flex items-center justify-between text-sm border-b border-line/60 pb-2">
                  <span>{m.email}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-mossLight text-moss capitalize">
                      {m.role}
                    </span>
                    {m.status === "invitación pendiente" && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-line/50 text-ink/50">
                        Pendiente
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {canInvite ? (
          <form onSubmit={invite} className="bg-white border border-line rounded-2xl p-4 space-y-3">
            <h2 className="font-medium">Invitar a un compañero</h2>
            <input
              type="email"
              required
              placeholder="email@empresa.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl border border-line px-4 py-2.5 text-sm"
            />
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full rounded-xl border border-line px-4 py-2.5 text-sm bg-white"
            >
              <option value="member">Miembro</option>
              <option value="admin">Administrador (puede invitar a otros)</option>
            </select>
            {error && <p className="text-sm text-clay">{error}</p>}
            {message && <p className="text-sm text-moss">{message}</p>}
            <button
              disabled={inviting}
              className="w-full rounded-xl bg-moss text-white py-2.5 text-sm font-medium disabled:opacity-50"
            >
              {inviting ? "Invitando…" : "Invitar"}
            </button>
          </form>
        ) : (
          <p className="text-sm text-ink/50 text-center">
            Solo el propietario o un administrador puede invitar a más personas.
          </p>
        )}
      </div>
    </div>
  );
}
