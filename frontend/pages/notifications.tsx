import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import NavBar from "../components/NavBar";
import { api } from "../lib/api";

const TYPE_ICON: Record<string, string> = {
  high_priority_lead: "⭐",
  business_responded: "💬",
};

export default function Notifications() {
  const router = useRouter();
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => { load(); }, []);

  function load() {
    setLoading(true);
    api.get("/api/notifications?limit=50")
      .then((r) => {
        setItems(r.data.items);
        setUnreadCount(r.data.unread_count);
      })
      .finally(() => setLoading(false));
  }

  async function markRead(id: string) {
    await api.post(`/api/notifications/${id}/read`);
    load();
  }

  async function markAllRead() {
    await api.post("/api/notifications/read-all");
    load();
  }

  return (
    <div className="min-h-screen bg-paper pb-24 md:pt-20 md:pb-10">
      <NavBar />
      <div className="mx-auto max-w-xl px-4 pt-6 md:pt-0">
        <div className="flex items-center justify-between mb-4">
          <h1 className="font-display text-2xl">Notificaciones</h1>
          {unreadCount > 0 && (
            <button onClick={markAllRead} className="text-sm text-moss underline">
              Marcar todas como leídas
            </button>
          )}
        </div>

        {loading && (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-16 bg-white border border-line rounded-xl animate-pulse" />
            ))}
          </div>
        )}

        {!loading && items.length === 0 && (
          <div className="rounded-2xl border border-dashed border-line bg-white p-6 text-center text-ink/60">
            Sin notificaciones todavía. Aquí verás avisos de leads de alta prioridad y respuestas.
          </div>
        )}

        <div className="space-y-2">
          {items.map((n) => (
            <div
              key={n.id}
              className={`rounded-xl border border-line p-3 flex items-start justify-between gap-3 ${
                n.read ? "bg-white" : "bg-mossLight"
              }`}
            >
              <button
                onClick={() => n.business_id && router.push(`/business/${n.business_id}`)}
                className="flex items-start gap-2 text-left flex-1"
              >
                <span>{TYPE_ICON[n.type] || "🔔"}</span>
                <div>
                  <p className="text-sm">{n.message}</p>
                  <p className="text-xs text-ink/40 mt-0.5">
                    {new Date(n.created_at).toLocaleString("es-ES")}
                  </p>
                </div>
              </button>
              {!n.read && (
                <button
                  onClick={() => markRead(n.id)}
                  className="text-xs text-moss shrink-0 mt-1"
                >
                  Marcar leída
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
