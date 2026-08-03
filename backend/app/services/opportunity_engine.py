"""
Convierte hallazgos técnicos en oportunidades comerciales concretas,
con evidencia, confianza y lenguaje siempre positivo (nunca "tu web es mala").
"""
from dataclasses import dataclass

from app.providers.website_auditor import AuditFinding


@dataclass
class OpportunityItem:
    title: str
    description: str
    evidence: str
    confidence: str  # verified|high|medium|low
    impact: str       # bajo|medio|alto
    effort: str        # bajo|medio|alto
    recommendation: str
    sales_angle: str


def detect_opportunities(business: dict, audit: AuditFinding | None) -> list[OpportunityItem]:
    items: list[OpportunityItem] = []

    if not business.get("website_url"):
        items.append(OpportunityItem(
            title="Sin página web propia",
            description="El negocio no tiene una web propia detectada.",
            evidence="No se encontró website_url en la ficha del negocio (fuente: proveedor de búsqueda).",
            confidence="high",
            impact="alto",
            effort="medio",
            recommendation="Proponer una web sencilla y funcional, orientada a captar contacto.",
            sales_angle="Muchos clientes potenciales buscan primero en Google antes de decidir; "
                         "una web ayuda a que te encuentren y confíen más rápido.",
        ))
        return items  # sin web, el resto de hallazgos de auditoría no aplican

    if audit is None:
        return items

    if not audit.reachable:
        items.append(OpportunityItem(
            title="La web no responde correctamente",
            description="La web del negocio no respondió o devolvió un error al visitarla.",
            evidence=f"HTTP status: {audit.http_status}",
            confidence="high",
            impact="alto",
            effort="bajo",
            recommendation="Recuperar o migrar la web a un hosting fiable.",
            sales_angle="Una web caída puede estar haciendo perder clientes ahora mismo.",
        ))
        return items

    if audit.is_parked_or_placeholder:
        items.append(OpportunityItem(
            title="Dominio aparcado o en construcción",
            description="La web parece un dominio aparcado o una página de 'en construcción'.",
            evidence="Se detectaron señales textuales de placeholder en la página principal.",
            confidence="medium",
            impact="alto",
            effort="medio",
            recommendation="Construir la web definitiva desde cero.",
            sales_angle="Aprovechar el dominio ya reservado para lanzar una web real.",
        ))

    if audit.https is False:
        items.append(OpportunityItem(
            title="Web sin HTTPS",
            description="La web no usa conexión segura (HTTPS).",
            evidence="El esquema detectado en la URL principal es http, no https.",
            confidence="high",
            impact="medio",
            effort="bajo",
            recommendation="Instalar certificado SSL/TLS (a menudo gratuito).",
            sales_angle="Los navegadores avisan a los visitantes cuando una web no es segura, "
                         "lo que genera desconfianza.",
        ))

    if audit.mobile_friendly is False:
        items.append(OpportunityItem(
            title="Web no adaptada a móvil",
            description="No se detectó configuración responsive (viewport) en la web.",
            evidence="Ausencia de meta viewport en la página principal.",
            confidence="high",
            impact="alto",
            effort="medio",
            recommendation="Rediseñar la web con enfoque mobile-first.",
            sales_angle="La mayoría de búsquedas locales se hacen desde el móvil; "
                         "una web no adaptada dificulta la conversión.",
        ))

    if not audit.has_cta and not audit.has_contact_form and not audit.has_booking:
        items.append(OpportunityItem(
            title="Sin llamada a la acción clara",
            description="No se detectó formulario, reserva online ni llamada a la acción visible.",
            evidence="No se encontraron formularios, botones de reserva ni CTA reconocibles.",
            confidence="medium",
            impact="medio",
            effort="bajo",
            recommendation="Añadir un botón claro de contacto/reserva en la portada.",
            sales_angle="Facilitar el siguiente paso puede aumentar directamente las consultas recibidas.",
        ))

    if not audit.has_whatsapp_button:
        items.append(OpportunityItem(
            title="Sin botón de WhatsApp",
            description="La web no muestra un enlace directo a WhatsApp.",
            evidence="No se detectó enlace wa.me ni api.whatsapp.com en las páginas revisadas.",
            confidence="medium",
            impact="medio",
            effort="bajo",
            recommendation="Añadir un botón flotante de WhatsApp.",
            sales_angle="WhatsApp suele tener mayor tasa de respuesta que el email para negocios locales.",
        ))

    if not audit.has_structured_data:
        items.append(OpportunityItem(
            title="Sin datos estructurados (SEO local)",
            description="No se detectaron datos estructurados (Schema.org) en la página.",
            evidence="No se encontró 'application/ld+json' ni referencias a schema.org.",
            confidence="medium",
            impact="bajo",
            effort="bajo",
            recommendation="Añadir marcado LocalBusiness para mejorar la aparición en buscadores.",
            sales_angle="Puede mejorar cómo se muestra el negocio en los resultados de Google.",
        ))

    if business.get("review_count", 0) and business["review_count"] >= 50 and not audit.has_booking:
        items.append(OpportunityItem(
            title="Buena reputación sin canal de conversión claro",
            description="El negocio tiene buen volumen de reseñas pero no ofrece reserva online.",
            evidence=f"{business['review_count']} reseñas registradas; sin sistema de reserva detectado.",
            confidence="medium",
            impact="alto",
            effort="medio",
            recommendation="Incorporar reservas online para capitalizar la buena reputación.",
            sales_angle="Ya generan confianza; falta facilitar la conversión de esa confianza en citas.",
        ))

    return items
