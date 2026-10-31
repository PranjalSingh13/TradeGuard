from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    PROJECT_NAME: str = "TradeGuard"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "tradeguard-insecure-dev-secret-key-change-in-production-32chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tradeguard"
    SYNC_DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/tradeguard"

    # S3 / MinIO Storage
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "tradeguard-documents"
    S3_REGION: str = "us-east-1"

    # Risk Decision Thresholds
    RISK_THRESHOLD_LOW: float = 0.20    # Below this -> AUTO_RELEASE (if no hard rule fails)
    RISK_THRESHOLD_HIGH: float = 0.60   # Above this -> HOLD
    OCR_CONFIDENCE_GATE: float = 0.70   # Below this -> MANUAL_REVIEW
    CLASSIFIER_CONFIDENCE_GATE: float = 0.80 # Below this -> MANUAL_REVIEW

    # Payment Gateway (Sandbox)
    PAYMENT_GATEWAY_PROVIDER: str = "simulated"  # 'simulated' | 'razorpay' | 'stripe'
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""


settings = Settings()

