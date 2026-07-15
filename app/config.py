import os

# ---------------------------------------------------------------------------
# SEC-02 FIX: All secrets are sourced from environment variables.
# The fallback values below are intentionally weak/placeholder strings
# that are ONLY acceptable for local development. In production (Kubernetes),
# these are injected from the vulntracker-secret Secret via the Helm chart.
# Never commit real production values here.
# ---------------------------------------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./vulntracker.db")

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-secret-key-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Database credentials — not used by SQLite; present for future Postgres migration
DB_USER = os.environ.get("DB_USER", "vulntracker_app")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "change-me-in-production")

# Internal service API key — passed via env in Kubernetes Secret
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")

NOTIFY_SERVICE_URL = os.environ.get("NOTIFY_SERVICE_URL", "http://localhost:3001")
