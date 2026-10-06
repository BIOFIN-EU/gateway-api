import os

# Settings are read on import: test values, before the app is imported.
os.environ.update({
    "AUTH_URL": "http://auth-api",
    "PHYSICAL_API_URL": "http://physical-api",
    "RISK_API_URL": "http://risk-framework",
    "AUTH_CLIENT_ID": "gateway",
    "AUTH_CLIENT_SECRET": "gateway-secret",
    "INTERNAL_API_SECRET": "internal-secret",
    "JWT_SECRET_KEY": "jwt-secret",
})
