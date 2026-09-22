# BioFin Dashboard — Gateway API

A reverse-proxy API gateway for the BioFin Dashboard microservices platform. It acts as the single entry point for all client traffic, handling JWT authentication, request routing to upstream services, and unified OpenAPI documentation.

## Architecture

```
Client
  │
  ▼
Gateway API  (port 8000)
  ├── /api/auth/*  ──────────►  Auth API         (port 8010)
  │                              (service-to-service via X-Client-* headers)
  │
  └── /api/*  ───────────────►  Physical Layer API  (port 8020)
                                 (JWT validated; forwards X-User-* identity headers)
```

The gateway enforces authentication for Physical Layer API traffic. Requests to the Auth API are forwarded without end-user authentication, using static service credentials instead.

## Features

- **Reverse proxy** — transparently forwards HTTP requests (all methods) to upstream services
- **JWT authentication** — validates Bearer tokens; extracts `user_id`, `roles`, and `permissions`
- **Identity forwarding** — injects trusted `X-User-Id`, `X-User-Roles`, `X-User-Permissions` headers so downstream services never touch raw JWTs
- **Service-to-service auth** — attaches `X-Client-ID` / `X-Client-Secret` for calls to the Auth service
- **Merged OpenAPI schema** — combines gateway, Auth API, and Physical Layer API schemas at `/openapi.json`
- **CORS** — permissive by default (configurable)
- **Health check** — `GET /status/api_status`

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.128, Starlette 0.49 |
| Server | Uvicorn (dev) / Gunicorn + Uvicorn workers (prod) |
| HTTP client | httpx (async) |
| Auth | python-jose (JWT), HS256 |
| Config | Pydantic Settings, python-dotenv |
| Containerisation | Docker, Docker Compose |
| CI/CD | GitHub Actions → GitHub Container Registry |

## Project Structure

```
gateway-api/
├── app/
│   ├── main.py                        # FastAPI app, lifespan, merged OpenAPI
│   ├── logging_config.py              # Structured console logging
│   ├── core/
│   │   └── settings.py                # Pydantic Settings (env vars)
│   ├── dependencies/
│   │   ├── user_auth.py               # JWT decode, CurrentUser, RBAC helpers
│   │   └── permissions.py             # Permission-check utilities
│   ├── routers/
│   │   ├── endpoints.py               # Router aggregator
│   │   ├── status.py                  # Health check
│   │   ├── auth_proxy.py              # Auth service reverse proxy
│   │   └── physical_layer_proxy.py    # Physical API reverse proxy (auth required)
│   ├── schemas/
│   │   └── auth.py                    # Pydantic request/response models
│   └── services/
│       └── auth_client.py             # Auth API client helpers
├── .env.dev                           # Development environment variables
├── Dockerfile                         # Production container image
├── docker-compose.yaml                # Local development orchestration
├── requirements.txt                   # Python dependencies
├── build-image.sh                     # Local Docker build helper
└── .github/workflows/docker-image.yml # CI/CD pipeline
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- The `biofin_network` external Docker network (shared with Auth API and Physical Layer API)

Create the network if it does not exist:

```bash
docker network create biofin_network
```

### Running locally with Docker Compose

```bash
docker-compose up
```

The gateway starts on `http://localhost:8000` with hot reload enabled. It expects:
- Auth API reachable at `http://auth-api:8010`
- Physical Layer API reachable at `http://physical-api:8020`

### Running without Docker

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Set environment variables as described below before starting.

## Configuration

Environment variables are loaded from `.env.dev` in development. Copy and adjust as needed.

| Variable | Description | Example |
|---|---|---|
| `AUTH_URL` | Base URL of the Auth API | `http://auth-api:8010` |
| `PHYSICAL_API_URL` | Base URL of the Physical Layer API | `http://physical-api:8020` |
| `AUTH_CLIENT_ID` | Client ID sent to Auth API for service auth | `api_gateway` |
| `AUTH_CLIENT_SECRET` | Client secret sent to Auth API for service auth | `<secret>` |
| `JWT_SECRET_KEY` | Shared secret for JWT validation | `<secret>` |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `SERVICE_NAME` | Identifier for this gateway instance | `gateway-api` |

> **Never commit real secrets.** The `.env` and `.env*` patterns are in `../gateway-api-orig/.gitignore`.

## API Endpoints

### Health check

```
GET /status/api_status
→ 200  {"status": "OK"}
```

### Auth service proxy

All requests are forwarded to the Auth API. No end-user authentication is required at the gateway level.

```
{GET,POST,PUT,PATCH,DELETE}  /api/auth/{path}
```

Service credentials (`X-Client-ID`, `X-Client-Secret`) are injected automatically.

### Physical Layer API proxy

Requires a valid JWT `Authorization: Bearer <token>` header. The gateway decodes the token, then forwards the request with identity headers:

| Injected header | Source |
|---|---|
| `X-User-Id` | `sub` claim from JWT |
| `X-User-Roles` | `roles` claim from JWT |
| `X-User-Permissions` | `permissions` claim from JWT |

```
{GET,POST,PUT,PATCH,DELETE}  /api/{path}
```

### OpenAPI / Swagger UI

| Path | Description |
|---|---|
| `GET /openapi.json` | Merged schema (gateway + Auth API + Physical API) |
| `GET /docs` | Swagger UI |

## Authentication Flow

```
1. Client POSTs credentials to  POST /api/auth/login
2. Gateway forwards to Auth API
3. Auth API returns { access_token, refresh_token }
4. Client includes  Authorization: Bearer <access_token>  on subsequent requests
5. Gateway validates JWT locally (no Auth API round-trip)
6. Validated identity is forwarded to Physical API via X-User-* headers
```

Token refresh:

```
POST /api/auth/refresh   { "refresh_token": "..." }
```

## Building the Docker Image

### CI/CD (GitHub Actions)

Pushing to `main` automatically:
1. Builds a multi-platform image (`linux/amd64`, `linux/arm64`)
2. Tags it with a timestamp-based version and `latest`
3. Pushes to `ghcr.io/<owner>/gateway-api`

### Local build

```bash
./build-image.sh 1.2.0
```

The version defaults to `1.0.0` if not provided.

### Production Dockerfile

The production image runs Gunicorn with 4 Uvicorn worker processes:

```
gunicorn -k uvicorn.workers.UvicornWorker app.main:app \
  --bind 0.0.0.0:8000 --workers 4
```

## Development Notes

- The routers use `httpx.AsyncClient` instances created at application startup (FastAPI lifespan) and shared across requests — avoid creating per-request clients.
- Hop-by-hop headers (`Connection`, `Transfer-Encoding`, etc.) are stripped from both outgoing requests and incoming responses.
- Role-based and permission-based access control helpers (`require_role`, `require_permission`) are available in `../gateway-api-orig/app/dependencies/user_auth.py` and can be added as FastAPI dependencies on any route.

## License

Licensed under the [Apache License 2.0](../gateway-api-orig/LICENSE).
