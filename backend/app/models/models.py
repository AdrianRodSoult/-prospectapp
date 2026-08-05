"""
Modelo de datos del MVP (Fase 1).
Cubre: users, prospecting_profiles, searches, businesses, business_contacts,
websites, website_audits, audit_findings, opportunities, lead_scores, leads,
activities, notes, tasks, message_drafts, email_connections, messages,
suppression_entries, audit_logs, provider_usage.

Entidades de Fase 2/3 (campaigns, whatsapp_connections, social_profiles,
learning_events, score_configurations) se dejan como TODO explícito en
FUTURE_WORK.md, no como código a medias.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey,
    Enum, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class ConfidenceLevel(str, enum.Enum):
    verified = "verified"       # confirmado por API oficial o dato manual
    high = "high"                # encontrado directamente en fuente pública
    medium = "medium"            # inferido con evidencia razonable
    low = "low"                  # inferencia débil de IA
    not_found = "not_found"      # buscado, no encontrado
    not_verified = "not_verified"  # no se ha podido comprobar


class DataSourceType(str, enum.Enum):
    google_places_api = "google_places_api"
    business_website = "business_website"
    ai_inference = "ai_inference"
    manual_entry = "manual_entry"
    demo_mock = "demo_mock"  # dato de demostración, nunca se muestra como real


class LeadStage(str, enum.Enum):
    descubierto = "descubierto"
    pendiente_analizar = "pendiente_analizar"
    analizado = "analizado"
    oportunidad_alta = "oportunidad_alta"
    pendiente_revisar = "pendiente_revisar"
    preparado_contactar = "preparado_contactar"
    contactado = "contactado"
    respondio = "respondio"
    interesado = "interesado"
    reunion_concertada = "reunion_concertada"
    propuesta_enviada = "propuesta_enviada"
    negociacion = "negociacion"
    cliente = "cliente"
    no_interesado = "no_interesado"
    seguimiento_futuro = "seguimiento_futuro"
    perdido = "perdido"
    excluido = "excluido"


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    profiles = relationship("ProspectingProfile", back_populates="user")


class ProspectingProfile(Base):
    __tablename__ = "prospecting_profiles"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)  # p.ej. "Webs para peluquerías"

    service_offered = Column(Text)
    ideal_customer = Column(Text)
    cities = Column(JSON, default=list)
    niches = Column(JSON, default=list)
    positive_signals = Column(JSON, default=list)
    negative_signals = Column(JSON, default=list)
    value_proposition = Column(Text)
    tone = Column(String, default="cercano_profesional")
    allowed_channels = Column(JSON, default=lambda: ["email"])
    scoring_weights = Column(JSON, default=dict)  # override de pesos por defecto
    contact_limits = Column(JSON, default=dict)
    consent_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profiles")


class Search(Base):
    __tablename__ = "searches"
    id = Column(String, primary_key=True, default=gen_uuid)
    profile_id = Column(String, ForeignKey("prospecting_profiles.id"), nullable=False)
    city = Column(String, nullable=False)
    region = Column(String, nullable=True)
    niche = Column(String, nullable=False)
    radius_km = Column(Float, default=5.0)
    max_results = Column(Integer, default=20)
    filters = Column(JSON, default=dict)
    source_mode = Column(String, default="mock")  # mock | live
    estimated_cost_usd = Column(Float, default=0.0)
    status = Column(String, default="completed")
    created_at = Column(DateTime, default=datetime.utcnow)

    results = relationship("Business", back_populates="search", cascade="all, delete-orphan")


class Business(Base):
    __tablename__ = "businesses"
    __table_args__ = (
        # Antes el place_id era único globalmente: dos clientes distintos que
        # buscaran el mismo negocio real acababan compartiendo la misma fila
        # (notas, etapa CRM, etc. se mezclaban). Ahora cada cliente (owner_user_id)
        # tiene su propia copia del negocio, aunque el place_id real coincida.
        UniqueConstraint("place_id", "owner_user_id", name="uq_business_place_id_per_owner"),
        Index("ix_business_domain", "website_domain"),
        Index("ix_business_owner", "owner_user_id"),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    search_id = Column(String, ForeignKey("searches.id"), nullable=True)
    owner_user_id = Column(String, ForeignKey("users.id"), nullable=False)

    name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    region = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    country = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    phone = Column(String, nullable=True)
    phone_intl = Column(String, nullable=True)

    website_url = Column(String, nullable=True)
    website_domain = Column(String, nullable=True)
    google_maps_url = Column(String, nullable=True)
    place_id = Column(String, nullable=True, index=True)

    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    opening_hours = Column(JSON, nullable=True)
    is_open_now = Column(Boolean, nullable=True)
    price_level = Column(Integer, nullable=True)

    whatsapp_link = Column(String, nullable=True)
    whatsapp_status = Column(String, default="not_found")  # confirmed|probable|not_found|not_verified

    last_checked_at = Column(DateTime, nullable=True)
    data_sources = Column(JSON, default=list)  # [{field, source, confidence, checked_at}]
    notes = Column(Text, nullable=True)
    tags = Column(JSON, default=list)
    crm_stage = Column(Enum(LeadStage), default=LeadStage.descubierto)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    search = relationship("Search", back_populates="results")
    contacts = relationship("BusinessContact", back_populates="business", cascade="all, delete-orphan")
    website_audit = relationship("WebsiteAudit", back_populates="business", uselist=False, cascade="all, delete-orphan")
    opportunities = relationship("Opportunity", back_populates="business", cascade="all, delete-orphan")
    lead_score = relationship("LeadScore", back_populates="business", uselist=False, cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="business", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="business", cascade="all, delete-orphan")
    message_drafts = relationship("MessageDraft", back_populates="business", cascade="all, delete-orphan")


class BusinessContact(Base):
    __tablename__ = "business_contacts"
    id = Column(String, primary_key=True, default=gen_uuid)
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False)
    type = Column(String, nullable=False)  # email | phone | social
    value = Column(String, nullable=False)
    subtype = Column(String, nullable=True)  # generico|personal|soporte|reservas
    confidence = Column(Enum(ConfidenceLevel), default=ConfidenceLevel.not_verified)
    source = Column(Enum(DataSourceType), default=DataSourceType.demo_mock)
    found_on_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="contacts")


class WebsiteAudit(Base):
    __tablename__ = "website_audits"
    id = Column(String, primary_key=True, default=gen_uuid)
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False, unique=True)

    reachable = Column(Boolean, nullable=True)
    http_status = Column(Integer, nullable=True)
    https = Column(Boolean, nullable=True)
    is_parked_or_placeholder = Column(Boolean, default=False)

    mobile_friendly = Column(Boolean, nullable=True)
    has_viewport_meta = Column(Boolean, nullable=True)
    performance_score_mobile = Column(Integer, nullable=True)  # 0-100, si hay PageSpeed
    performance_score_desktop = Column(Integer, nullable=True)
    load_time_ms = Column(Integer, nullable=True)

    has_cta = Column(Boolean, default=False)
    has_contact_form = Column(Boolean, default=False)
    has_booking = Column(Boolean, default=False)
    has_whatsapp_button = Column(Boolean, default=False)
    has_call_button = Column(Boolean, default=False)

    has_title = Column(Boolean, default=False)
    has_meta_description = Column(Boolean, default=False)
    has_h1 = Column(Boolean, default=False)
    has_structured_data = Column(Boolean, default=False)
    has_sitemap = Column(Boolean, default=False)

    has_privacy_policy = Column(Boolean, default=False)
    has_cookie_banner = Column(Boolean, default=False)

    visual_assessment = Column(JSON, nullable=True)  # {label, notes, confidence} — "evaluación estimada"
    source_mode = Column(String, default="mock")  # mock | live
    audited_at = Column(DateTime, default=datetime.utcnow)
    raw_findings = Column(JSON, default=dict)

    business = relationship("Business", back_populates="website_audit")


class Opportunity(Base):
    __tablename__ = "opportunities"
    id = Column(String, primary_key=True, default=gen_uuid)
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    evidence = Column(Text, nullable=True)
    source = Column(String, nullable=True)
    confidence = Column(Enum(ConfidenceLevel), default=ConfidenceLevel.medium)
    estimated_impact = Column(String, default="medio")  # bajo|medio|alto
    estimated_effort = Column(String, default="medio")
    recommendation = Column(Text, nullable=True)
    sales_angle = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="opportunities")


class LeadScore(Base):
    __tablename__ = "lead_scores"
    id = Column(String, primary_key=True, default=gen_uuid)
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False, unique=True)

    total_score = Column(Integer, nullable=False)
    need_score = Column(Integer, default=0)
    potential_score = Column(Integer, default=0)
    contactability_score = Column(Integer, default=0)
    fit_score = Column(Integer, default=0)
    penalties = Column(Integer, default=0)

    priority = Column(String, default="media")  # muy_alta|alta|media|baja
    main_reasons = Column(JSON, default=list)
    risks = Column(JSON, default=list)
    best_offer = Column(String, nullable=True)
    best_channel = Column(String, nullable=True)
    score_confidence = Column(Enum(ConfidenceLevel), default=ConfidenceLevel.medium)
    breakdown = Column(JSON, default=dict)  # detalle explicable de cada componente

    computed_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="lead_score")


class Activity(Base):
    __tablename__ = "activities"
    id = Column(String, primary_key=True, default=gen_uuid)
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False)
    type = Column(String, nullable=False)  # stage_change|note|email_sent|call|...
    description = Column(Text, nullable=True)
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="activities")


class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True, default=gen_uuid)
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False)
    title = Column(String, nullable=False)
    due_date = Column(DateTime, nullable=True)
    done = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="tasks")


class MessageDraft(Base):
    __tablename__ = "message_drafts"
    id = Column(String, primary_key=True, default=gen_uuid)
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False)
    channel = Column(String, nullable=False)  # email|whatsapp|call_script|form
    subject = Column(String, nullable=True)
    body = Column(Text, nullable=False)
    short_version = Column(Text, nullable=True)
    consultative_version = Column(Text, nullable=True)
    follow_up = Column(Text, nullable=True)
    objection_response = Column(Text, nullable=True)
    used_evidence = Column(JSON, default=list)
    ai_provider = Column(String, default="mock")
    ai_model = Column(String, nullable=True)
    confidence = Column(Enum(ConfidenceLevel), default=ConfidenceLevel.medium)
    status = Column(String, default="draft")  # draft|approved|sent
    gmail_draft_id = Column(String, nullable=True)
    gmail_message_id = Column(String, nullable=True)
    gmail_thread_id = Column(String, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="message_drafts")


class EmailConnection(Base):
    __tablename__ = "email_connections"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    email_address = Column(String, nullable=True)
    provider = Column(String, default="gmail")
    mode = Column(String, default="mock")  # mock|live
    access_token_encrypted = Column(Text, nullable=True)
    refresh_token_encrypted = Column(Text, nullable=True)
    connected_at = Column(DateTime, default=datetime.utcnow)
    revoked = Column(Boolean, default=False)


class SuppressionEntry(Base):
    __tablename__ = "suppression_entries"
    id = Column(String, primary_key=True, default=gen_uuid)
    value = Column(String, nullable=False, index=True)  # email, dominio o place_id
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=True)
    entity_id = Column(String, nullable=True)
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProviderUsage(Base):
    __tablename__ = "provider_usage"
    id = Column(String, primary_key=True, default=gen_uuid)
    provider = Column(String, nullable=False)  # google_places|anthropic|openai|pagespeed
    operation = Column(String, nullable=True)
    estimated_cost_usd = Column(Float, default=0.0)
    units = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
