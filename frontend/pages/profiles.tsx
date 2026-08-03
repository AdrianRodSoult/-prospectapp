import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import NavBar from "../components/NavBar";
import { api } from "../lib/api";

export default function Profiles() {
  const router = useRouter();
  const [profiles, setProfiles] = useState<any[]>([]);

  useEffect(() => {
    api.get("/api/profiles").then((r) => setProfiles(r.data)).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-paper pb-24 md:pt-20 md:pb-10">
      <NavBar />
      <div className="mx-auto max-w-3xl px-4 pt-6 md:pt-0">
        <div className="flex items-center justify-between mb-4">
          <h1 className="font-display text-2xl">Perfiles de prospección</h1>
          <button
            onClick={() => router.push("/onboarding")}
            className="text-sm rounded-xl border border-line bg-white px-3 py-2"
          >
            + Nuevo
          </button>
        </div>

        {profiles.length === 0 && (
          <div className="rounded-2xl border border-dashed border-line bg-white p-6 text-center text-ink/60">
            Aún no tienes perfiles. Crea uno para definir qué vendes y a quién buscas.
          </div>
        )}

        <div className="space-y-3">
          {profiles.map((p) => (
            <div key={p.id} className="rounded-2xl border border-line bg-white p-4">
              <div className="flex items-center justify-between">
                <h2 className="font-medium">{p.name}</h2>
                <button
                  onClick={() => router.push(`/search?profile_id=${p.id}`)}
                  className="text-sm text-moss font-medium"
                >
                  Buscar con este →
                </button>
              </div>
              {p.value_proposition && <p className="text-sm text-ink/60 mt-1">{p.value_proposition}</p>}
              <div className="flex flex-wrap gap-2 mt-2">
                {(p.niches || []).map((n: string) => (
                  <span key={n} className="text-xs px-2 py-0.5 rounded-full bg-mossLight text-moss">{n}</span>
                ))}
                {(p.cities || []).map((c: string) => (
                  <span key={c} className="text-xs px-2 py-0.5 rounded-full bg-line/60">{c}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
