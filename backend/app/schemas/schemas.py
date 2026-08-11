from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str | None
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileCreate(BaseModel):
    name: str
    service_offered: str | None = None
    ideal_customer: str | None = None
    cities: list[str] = Field(default_factory=list)
    niches: list[str] = Field(default_factory=list)
    positive_signals: list[str] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)
    value_proposition: str | None = None
    tone: str = "cercano_profesional"
    allowed_channels: list[str] = Field(default_factory=lambda: ["email"])


class ProfileOut(ProfileCreate):
    id: str
    created_at: datetime
    class Config:
        from_attributes = True


class SearchCreate(BaseModel):
    profile_id: str
    city: str
    region: str | None = None
    niche: str
    radius_km: float = 5.0
    max_results: int = 20
    min_rating: float | None = None
    max_rating: float | None = None
    min_reviews: int | None = None
    has_website: bool | None = None
    has_phone: bool | None = None
    open_now: bool | None = None


class BusinessOut(BaseModel):
    id: str
    name: str
    category: str | None
    address: str | None
    city: str | None
    latitude: float | None
    longitude: float | None
    phone_intl: str | None
    website_url: str | None
    google_maps_url: str | None
    rating: float | None
    review_count: int | None
    is_open_now: bool | None
    whatsapp_status: str
    crm_stage: str
    class Config:
        from_attributes = True


class MessageGenerateRequest(BaseModel):
    business_id: str
    profile_id: str
    channel: str = "email"


class StageUpdate(BaseModel):
    stage: str


class ApiCredentialsUpdate(BaseModel):
    """Todos los campos opcionales: solo se actualizan los que se envíen.
    Enviar un campo como cadena vacía "" borra esa key concreta."""
    google_places_api_key: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None


class ApiCredentialsStatus(BaseModel):
    """Nunca se devuelve la clave real, solo si está configurada o no."""
    google_places_configured: bool
    anthropic_configured: bool
    openai_configured: bool


class PaginatedBusinesses(BaseModel):
    items: list[BusinessOut]
    total: int
    page: int
    page_size: int
    total_pages: int
