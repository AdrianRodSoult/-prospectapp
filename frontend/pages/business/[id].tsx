import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import NavBar from "../../components/NavBar";
import { api } from "../../lib/api";

const STAGES = [
  "descubierto", "analizado", "preparado_contactar", "contactado",
  "respondio", "interesado", "reunion_concertada", "cliente", "no_interesado",
];

export default function BusinessDetail() {
  const router = useRouter();
  const { id } = router.query;
  const [biz, setBiz] = useState<any>(null);
  const [loadError, setLoadError] = useState(false);
  const [message, setMessage] = useState<any>(null);
  const [generating, setGenerating] = useState(false);
  const [profileId, setProfileId] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    load();
    api.get("/api/profiles").then((r) => r.data[0] && setProfileId(r.data[0].id));
  }, [id]);

  function load() {
    setLoadError(false);
    api.get(`/api/businesses/${id}`).then((r) => setBiz(r.data)).catch(() => setLoadError(true));
  }

  async function updateStage(stage: string) {
    await api.patch(`/api/businesses/${id}/stage`, { stage });
    load();
  }

  async function generateMessage(channel: string) {
    if (!profileId) return;
    setGenerating(true);
    try {
      const resp = await api.post("/api/messages/generate", { business_id: id, profile_id: profileId, channel });
      setMessage(resp.data);
    } finally {
      setGenerating(false);
    }
  }

  if (loadError) {
    return (
      <div className="min-h-screen bg-paper flex flex-col items-center justify-center px-6 text-center">
        <p className="text-ink/60 mb-4">No se pudo cargar este negocio. Puede que ya no exista o no tengas acceso.</p>
        <button onClick={() => router.push("/results")} className="text-moss underline text-sm">
          ← Volver a resultados
        </button>
      </div>
    );
  }

  if (!biz) {
    return (
      <div className="min-h-screen bg-paper pb-24 md:pt-20 md:pb-10">
        <NavBar />
        <div className="mx-auto max-w-2xl px-4 pt-6 md:pt-0">
          <div className="animate-pulse space-y-4">
            <div className="h-8 w-2/3 bg-line/50 rounded" />
            <div className="h-24 bg-white border border-line rounded-2xl" />
            <div className="h-32 bg-white border border-line rounded-2xl" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper pb-24 md:pt-20 md:pb-10">
      <NavBar />
      <div className="mx-auto max-w-2xl px-4 pt-6 md:pt-0">
        <button onClick={() => router.back()} className="text-sm text-ink/50 mb-3">← Volver</button>

        <div className="bg-white border border-line rounded-2xl p-5">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="font-display text-2xl">{biz.name}</h1>
              <p className="text-sm text-ink/60 mt-1">{biz.category} · {biz.address}</p>
            </div>
            {biz.score && (
              <div className="text-center">
                <div className="text-2xl font-display text-moss">{biz.score.total}</div>
                <div className="text-xs text-ink/50">{biz.score.priority.replaceAll("_", " ")}</div>
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-2 mt-4 text-xs">
            {biz.phone_intl && <Chip>{biz.phone_intl}</Chip>}
            {biz.website_url && <Chip><a href={biz.website_url} target="_blank" rel="noreferrer">Ver web ↗</a></Chip>}
            {biz.google_maps_url && <Chip><a href={biz.google_maps_url} target="_blank" rel="noreferrer">Google Maps ↗</a></Chip>}
            {biz.whatsapp_link && <Chip><a href={biz.whatsapp_link} target="_blank" rel="noreferrer">WhatsApp ↗</a></Chip>}
          </div>

          <div className="mt-4">
            <label className="text-xs text-ink/50">Etapa en el CRM</label>
            <select
              value={biz.crm_stage}
              onChange={(e) => updateStage(e.target.value)}
              className="w-full mt-1 rounded-xl border border-line px-4 py-2.5 bg-white"
            >
              {STAGES.map((s) => <option key={s} value={s}>{s.replaceAll("_", " ")}</option>)}
            </select>
          </div>
        </div>

        {biz.score && (
          <div className="bg-white border border-line rounded-2xl p-5 mt-4">
            <h2 className="font-medium mb-2">Por qué esta puntuación</h2>
            <ul className="text-sm space-y-1 text-ink/70">
              {biz.score.main_reasons.map((r: string, i: number) => <li key={i}>• {r}</li>)}
            </ul>
            {biz.score.risks.length > 0 && (
              <>
                <h3 className="text-sm font-medium mt-3 text-clay">Riesgos a tener en cuenta</h3>
                <ul className="text-sm space-y-1 text-ink/70">
                  {biz.score.risks.map((r: string, i: number) => <li key={i}>• {r}</li>)}
                </ul>
              </>
            )}
          </div>
        )}

        <div className="bg-white border border-line rounded-2xl p-5 mt-4">
          <h2 className="font-medium mb-3">Oportunidades detectadas</h2>
          {biz.opportunities.length === 0 && <p className="text-sm text-ink/50">Sin oportunidades detectadas todavía.</p>}
          <div className="space-y-3">
            {biz.opportunities.map((o: any, i: number) => (
              <div key={i} className="border-l-2 border-moss pl-3">
                <p className="font-medium text-sm">{o.title}</p>
                <p className="text-sm text-ink/60">{o.description}</p>
                <p className="text-xs text-ink/40 mt-1">Confianza: {o.confidence} · Evidencia: {o.evidence}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white border border-line rounded-2xl p-5 mt-4">
          <h2 className="font-medium mb-3">Generar mensaje comercial</h2>
          <div className="flex gap-2 mb-3">
            <button onClick={() => generateMessage("email")} disabled={generating}
                    className="flex-1 rounded-xl border border-line py-2.5 text-sm disabled:opacity-50">Email</button>
            <button onClick={() => generateMessage("whatsapp")} disabled={generating}
                    className="flex-1 rounded-xl border border-line py-2.5 text-sm disabled:opacity-50">WhatsApp</button>
          </div>
          {generating && <p className="text-sm text-ink/50">Generando…</p>}
          {message && (
            <div className="rounded-xl bg-mossLight p-4 text-sm space-y-2">
              {message.subject && <p><strong>Asunto:</strong> {message.subject}</p>}
              <p className="whitespace-pre-line">{message.body}</p>
              <p className="text-xs text-ink/40 pt-2 border-t border-line/60">
                Generado por: {message.ai_provider} · Puedes editar este texto antes de enviarlo.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return <span className="px-2.5 py-1 rounded-full bg-mossLight text-moss">{children}</span>;
}
