import { useEffect, useState } from "react";
import NavBar from "../../components/NavBar";
import { api } from "../../lib/api";

type Provider = {
  key: "google_places_api_key" | "anthropic_api_key" | "openai_api_key";
  label: string;
  placeholder: string;
  helpUrl: string;
  helpLabel: string;
  configuredField: "google_places_configured" | "anthropic_configured" | "openai_configured";
};

const PROVIDERS: Provider[] = [
  {
    key: "google_places_api_key",
    label: "Google Places",
    placeholder: "AIza...",
    helpUrl: "https://console.cloud.google.com/",
    helpLabel: "Consíguela en Google Cloud Console",
    configuredField: "google_places_configured",
  },
  {
    key: "anthropic_api_key",
    label: "Claude (Anthropic)",
    placeholder: "sk-ant-...",
    helpUrl: "https://console.anthropic.com/",
    helpLabel: "Consíguela en console.anthropic.com",
    configuredField: "anthropic_configured",
  },
  {
    key: "openai_api_key",
    label: "GPT (OpenAI)",
    placeholder: "sk-...",
    helpUrl: "https://platform.openai.com/api-keys",
    helpLabel: "Consíguela en platform.openai.com",
    configuredField: "openai_configured",
  },
];

export default function ApiKeysSettings() {
  const [status, setStatus] = useState<Record<string, boolean> | null>(null);
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => { load(); }, []);

  function load() {
    api.get("/api/settings/api-keys").then((r) => setStatus(r.data)).catch(() => {});
  }

  async function save(provider: Provider) {
    const value = inputs[provider.key];
    if (!value) return;
    setSaving(provider.key);
    setMessage(null);
    try {
      const resp = await api.put("/api/settings/api-keys", { [provider.key]: value });
      setStatus(resp.data);
      setInputs({ ...inputs, [provider.key]: "" });
      setMessage(`${provider.label}: clave guardada correctamente.`);
    } catch {
      setMessage(`${provider.label}: no se pudo guardar. Inténtalo de nuevo.`);
    } finally {
      setSaving(null);
    }
  }

  async function remove(provider: Provider) {
    setSaving(provider.key);
    setMessage(null);
    try {
      const resp = await api.put("/api/settings/api-keys", { [provider.key]: "" });
      setStatus(resp.data);
      setMessage(`${provider.label}: clave eliminada. Volverás al modo demo para esta integración.`);
    } finally {
      setSaving(null);
    }
  }

  return (
    <div className="min-h-screen bg-paper pb-24 md:pt-20 md:pb-10">
      <NavBar />
      <div className="mx-auto max-w-xl px-4 pt-6 md:pt-0">
        <h1 className="font-display text-2xl mb-1">Tus claves de API</h1>
        <p className="text-sm text-ink/60 mb-6">
          Opcional. Sin ellas, todo sigue funcionando en modo demostración, sin coste.
          Añade tus propias claves para usar datos y mensajes reales — el coste de cada
          API corre por tu cuenta, tú controlas tu propio gasto.
        </p>

        {message && (
          <div className="rounded-xl bg-mossLight border border-moss/30 text-moss text-sm px-4 py-2.5 mb-4">
            {message}
          </div>
        )}

        <div className="space-y-4">
          {PROVIDERS.map((p) => {
            const configured = status?.[p.configuredField];
            return (
              <div key={p.key} className="bg-white border border-line rounded-2xl p-4">
                <div className="flex items-center justify-between mb-1">
                  <h2 className="font-medium">{p.label}</h2>
                  {status && (
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      configured ? "bg-mossLight text-moss" : "bg-line/50 text-ink/50"
                    }`}>
                      {configured ? "Configurada" : "Modo demo"}
                    </span>
                  )}
                </div>
                <a href={p.helpUrl} target="_blank" rel="noreferrer"
                   className="text-xs text-moss underline">{p.helpLabel}</a>

                <div className="flex gap-2 mt-3">
                  <input
                    type="password"
                    autoComplete="off"
                    placeholder={configured ? "•••••••••••••••• (guardada)" : p.placeholder}
                    value={inputs[p.key] || ""}
                    onChange={(e) => setInputs({ ...inputs, [p.key]: e.target.value })}
                    className="flex-1 rounded-xl border border-line px-3 py-2.5 text-sm"
                  />
                  <button
                    onClick={() => save(p)}
                    disabled={saving === p.key || !inputs[p.key]}
                    className="rounded-xl bg-moss text-white px-4 py-2.5 text-sm font-medium disabled:opacity-40"
                  >
                    Guardar
                  </button>
                </div>
                {configured && (
                  <button
                    onClick={() => remove(p)}
                    disabled={saving === p.key}
                    className="text-xs text-clay mt-2"
                  >
                    Quitar esta clave
                  </button>
                )}
              </div>
            );
          })}
        </div>

        <p className="text-xs text-ink/40 mt-6 text-center">
          Tus claves se guardan cifradas. Nunca se muestran de nuevo, ni siquiera a ti —
          solo puedes reemplazarlas o quitarlas.
        </p>
      </div>
    </div>
  );
}
