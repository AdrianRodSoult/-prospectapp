import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import NavBar from "../components/NavBar";
import { api } from "../lib/api";

export default function Results() {
  const router = useRouter();
  const [businesses, setBusinesses] = useState<any[]>([]);
  const [sortBy, setSortBy] = useState("score");
  const [loading, setLoading] = useState(true);
  const [dataSource, setDataSource] = useState<string | null>(null);
  const [dataWarning, setDataWarning] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const PAGE_SIZE = 20;

  useEffect(() => { setPage(1); }, [sortBy]);
  useEffect(() => { load(); }, [sortBy, page]);

  useEffect(() => {
    setDataSource(window.sessionStorage.getItem("last_search_data_source"));
    const warning = window.sessionStorage.getItem("last_search_data_warning");
    setDataWarning(warning || null);
  }, []);

  function load() {
    setLoading(true);
    api.get(`/api/businesses?sort_by=${sortBy}&page=${page}&page_size=${PAGE_SIZE}`)
      .then((r) => {
        setBusinesses(r.data.items);
        setTotalPages(r.data.total_pages);
        setTotal(r.data.total);
      })
      .finally(() => setLoading(false));
  }

  return (
    <div className="min-h-screen bg-paper pb-24 md:pt-20 md:pb-10">
      <NavBar />
      <div className="mx-auto max-w-3xl px-4 pt-6 md:pt-0">
        <div className="flex items-center justify-between mb-4">
          <h1 className="font-display text-2xl">Resultados</h1>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}
                  className="rounded-lg border border-line px-2 py-1.5 text-sm bg-white">
            <option value="score">Ordenar: puntuación</option>
            <option value="reviews">Ordenar: reseñas</option>
            <option value="rating">Ordenar: valoración</option>
          </select>
        </div>

        {dataSource === "live" && (
          <div className="rounded-xl bg-mossLight border border-moss/30 text-moss text-sm px-4 py-2.5 mb-4">
            ✓ Datos reales de Google Places
          </div>
        )}
        {dataSource === "mock" && (
          <div className="rounded-xl bg-line/40 border border-line text-ink/60 text-sm px-4 py-2.5 mb-4">
            Modo demostración — datos de ejemplo, no negocios reales.
          </div>
        )}
        {dataSource === "live_fallback_mock" && (
          <div className="rounded-xl bg-clay/10 border border-clay/30 text-clay text-sm px-4 py-2.5 mb-4">
            ⚠ No se pudo conectar con Google Places, así que se muestran datos de
            demostración como respaldo. {dataWarning && <span className="block text-xs mt-1 opacity-80">{dataWarning}</span>}
          </div>
        )}

        {loading && <p className="text-sm text-ink/50">Cargando…</p>}
        {!loading && businesses.length === 0 && (
          <div className="rounded-2xl border border-dashed border-line bg-white p-6 text-center text-ink/60">
            Todavía no hay resultados. <button className="text-moss underline" onClick={() => router.push("/search")}>Haz una búsqueda</button>.
          </div>
        )}

        <div className="space-y-3">
          {businesses.map((b) => (
            <button
              key={b.id}
              onClick={() => router.push(`/business/${b.id}`)}
              className="w-full text-left rounded-2xl border border-line bg-white p-4 active:bg-mossLight transition"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="font-medium">{b.name}</h2>
                  <p className="text-xs text-ink/50 mt-0.5">{b.category} · {b.city}</p>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2 mt-3 text-xs">
                {b.rating && <Chip>{"★"} {b.rating} ({b.review_count})</Chip>}
                <Chip>{b.website_url ? "Con web" : "Sin web"}</Chip>
                <Chip>{b.whatsapp_status === "confirmed" ? "WhatsApp ✓" : "WhatsApp no verificado"}</Chip>
                <span className="ml-auto tag-stamp text-moss px-2 py-0.5">{b.crm_stage.replaceAll("_", " ")}</span>
              </div>
            </button>
          ))}
        </div>

        <p className="text-xs text-ink/40 mt-6 text-center">
          Nota: el mapa interactivo requiere una clave de Google Maps configurada en el servidor
          (no se activa por defecto para mantener la app gratuita).
        </p>

        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-3 mt-6">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="rounded-lg border border-line bg-white px-3 py-2 text-sm disabled:opacity-30"
            >
              ← Anterior
            </button>
            <span className="text-sm text-ink/60">
              Página {page} de {totalPages} · {total} negocios
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="rounded-lg border border-line bg-white px-3 py-2 text-sm disabled:opacity-30"
            >
              Siguiente →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return <span className="px-2 py-1 rounded-full bg-mossLight text-moss">{children}</span>;
}


