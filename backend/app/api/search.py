from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    Search, Business, BusinessContact, WebsiteAudit, Opportunity, LeadScore,
    ProspectingProfile, User, SuppressionEntry, Activity, ConfidenceLevel, DataSourceType,
    ProviderUsage,
)
from app.providers.business_data_provider import get_places_provider
from app.providers.website_auditor import audit_website, audit_website_mock
from app.providers.ai_provider import get_ai_provider
from app.services.opportunity_engine import detect_opportunities
from app.services.scoring_engine import compute_score
from app.schemas.schemas import SearchCreate, BusinessOut, MessageGenerateRequest, StageUpdate

router = APIRouter(prefix="/api", tags=["search"])
settings = get_settings()


def _urldomain(url: str | None) -> str | None:
    if not url:
        return None
    from urllib.parse import urlparse
    netloc = urlparse(url).netloc or url
    return netloc.replace("www.", "").lower()


@router.post("/searches", response_model=list[BusinessOut])
def run_search(payload: SearchCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    profile = db.query(ProspectingProfile).filter(
        ProspectingProfile.id == payload.profile_id, ProspectingProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(404, "Perfil no encontrado")

    max_results = min(payload.max_results, settings.MAX_RESULTS_PER_SEARCH)
    provider = get_places_provider()
    result = provider.search(payload.city, payload.niche, payload.region, payload.radius_km, max_results)

    search = Search(
        profile_id=profile.id, city=payload.city, region=payload.region, niche=payload.niche,
        radius_km=payload.radius_km, max_results=max_results,
        source_mode="live" if settings.PLACES_MODE == "live" else "mock",
        estimated_cost_usd=result.estimated_cost_usd,
        filters=payload.model_dump(exclude={"profile_id", "city", "region", "niche", "radius_km", "max_results"}),
    )
    db.add(search)
    db.flush()

    db.add(ProviderUsage(provider=result.source, operation="search", estimated_cost_usd=result.estimated_cost_usd))

    suppressed_values = {s.value for s in db.query(SuppressionEntry).all()}
    created: list[Business] = []

    for item in result.businesses:
        # Deduplicación por place_id
        existing = db.query(Business).filter(Business.place_id == item.get("place_id")).first()
        if existing:
            biz = existing
        else:
            biz = Business(
                search_id=search.id,
                name=item.get("name"),
                category=item.get("category") or payload.niche,
                address=item.get("address"),
                city=payload.city,
                region=payload.region,
                latitude=item.get("latitude"),
                longitude=item.get("longitude"),
                phone_intl=item.get("phone_intl"),
                website_url=item.get("website_url"),
                website_domain=_urldomain(item.get("website_url")),
                google_maps_url=item.get("google_maps_url"),
                place_id=item.get("place_id"),
                rating=item.get("rating"),
                review_count=item.get("review_count"),
                opening_hours=item.get("opening_hours"),
                is_open_now=item.get("is_open_now"),
                last_checked_at=datetime.utcnow(),
                data_sources=[{
                    "source": result.source, "confidence": result.confidence,
                    "checked_at": result.queried_at.isoformat(),
                }],
            )
            db.add(biz)
            db.flush()

        # Aplicar filtros post-búsqueda
        if payload.min_rating is not None and (biz.rating or 0) < payload.min_rating:
            continue
        if payload.min_reviews is not None and (biz.review_count or 0) < payload.min_reviews:
            continue
        if payload.has_website is True and not biz.website_url:
            continue
        if payload.has_website is False and biz.website_url:
            continue

        is_suppressed = (biz.place_id in suppressed_values) or (biz.website_domain in suppressed_values)
        if is_suppressed:
            biz.crm_stage = "excluido"

        # --- Auditoría web (mock o real según disponibilidad de red) ---
        audit_finding = None
        if biz.website_url:
            try:
                if settings.PLACES_MODE == "live":
                    audit_finding = audit_website(biz.website_url)
                else:
                    audit_finding = audit_website_mock(biz.website_url)
            except Exception:
                audit_finding = audit_website_mock(biz.website_url)

            audit_row = db.query(WebsiteAudit).filter(WebsiteAudit.business_id == biz.id).first()
            if not audit_row:
                audit_row = WebsiteAudit(business_id=biz.id)
                db.add(audit_row)
            audit_row.reachable = audit_finding.reachable
            audit_row.http_status = audit_finding.http_status
            audit_row.https = audit_finding.https
            audit_row.is_parked_or_placeholder = audit_finding.is_parked_or_placeholder
            audit_row.mobile_friendly = audit_finding.mobile_friendly
            audit_row.has_viewport_meta = audit_finding.has_viewport_meta
            audit_row.has_cta = audit_finding.has_cta
            audit_row.has_contact_form = audit_finding.has_contact_form
            audit_row.has_booking = audit_finding.has_booking
            audit_row.has_whatsapp_button = audit_finding.has_whatsapp_button
            audit_row.has_call_button = audit_finding.has_call_button
            audit_row.has_title = audit_finding.has_title
            audit_row.has_meta_description = audit_finding.has_meta_description
            audit_row.has_h1 = audit_finding.has_h1
            audit_row.has_structured_data = audit_finding.has_structured_data
            audit_row.has_privacy_policy = audit_finding.has_privacy_policy
            audit_row.source_mode = audit_finding.source_mode
            audit_row.audited_at = datetime.utcnow()

            if audit_finding.emails_found:
                for email in audit_finding.emails_found[:3]:
                    if not db.query(BusinessContact).filter(
                        BusinessContact.business_id == biz.id, BusinessContact.value == email
                    ).first():
                        db.add(BusinessContact(
                            business_id=biz.id, type="email", value=email,
                            subtype="generico" if email.split("@")[0] in
                            ("info", "contacto", "hola", "reservas", "administracion") else "personal",
                            confidence=ConfidenceLevel.high,
                            source=DataSourceType.business_website if audit_finding.source_mode == "live"
                            else DataSourceType.demo_mock,
                        ))
            if audit_finding.whatsapp_links:
                biz.whatsapp_link = audit_finding.whatsapp_links[0]
                biz.whatsapp_status = "confirmed"

            # --- Oportunidades ---
            db.query(Opportunity).filter(Opportunity.business_id == biz.id).delete()
            biz_dict = {"website_url": biz.website_url, "review_count": biz.review_count}
            opps = detect_opportunities(biz_dict, audit_finding)
            for o in opps:
                db.add(Opportunity(
                    business_id=biz.id, title=o.title, description=o.description, evidence=o.evidence,
                    source="website_auditor", confidence=o.confidence, estimated_impact=o.impact,
                    estimated_effort=o.effort, recommendation=o.recommendation, sales_angle=o.sales_angle,
                ))
        else:
            db.query(Opportunity).filter(Opportunity.business_id == biz.id).delete()
            opps = detect_opportunities({"website_url": None}, None)
            for o in opps:
                db.add(Opportunity(
                    business_id=biz.id, title=o.title, description=o.description, evidence=o.evidence,
                    source="business_data_provider", confidence=o.confidence, estimated_impact=o.impact,
                    estimated_effort=o.effort, recommendation=o.recommendation, sales_angle=o.sales_angle,
                ))

        # --- Puntuación ---
        has_email = db.query(BusinessContact).filter(
            BusinessContact.business_id == biz.id, BusinessContact.type == "email"
        ).first() is not None
        breakdown = compute_score(
            business={"website_url": biz.website_url, "review_count": biz.review_count,
                      "rating": biz.rating, "phone_intl": biz.phone_intl},
            audit=audit_finding,
            has_email=has_email,
            has_whatsapp_confirmed=biz.whatsapp_status == "confirmed",
            fit_points=_estimate_fit(profile, biz),
            is_suppressed=is_suppressed,
        )
        score_row = db.query(LeadScore).filter(LeadScore.business_id == biz.id).first()
        if not score_row:
            score_row = LeadScore(business_id=biz.id, total_score=0)
            db.add(score_row)
        score_row.total_score = breakdown.total
        score_row.need_score = breakdown.need_score
        score_row.potential_score = breakdown.potential_score
        score_row.contactability_score = breakdown.contactability_score
        score_row.fit_score = breakdown.fit_score
        score_row.penalties = breakdown.penalties
        score_row.priority = breakdown.priority
        score_row.main_reasons = breakdown.main_reasons
        score_row.risks = breakdown.risks
        score_row.breakdown = breakdown.details
        score_row.computed_at = datetime.utcnow()

        if biz.crm_stage == "descubierto":
            biz.crm_stage = "analizado"

        created.append(biz)

    db.commit()
    for b in created:
        db.refresh(b)
    return created


def _estimate_fit(profile: ProspectingProfile, biz: Business) -> int:
    """Heurística simple de encaje: coincidencia de ciudad/nicho con el perfil."""
    fit = 10
    if profile.cities and biz.city in profile.cities:
        fit += 5
    if profile.niches and biz.category in profile.niches:
        fit += 5
    return min(fit, 20)


@router.get("/businesses", response_model=list[BusinessOut])
def list_businesses(search_id: str | None = None, min_score: int | None = None,
                     stage: str | None = None, sort_by: str = "score",
                     db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(Business)
    if search_id:
        q = q.filter(Business.search_id == search_id)
    if stage:
        q = q.filter(Business.crm_stage == stage)
    businesses = q.all()
    if min_score is not None:
        businesses = [b for b in businesses if b.lead_score and b.lead_score.total_score >= min_score]
    if sort_by == "score":
        businesses.sort(key=lambda b: (b.lead_score.total_score if b.lead_score else 0), reverse=True)
    elif sort_by == "reviews":
        businesses.sort(key=lambda b: b.review_count or 0, reverse=True)
    elif sort_by == "rating":
        businesses.sort(key=lambda b: b.rating or 0, reverse=True)
    return businesses


@router.get("/businesses/{business_id}")
def get_business_detail(business_id: str, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    biz = db.query(Business).filter(Business.id == business_id).first()
    if not biz:
        raise HTTPException(404, "Negocio no encontrado")
    return {
        "id": biz.id, "name": biz.name, "category": biz.category, "address": biz.address,
        "city": biz.city, "phone_intl": biz.phone_intl, "website_url": biz.website_url,
        "google_maps_url": biz.google_maps_url, "rating": biz.rating, "review_count": biz.review_count,
        "whatsapp_link": biz.whatsapp_link, "whatsapp_status": biz.whatsapp_status,
        "crm_stage": biz.crm_stage, "notes": biz.notes,
        "contacts": [{"type": c.type, "value": c.value, "subtype": c.subtype,
                      "confidence": c.confidence, "source": c.source} for c in biz.contacts],
        "audit": None if not biz.website_audit else {
            "reachable": biz.website_audit.reachable, "https": biz.website_audit.https,
            "mobile_friendly": biz.website_audit.mobile_friendly,
            "has_cta": biz.website_audit.has_cta, "has_whatsapp_button": biz.website_audit.has_whatsapp_button,
            "source_mode": biz.website_audit.source_mode,
        },
        "opportunities": [{"title": o.title, "description": o.description, "evidence": o.evidence,
                           "confidence": o.confidence, "impact": o.estimated_impact,
                           "recommendation": o.recommendation, "sales_angle": o.sales_angle}
                          for o in biz.opportunities],
        "score": None if not biz.lead_score else {
            "total": biz.lead_score.total_score, "priority": biz.lead_score.priority,
            "main_reasons": biz.lead_score.main_reasons, "risks": biz.lead_score.risks,
            "breakdown": biz.lead_score.breakdown,
        },
    }


@router.patch("/businesses/{business_id}/stage")
def update_stage(business_id: str, payload: StageUpdate, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    biz = db.query(Business).filter(Business.id == business_id).first()
    if not biz:
        raise HTTPException(404, "Negocio no encontrado")
    biz.crm_stage = payload.stage
    db.add(Activity(business_id=biz.id, type="stage_change", description=f"Cambiado a {payload.stage}"))
    db.commit()
    return {"ok": True, "stage": biz.crm_stage}


@router.post("/messages/generate")
def generate_message(payload: MessageGenerateRequest, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    biz = db.query(Business).filter(Business.id == payload.business_id).first()
    profile = db.query(ProspectingProfile).filter(ProspectingProfile.id == payload.profile_id).first()
    if not biz or not profile:
        raise HTTPException(404, "Negocio o perfil no encontrado")

    ai = get_ai_provider()
    business_context = {
        "name": biz.name,
        "category": biz.category,
        "rating": biz.rating,
        "review_count": biz.review_count,
        "has_email": any(c.type == "email" for c in biz.contacts),
        "opportunities": [{"title": o.title, "evidence": o.evidence} for o in biz.opportunities],
    }
    profile_context = {
        "service_offered": profile.service_offered,
        "value_proposition": profile.value_proposition,
        "tone": profile.tone,
    }
    result = ai.generate_message(business_context, profile_context, payload.channel)

    from app.models.models import MessageDraft
    draft = MessageDraft(
        business_id=biz.id, channel=payload.channel,
        subject=result.content.get("subject"), body=result.content.get("body", ""),
        short_version=result.content.get("short_version"),
        consultative_version=result.content.get("consultative_version"),
        follow_up=result.content.get("follow_up"),
        objection_response=result.content.get("objection_response"),
        used_evidence=business_context["opportunities"],
        ai_provider=result.provider, ai_model=result.model,
        confidence=ConfidenceLevel.medium,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return {
        "id": draft.id, "channel": draft.channel, "subject": draft.subject, "body": draft.body,
        "short_version": draft.short_version, "consultative_version": draft.consultative_version,
        "follow_up": draft.follow_up, "objection_response": draft.objection_response,
        "ai_provider": draft.ai_provider, "used_evidence": draft.used_evidence,
    }


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    all_biz = db.query(Business).all()
    total = len(all_biz)
    by_stage: dict[str, int] = {}
    for b in all_biz:
        by_stage[b.crm_stage] = by_stage.get(b.crm_stage, 0) + 1
    high_priority = sum(1 for b in all_biz if b.lead_score and b.lead_score.priority in ("muy_alta", "alta"))
    total_cost = sum(u.estimated_cost_usd for u in db.query(ProviderUsage).all())
    return {
        "total_businesses": total,
        "by_stage": by_stage,
        "high_priority_count": high_priority,
        "estimated_total_cost_usd": round(total_cost, 4),
    }
