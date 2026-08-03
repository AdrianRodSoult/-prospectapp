"""
Sistema de puntuación 0-100, con topes por categoría y desglose explicable.
Los pesos por defecto siguen el brief; se pueden sobrescribir por perfil
(prospecting_profile.scoring_weights).
"""
from dataclasses import dataclass, field

from app.providers.website_auditor import AuditFinding

DEFAULT_WEIGHTS = {
    "need": {
        "cap": 35,
        "no_website": 30,
        "website_down": 25,
        "not_mobile_friendly": 15,
        "slow": 10,
        "no_https": 8,
        "no_cta": 6,
        "no_conversion_channel": 5,
    },
    "potential": {
        "cap": 25,
        "reviews_200_plus": 15,
        "reviews_75_199": 10,
        "reviews_20_74": 6,
        "rating_bonus_max": 5,
        "multi_location_bonus": 5,
        "activity_signal_max": 5,
    },
    "contactability": {
        "cap": 20,
        "email_confirmed": 8,
        "phone": 4,
        "whatsapp_confirmed": 5,
        "contact_form": 2,
        "active_social": 1,
    },
    "fit": {
        "cap": 20,
    },
    "penalties": {
        "modern_website": -20,
        "already_rejected": -40,
        "closed_business": -100,
        "low_confidence_data": -15,
        "recent_contact": -30,
        "in_suppression_list": -100,
        "no_profile_fit": -20,
    },
}


@dataclass
class ScoreBreakdown:
    need_score: int = 0
    potential_score: int = 0
    contactability_score: int = 0
    fit_score: int = 0
    penalties: int = 0
    total: int = 0
    priority: str = "media"
    main_reasons: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


def _cap(value: int, cap: int) -> int:
    return max(0, min(value, cap))


def compute_score(
    business: dict,
    audit: AuditFinding | None,
    has_email: bool,
    has_whatsapp_confirmed: bool,
    fit_points: int = 10,
    weights: dict | None = None,
    is_suppressed: bool = False,
    previously_rejected: bool = False,
) -> ScoreBreakdown:
    w = weights or DEFAULT_WEIGHTS
    reasons: list[str] = []
    risks: list[str] = []

    # --- Necesidad digital ---
    need = 0
    if not business.get("website_url"):
        need += w["need"]["no_website"]
        reasons.append("Sin página web detectada (+30)")
    elif audit is not None:
        if not audit.reachable:
            need += w["need"]["website_down"]
            reasons.append("Web caída o no accesible (+25)")
        if audit.mobile_friendly is False:
            need += w["need"]["not_mobile_friendly"]
            reasons.append("Web no adaptada a móvil (+15)")
        if audit.https is False:
            need += w["need"]["no_https"]
            reasons.append("Web sin HTTPS (+8)")
        if not audit.has_cta and not audit.has_contact_form and not audit.has_booking:
            need += w["need"]["no_cta"]
            reasons.append("Sin llamada a la acción clara (+6)")
    need = _cap(need, w["need"]["cap"])

    # --- Potencial comercial ---
    potential = 0
    reviews = business.get("review_count") or 0
    if reviews >= 200:
        potential += w["potential"]["reviews_200_plus"]
        reasons.append(f"{reviews} reseñas (+15)")
    elif reviews >= 75:
        potential += w["potential"]["reviews_75_199"]
        reasons.append(f"{reviews} reseñas (+10)")
    elif reviews >= 20:
        potential += w["potential"]["reviews_20_74"]
        reasons.append(f"{reviews} reseñas (+6)")
    rating = business.get("rating") or 0
    if rating >= 4.5:
        potential += w["potential"]["rating_bonus_max"]
    elif rating >= 4.0:
        potential += int(w["potential"]["rating_bonus_max"] * 0.6)
    potential = _cap(potential, w["potential"]["cap"])

    # --- Facilidad de contacto ---
    contact = 0
    if has_email:
        contact += w["contactability"]["email_confirmed"]
        reasons.append("Email corporativo confirmado (+8)")
    if business.get("phone_intl") or business.get("phone"):
        contact += w["contactability"]["phone"]
        reasons.append("Teléfono disponible (+4)")
    if has_whatsapp_confirmed:
        contact += w["contactability"]["whatsapp_confirmed"]
        reasons.append("WhatsApp confirmado (+5)")
    if audit is not None and audit.has_contact_form:
        contact += w["contactability"]["contact_form"]
    contact = _cap(contact, w["contactability"]["cap"])

    # --- Encaje con cliente ideal (calculado externamente, aquí solo se acota) ---
    fit = _cap(fit_points, w["fit"]["cap"])

    # --- Penalizaciones ---
    penalties = 0
    if audit is not None and audit.reachable and audit.mobile_friendly and audit.https and audit.has_cta:
        penalties += w["penalties"]["modern_website"]
        risks.append("La web ya parece moderna y funcional: menor margen de mejora evidente.")
    if previously_rejected:
        penalties += w["penalties"]["already_rejected"]
        risks.append("Este negocio ya rechazó un contacto anterior.")
    if is_suppressed:
        penalties += w["penalties"]["in_suppression_list"]
        risks.append("Está en la lista de exclusión: no debe contactarse.")

    total = max(0, min(100, need + potential + contact + fit + penalties))

    if total >= 75:
        priority = "muy_alta"
    elif total >= 55:
        priority = "alta"
    elif total >= 30:
        priority = "media"
    else:
        priority = "baja"

    return ScoreBreakdown(
        need_score=need,
        potential_score=potential,
        contactability_score=contact,
        fit_score=fit,
        penalties=penalties,
        total=total,
        priority=priority,
        main_reasons=reasons[:6],
        risks=risks,
        details={
            "need": need, "potential": potential, "contact": contact,
            "fit": fit, "penalties": penalties,
        },
    )
