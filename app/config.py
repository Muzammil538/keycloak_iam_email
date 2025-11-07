from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", 8080))
    APP_BASE = os.getenv("APP_BASE", "http://localhost:8080")

    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/iam.db")

    # Keycloak
    KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL")
    KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM")
    KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID")
    KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET")

    # SMTP
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASS = os.getenv("SMTP_PASS")

    # Tokens
    TOKEN_SECRET = os.getenv("TOKEN_SECRET", "change_me")
    TOKEN_EXPIRY_SECONDS = int(os.getenv("TOKEN_EXPIRY_SECONDS", 7*24*3600))

    # reminders
    REMINDER_HOURS = int(os.getenv("REMINDER_HOURS", 48))
    REMINDER_CHECK_INTERVAL_MINUTES = int(os.getenv("REMINDER_CHECK_INTERVAL_MINUTES", 60))

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
