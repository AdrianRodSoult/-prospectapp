import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import NavBar from "../components/NavBar";
import { api } from "../lib/api";

export default function Dashboard() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.get("/api/dashboard").then((r) => setData(r.data)).catch(() => setError(true));
  }, []);

  return (
    <div className="min-h-screen bg-paper pb-24 md:pt-20 md:pb-10">
      <NavBar />
      <div className="mx-auto max-w-5xl px-4 pt-6 md:pt-0">
        <h1 className="font-display text-2xl mb-1">Panel principal</h1>
        <p className="text-sm text-ink/60 mb-6">Resumen de tu prospección hasta ahora.</p>

        {error && (
          <div className="rounded-xl border border-line bg-white p-4 text-sm text-ink/60">
            No se pudo cargar el panel. ¿Iniciaste sesión?{" "}
            <button className="text-moss underline" onClick={() => router.push("/")}>Ir a login</button>
          </div>
        )}

        {data && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Negocios descubiertos" value={data.total_businesses} />
            <StatCard label="Oportunidad alta" value={data.high_priority_count} accent />
            <StatCard label="Coste estimado (APIs)" value={`$${data.estimated_total_cost_usd}`} />
            <StatCard label="Etapas activas" value={Object.keys(data.by_stage).length} />
          </div>
        )}

        {data && (
          <div className="mt-6 bg-white border border-line rounded-2xl p-4">
            <h2 className="font-medium mb-3">Negocios por etapa</h2>
            <div className="space-y-2">
              {Object.entries(data.by_stage).map(([stage, count]: any) => (
                <div key={stage} className="flex justify-between text-sm border-b border-line/60 pb-2">
                  <span className="capitalize">{stage.replaceAll("_", " ")}</span>
                  <span className="font-medium">{count}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <button
          onClick={() => router.push("/search")}
          className="mt-6 w-full md:w-auto rounded-xl bg-moss text-white px-5 py-3 font-medium"
        >
          + Nueva búsqueda
        </button>
      </div>
    </div>
  );
}

function StatCard({ label, value, accent }: { label: string; value: any; accent?: boolean }) {
  return (
    <div className={`rounded-2xl border border-line p-4 ${accent ? "bg-mossLight" : "bg-white"}`}>
      <div className="text-2xl font-display">{value}</div>
      <div className="text-xs text-ink/60 mt-1">{label}</div>
    </div>
  );
}
