from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "Velnio"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api"

    DATABASE_URL: str = "postgresql+asyncpg://velnio:velnio@localhost:5432/velnio"

    JWT_SECRET: str = "dev-jwt-secret-change-in-production-32-bytes-minimum"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ENCRYPTION_KEY: str = "dev-encryption-key-change-in-production"

    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    AI_PROVIDER: str = "mock"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5.6-terra"
    OPENAI_TIMEOUT_SECONDS: float = 30.0

    IMAGE_PROVIDER: str = "mock"
    OPENAI_IMAGE_MODEL: str = "gpt-image-1"

    STORAGE_PROVIDER: str = "local"
    STORAGE_LOCAL_PATH: str = "./storage"
    STORAGE_PUBLIC_URL: str = "http://localhost:8000/storage"
    S3_BUCKET: str = ""
    S3_REGION: str = "us-east-2"

    SHOPIFY_MODE: str = "mock"
    SHOPIFY_API_KEY: str = ""
    SHOPIFY_API_SECRET: str = ""
    SHOPIFY_SCOPES: str = "read_products,write_products"
    SHOPIFY_REDIRECT_URI: str = "http://localhost:8000/api/stores/shopify/callback"
    SHOPIFY_API_VERSION: str = "2026-07"
    SHOPIFY_REQUEST_TIMEOUT_SECONDS: float = 15.0

    BILLING_PROVIDER: str = "mock"
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_LAUNCH: str = ""
    STRIPE_PRICE_GROWTH: str = ""
    STRIPE_PRICE_SCALE: str = ""
    STRIPE_TRIAL_DAYS: int = 7
    FRONTEND_URL: str = "http://localhost:5173"

    GOOGLE_DRIVE_PROVIDER: str = "mock"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/google-drive/callback"
    GOOGLE_DRIVE_SCOPES: str = "https://www.googleapis.com/auth/drive.readonly"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()
