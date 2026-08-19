"""Application settings, sourced from environment variables."""
import os


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./shoplive.db")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))
    # Comma-separated list of allowed CORS origins for the web frontend.
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")


settings = Settings()
