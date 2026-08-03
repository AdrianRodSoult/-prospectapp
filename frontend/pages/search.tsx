import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import NavBar from "../components/NavBar";
import { api } from "../lib/api";

export default function Search() {
  const router = useRouter();
  const [profiles, setProfiles] = useState<any[]>([]);
  const [profileId, setProfileId] = useState("");
  const [city, setCity] = useState("Algeciras");
  const [niche, setNiche] = useState("peluquería");
  const [maxResults, setMaxResults] = useState(20);
  const [hasWebsite, setHasWebsite] = useState<"any" | "yes" | "no">("any");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get("/api/profiles").then((r) => {
      setProfiles(r.data);
      const qId = router.query.profile_id as string | undefined;
      if (qId) setProfileId(qId);
      else if (r.data[0]) setProfileId(r.data[0].id);
    }).catch(() => {});
  }, [router.query.profile_id]);

  async function runSearch() {
    if (!profileId) { setError("Crea antes un perfil de prospección."); return; }
    setLoading(true);
    setError(null);
    try {
      const resp = await api.post("/api/searches", {
        profile_id: profileId, city, niche, max_results: maxResults,
        has_website: hasWebsite === "any" ? null : hasWebsite === "yes",
      });
      const ids = resp.data.map((b: any) => b.id);
      window.sessionStorage.setItem("last_search_business_ids", JSON.stringify(ids));
      router.push("/results");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "No se pudo completar la búsqueda.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-paper pb-24 md:pt-20 md:pb-10">
      <NavBar />
      <div className="mx-auto max-w-xl px-4 pt-6 md:pt-0">
        <h1 className="font-display text-2xl mb-1">Nueva búsqueda</h1>
        <p className="text-sm text-ink/60 mb-5">
          Datos de demostración por defecto — sin coste. Conecta Google Places en el servidor para usar datos reales.
        </p>

        <div className="bg-white border border-line rounded-2xl p-4 space-y-4">
          <div>
            <label className="text-sm text-ink/60">Perfil de prospección</label>
            <select
              value={profileId}
              onChange={(e) => setProfileId(e.target.value)}
              className="w-full mt-1 rounded-xl border border-line px-4 py-3"
            >
              {profiles.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm text-ink/60">Ciudad</label>
              <input value={city} onChange={(e) => setCity(e.target.value)}
                     className="w-full mt-1 rounded-xl border border-line px-4 py-3" />
            </div>
            <div>
              <label className="text-sm text-ink/60">Nicho</label>
              <input value={niche} onChange={(e) => setNiche(e.target.value)}
                     className="w-full mt-1 rounded-xl border border-line px-4 py-3" />
            </div>
          </div>

          <div>
            <label className="text-sm text-ink/60">Presencia web</label>
            <div className="flex gap-2 mt-1">
              {(["any", "no", "yes"] as const).map((v) => (
                <button
                  key={v}
                  onClick={() => setHasWebsite(v)}
                  className={`flex-1 rounded-xl border px-3 py-2 text-sm ${
                    hasWebsite === v ? "border-moss bg-mossLight text-moss" : "border-line"
                  }`}
                >
                  {v === "any" ? "Cualquiera" : v === "no" ? "Sin web" : "Con web"}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-sm text-ink/60">Máximo de resultados: {maxResults}</label>
            <input type="range" min={5} max={60} step={5} value={maxResults}
                   onChange={(e) => setMaxResults(parseInt(e.target.value))} className="w-full" />
          </div>

          {error && <p className="text-sm text-clay">{error}</p>}

          <button
            onClick={runSearch}
            disabled={loading}
            className="w-full rounded-xl bg-moss text-white py-3 font-medium disabled:opacity-60"
          >
            {loading ? "Buscando…" : "Buscar negocios"}
          </button>
        </div>
      </div>
    </div>
  );
}
