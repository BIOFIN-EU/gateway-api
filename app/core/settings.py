from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- service connections ---
    AUTH_URL: str
    PHYSICAL_API_URL: str
    RISK_API_URL: str

    # --- service-to-service auth ---
    AUTH_CLIENT_ID: str
    AUTH_CLIENT_SECRET: str

    # Shared with physical-api: sent on every request to it, so it knows the
    # request (and the user in X-User-Id) comes from the gateway.
    INTERNAL_API_SECRET: str

    # JWT verification
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    # optional
    SERVICE_NAME: str = "gateway-api"

    class Config:
        env_file = ".env"  # only used if running outside docker
        case_sensitive = True


settings = Settings()
