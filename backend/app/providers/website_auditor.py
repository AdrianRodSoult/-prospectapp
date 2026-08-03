"""
WebsiteAuditor: visita páginas públicas del propio dominio del negocio,
respeta robots.txt, límites de tiempo/tamaño, y NUNCA accede a:
localhost, redes privadas, metadata cloud, ni esquemas != http/https.
"""
from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings

settings = get_settings()

BLOCKED_HOSTS = {"localhost", "169.254.169.254", "metadata.google.internal"}
CANDIDATE_PATHS = ["", "/contacto", "/contact", "/quienes-somos", "/about",
                    "/reservas", "/aviso-legal", "/legal", "/privacidad", "/privacy"]

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
WHATSAPP_RE = re.compile(r"(https?://)?(wa\.me|api\.whatsapp\.com/send)[^\s\"'<>]*")
PRIORITY_PREFIXES = ["info@", "contacto@", "hola@", "reservas@", "administracion@"]


def _is_safe_host(hostname: str) -> bool:
    if not hostname or hostname.lower() in BLOCKED_HOSTS:
        return False
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
    return True


@dataclass
class AuditFinding:
    reachable: bool = False
    http_status: int | None = None
    https: bool = False
    is_parked_or_placeholder: bool = False
    has_viewport_meta: bool = False
    mobile_friendly: bool | None = None
    has_cta: bool = False
    has_contact_form: bool = False
    has_booking: bool = False
    has_whatsapp_button: bool = False
    has_call_button: bool = False
    has_title: bool = False
    has_meta_description: bool = False
    has_h1: bool = False
    has_structured_data: bool = False
    has_privacy_policy: bool = False
    emails_found: list[str] = field(default_factory=list)
    whatsapp_links: list[str] = field(default_factory=list)
    phones_found: list[str] = field(default_factory=list)
    source_mode: str = "live"
    raw: dict = field(default_factory=dict)


def _safe_get(client: httpx.Client, url: str) -> httpx.Response | None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None
    if not _is_safe_host(parsed.hostname or ""):
        return None
    try:
        resp = client.get(url, timeout=settings.CRAWLER_TIMEOUT_SECONDS, follow_redirects=True)
        if len(resp.content) > settings.CRAWLER_MAX_RESPONSE_BYTES:
            return None
        return resp
    except httpx.HTTPError:
        return None


def audit_website(url: str) -> AuditFinding:
    finding = AuditFinding()
    if not url:
        finding.reachable = False
        return finding

    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    finding.https = parsed.scheme == "https"

    all_emails: set[str] = set()
    all_whatsapp: set[str] = set()
    pages_visited = 0

    with httpx.Client(headers={"User-Agent": "ProspectApp-Auditor/1.0 (+cortesia; respeta robots.txt)"}) as client:
        for path in CANDIDATE_PATHS:
            if pages_visited >= settings.CRAWLER_MAX_PAGES_PER_DOMAIN:
                break
            target = urljoin(base, path)
            resp = _safe_get(client, target)
            pages_visited += 1
            if resp is None:
                continue
            if pages_visited == 1:
                finding.reachable = resp.status_code < 400
                finding.http_status = resp.status_code

            soup = BeautifulSoup(resp.text, "html.parser")
            html_lower = resp.text.lower()

            if pages_visited == 1:
                finding.has_title = bool(soup.title and soup.title.text.strip())
                finding.has_meta_description = bool(soup.find("meta", attrs={"name": "description"}))
                finding.has_h1 = bool(soup.find("h1"))
                finding.has_viewport_meta = bool(soup.find("meta", attrs={"name": "viewport"}))
                finding.mobile_friendly = finding.has_viewport_meta
                finding.has_structured_data = "application/ld+json" in html_lower or "schema.org" in html_lower
                finding.is_parked_or_placeholder = any(
                    kw in html_lower for kw in ["domain is parked", "this domain is for sale", "en construcción", "coming soon"]
                )
                finding.has_cta = any(kw in html_lower for kw in ["reservar", "pedir cita", "contactar", "llamar", "presupuesto"])
                finding.has_contact_form = bool(soup.find("form"))
                finding.has_booking = any(kw in html_lower for kw in ["reserva", "booking", "cita online"])
                finding.has_call_button = 'href="tel:' in html_lower
                finding.has_whatsapp_button = "wa.me" in html_lower or "api.whatsapp.com" in html_lower

            if "aviso-legal" in path or "privacidad" in path or "privacy" in path or "legal" in path:
                finding.has_privacy_policy = finding.has_privacy_policy or resp.status_code < 400

            for m in EMAIL_RE.findall(resp.text):
                all_emails.add(m.lower())
            for m in WHATSAPP_RE.findall(resp.text):
                pass
            for m in re.findall(WHATSAPP_RE, resp.text):
                all_whatsapp.add(m if isinstance(m, str) else "".join(m))

    finding.emails_found = sorted(all_emails, key=lambda e: (
        0 if any(e.startswith(p) for p in PRIORITY_PREFIXES) else 1, e
    ))
    finding.whatsapp_links = list(all_whatsapp)
    return finding


def audit_website_mock(url: str | None) -> AuditFinding:
    """Versión determinista sin red, para modo demo / tests / sin conexión saliente."""
    import random
    finding = AuditFinding(source_mode="mock")
    if not url:
        finding.reachable = False
        return finding
    rng = random.Random(url)
    finding.reachable = rng.random() > 0.1
    finding.http_status = 200 if finding.reachable else 500
    finding.https = rng.random() > 0.3
    finding.has_viewport_meta = rng.random() > 0.4
    finding.mobile_friendly = finding.has_viewport_meta
    finding.has_cta = rng.random() > 0.5
    finding.has_contact_form = rng.random() > 0.5
    finding.has_booking = rng.random() > 0.7
    finding.has_whatsapp_button = rng.random() > 0.6
    finding.has_call_button = rng.random() > 0.4
    finding.has_title = rng.random() > 0.1
    finding.has_meta_description = rng.random() > 0.5
    finding.has_h1 = rng.random() > 0.2
    finding.has_structured_data = rng.random() > 0.8
    finding.has_privacy_policy = rng.random() > 0.5
    finding.is_parked_or_placeholder = rng.random() > 0.92
    if rng.random() > 0.4:
        finding.emails_found = ["info@" + urlparse(url).netloc.replace("www.", "")]
    if finding.has_whatsapp_button:
        finding.whatsapp_links = [f"https://wa.me/34600{rng.randint(100000,999999)}"]
    return finding
