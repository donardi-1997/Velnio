from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    APP_NAME: str = "Velnio"
    APP_ENV: str = "development"

    DATABASE_URL: str = "postgresql+asyncpg://velnio:velnio@localhost:5432/velnio"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://velnio:velnio@localhost:5432/velnio"

    JWT_SECRET: str = "dev-secret-change-in-production-velnio"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    ENCRYPTION_KEY: str = "dev-encryption-key-change-in-production"

    AI_PROVIDER: str = "mock"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    AI_REQUEST_TIMEOUT_SECONDS: float = 30.0

    SHOPIFY_MODE: str = "mock"
    SHOPIFY_API_KEY: str = ""
    SHOPIFY_API_SECRET: str = ""
    SHOPIFY_SCOPES: str = "read_products,write_products,write_online_store_pages,read_publications,write_publications"
    SHOPIFY_REDIRECT_URI: str = "http://localhost:8000/api/stores/shopify/callback"
    SHOPIFY_API_VERSION: str = "2026-07"
    SHOPIFY_REQUEST_TIMEOUT_SECONDS: float = 15.0

    BILLING_PROVIDER: str = "mock"
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_GROWTH: str = ""
    STRIPE_PRICE_SCALE: str = ""
    STRIPE_TRIAL_DAYS: int = 7
    STRIPE_REQUEST_TIMEOUT_SECONDS: float = 20.0

    FRONTEND_URL: str = "http://localhost:5173"

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    FREE_CREDITS: int = 10
    PLAN_ANALYSIS_COST: int = 1
    PLAN_ANGLES_COST: int = 2
    PLAN_OFFER_COST: int = 2
    PLAN_LANDING_COST: int = 5
    PLAN_SECTION_REGEN_COST: int = 1
    PLAN_BRIEF_COST: int = 3

    IMAGE_PROVIDER: str = "mock"
    OPENAI_IMAGE_MODEL: str = "dall-e-3"

    STORAGE_PROVIDER: str = "local"
    LOCAL_STORAGE_PATH: str = "./storage"
    MAX_IMAGE_UPLOAD_MB: int = 10

    PLAN_ENRICHMENT_COST: int = 2
    PLAN_IMAGE_COST: int = 2
    PLAN_VISUAL_DIRECTION_COST: int = 1
    PLAN_LAUNCH_PACK_COST: int = 8

    PLAN_PERFORMANCE_ANALYSIS_COST: int = 2
    PLAN_AI_VARIANT_SUGGESTION_COST: int = 2
    PLAN_CREATE_SUGGESTED_VARIANT_COST: int = 3

    EXPERIMENT_MIN_SESSIONS_PER_VARIANT: int = 100
    EXPERIMENT_MIN_PURCHASES: int = 10

    TRACKING_EVENT_RETENTION_DAYS: int = 365
    TRACKING_MAX_PAYLOAD_SIZE: int = 51200

    GOOGLE_DRIVE_MODE: str = "mock"
    GOOGLE_DRIVE_CLIENT_ID: str = ""
    GOOGLE_DRIVE_CLIENT_SECRET: str = ""
    GOOGLE_DRIVE_REDIRECT_URI: str = "http://localhost:8000/api/google-drive/callback"
    GOOGLE_DRIVE_SCOPES: str = "https://www.googleapis.com/auth/drive.file"
    GOOGLE_DRIVE_MAX_FILE_MB: int = 25

    MAX_DOCUMENT_PROCESSING_MB: int = 25
    MAX_AI_CONTEXT_CHARS: int = 50000


settings = Settings()
