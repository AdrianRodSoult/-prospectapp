import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import NavBar from "../components/NavBar";
import { api } from "../lib/api";

const STAGES = [
  { key: "descubierto", label: "Descubierto" },
  { key: "analizado", label: "Analizado" },
  { key: "preparado_contactar", label: "Preparado" },
  { key: "contactado", label: "Contactado" },
  { key: "respondio", label: "Respondió" },
  { key: "interesado", label: "Interesado" },
  { key: "cliente", label: "Cliente" },
  { key: "no_interesado", label: "No interesado" },
];

export default function CRM() {
  const router = useRouter();
  const [businesses, setBusinesses] = useState<any[]>([]);

  useEffect(() => {
    // El tablero Kanban necesita ver todas las etapas a la vez, así que se
    // pide una página grande en vez de paginar por columna (limitación
    // conocida: con más de 100 leads, el tablero no los mostraría todos
    // todavía — pendiente de paginación real por columna más adelante).
    api.get("/api/businesses?page_size=100").then((r) => setBusinesses(r.data.items));
  }, []);

  return (
    <div className="min-h-screen bg-paper pb-24 md:pt-20 md:pb-10">
      <NavBar />
      <div className="pt-6 md:pt-0 px-4">
        <h1 className="font-display text-2xl mb-4 max-w-5xl mx-auto">CRM</h1>
      </div>
      <div className="overflow-x-auto px-4 pb-4">
        <div className="flex gap-3 mx-auto max-w-5xl w-max md:w-auto">
          {STAGES.map((stage) => {
            const items = businesses.filter((b) => b.crm_stage === stage.key);
            return (
              <div key={stage.key} className="w-64 shrink-0">
                <div className="flex items-center justify-between mb-2 px-1">
                  <h2 className="text-sm font-medium">{stage.label}</h2>
                  <span className="text-xs text-ink/40">{items.length}</span>
                </div>
                <div className="space-y-2">
                  {items.map((b) => (
                    <button
                      key={b.id}
                      onClick={() => router.push(`/business/${b.id}`)}
                      className="w-full text-left rounded-xl border border-line bg-white p-3 active:bg-mossLight"
                    >
                      <p className="text-sm font-medium">{b.name}</p>
                      <p className="text-xs text-ink/50">{b.category}</p>
                    </button>
                  ))}
                  {items.length === 0 && (
                    <div className="rounded-xl border border-dashed border-line p-3 text-xs text-ink/30 text-center">
                      Vacío
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
