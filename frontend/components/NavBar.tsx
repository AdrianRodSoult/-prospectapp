import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { api } from "../lib/api";

const ITEMS = [
  { href: "/dashboard", label: "Panel", icon: "◧" },
  { href: "/search", label: "Buscar", icon: "◎" },
  { href: "/crm", label: "CRM", icon: "☰" },
  { href: "/profiles", label: "Perfiles", icon: "✎" },
];

export default function NavBar() {
  const router = useRouter();
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    api.get("/api/notifications?limit=1")
      .then((r) => setUnreadCount(r.data.unread_count))
      .catch(() => {});
  }, [router.pathname]);

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 border-t border-line bg-paper/95 backdrop-blur
                 md:top-0 md:bottom-auto md:border-t-0 md:border-b"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 md:px-6">
        <div className="hidden md:block py-3 font-display text-lg text-moss">ProspectApp</div>
        <div className="flex w-full justify-around md:w-auto md:gap-8 py-2 md:py-3">
          {ITEMS.map((item) => {
            const active = router.pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex flex-col items-center gap-0.5 text-xs md:flex-row md:gap-2 md:text-sm px-2 py-1 rounded-lg
                  ${active ? "text-moss font-semibold" : "text-ink/60"}`}
              >
                <span className="text-lg md:text-base">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </div>
        <div className="hidden md:flex items-center gap-4">
          <Link
            href="/notifications"
            className={`relative flex items-center gap-2 text-sm px-2 py-1 rounded-lg
              ${router.pathname.startsWith("/notifications") ? "text-moss font-semibold" : "text-ink/60"}`}
          >
            <span>🔔</span> Notificaciones
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-2 bg-clay text-white text-[10px] rounded-full px-1.5 py-0.5 leading-none">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </Link>
          <Link
            href="/settings/api-keys"
            className={`flex items-center gap-2 text-sm px-2 py-1 rounded-lg
              ${router.pathname.startsWith("/settings") ? "text-moss font-semibold" : "text-ink/60"}`}
          >
            <span>⚙</span> Ajustes
          </Link>
        </div>
      </div>
    </nav>
  );
}
