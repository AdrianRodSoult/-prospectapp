import { useState } from "react";
import { useRouter } from "next/router";
import { api } from "../lib/api";

type Step = {
  key: string;
  question: string;
  placeholder: string;
  suggestions?: string[];
  multi?: boolean;
};

const STEPS: Step[] = [
  { key: "name", question: "Para empezar, ¿cómo quieres llamar a este perfil de prospección?",
    placeholder: "Ej. Webs para peluquerías" },
  { key: "service_offered", question: "¿Qué servicio quieres vender?",
    placeholder: "Ej. Creación de páginas web para negocios locales" },
  { key: "value_proposition", question: "¿Cuál es tu propuesta de valor?",
    placeholder: "Ej. Webs sencillas, rápidas y pensadas para captar clientes desde el móvil" },
  { key: "niches_text", question: "¿Qué tipo de negocios te interesan?",
    placeholder: "Ej. peluquerías, restaurantes",
    suggestions: ["Peluquerías", "Restaurantes", "Clínicas", "Gimnasios"] },
  { key: "cities_text", question: "¿En qué ciudad o zona quieres buscar?",
    placeholder: "Ej. Algeciras, Cádiz" },
  { key: "tone", question: "¿Qué tono de comunicación prefieres?",
    placeholder: "cercano_profesional",
    suggestions: ["Cercano y profesional", "Muy formal", "Directo y breve"] },
];

export default function Onboarding() {
  const router = useRouter();
  const [stepIndex, setStepIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const step = STEPS[stepIndex];
  const isLast = stepIndex === STEPS.length - 1;

  function setAnswer(value: string) {
    setAnswers({ ...answers, [step.key]: value });
  }

  async function next() {
    if (isLast) {
      setSaving(true);
      try {
        await api.post("/api/profiles", {
          name: answers.name || "Mi perfil de prospección",
          service_offered: answers.service_offered,
          value_proposition: answers.value_proposition,
          tone: answers.tone || "cercano_profesional",
          niches: (answers.niches_text || "").split(",").map((s) => s.trim()).filter(Boolean),
          cities: (answers.cities_text || "").split(",").map((s) => s.trim()).filter(Boolean),
          allowed_channels: ["email", "whatsapp"],
        });
        router.push("/search");
      } catch {
        setSaving(false);
      }
    } else {
      setStepIndex(stepIndex + 1);
    }
  }

  return (
    <div className="min-h-screen bg-paper flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-md">
        <div className="mb-6 flex gap-1">
          {STEPS.map((_, i) => (
            <div key={i} className={`h-1 flex-1 rounded-full ${i <= stepIndex ? "bg-moss" : "bg-line"}`} />
          ))}
        </div>

        <h1 className="font-display text-2xl text-ink mb-4 leading-snug">{step.question}</h1>

        <textarea
          autoFocus
          className="w-full rounded-xl border border-line px-4 py-3 text-base min-h-[100px] bg-white"
          placeholder={step.placeholder}
          value={answers[step.key] || ""}
          onChange={(e) => setAnswer(e.target.value)}
        />

        {step.suggestions && (
          <div className="flex flex-wrap gap-2 mt-3">
            {step.suggestions.map((s) => (
              <button
                key={s}
                onClick={() => setAnswer(s)}
                className="text-sm px-3 py-1.5 rounded-full border border-line bg-white hover:bg-mossLight"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <div className="mt-6 flex gap-3">
          {stepIndex > 0 && (
            <button
              onClick={() => setStepIndex(stepIndex - 1)}
              className="px-4 py-3 rounded-xl border border-line text-ink/70"
            >
              Atrás
            </button>
          )}
          <button
            onClick={next}
            disabled={saving}
            className="flex-1 rounded-xl bg-moss text-white py-3 font-medium disabled:opacity-60"
          >
            {saving ? "Creando perfil…" : isLast ? "Crear perfil y buscar" : "Siguiente"}
          </button>
        </div>

        <button onClick={() => router.push("/search")} className="w-full text-center text-sm text-ink/40 mt-4">
          Saltar por ahora
        </button>
      </div>
    </div>
  );
}
