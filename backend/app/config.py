import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./brightloop.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me-use-a-long-random-value-in-production")
TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "480"))
RESET_TOKEN_EXPIRE_MINUTES = 30

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# First admin is created on startup if it doesn't exist (dev defaults; override in prod).
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@brightloop.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@12345")

# Optional SMTP. Without SMTP_HOST, emails are logged and kept in an in-memory outbox.
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "billing@brightloop.local")
