import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/taskflow",
    )
    database_sync_url: str = os.getenv(
        "DATABASE_SYNC_URL",
        "postgresql://postgres:postgres@localhost:5432/taskflow",
    )
    secret_key: str = os.getenv("SECRET_KEY", "change-me-in-production-use-a-long-random-string")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expiry_hours: int = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
