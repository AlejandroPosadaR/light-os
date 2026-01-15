# Health API

FastAPI application for health data tracking with JWT authentication and Firestore database.

## Prerequisites

**Local Development:**
- Docker and Docker Compose
- Git

**Cloud Run Deployment:**
- Google Cloud SDK
- GCP project with billing enabled

## Setup

```bash
git clone https://github.com/AlejandroPosadaR/light-os.git
cd light-os
```

## Local Development

```bash
docker-compose up
```

API available at http://localhost:8080  
Interactive docs: http://localhost:8080/docs

## Deploy to Cloud Run

### Prerequisites

```bash
# Install gcloud SDK
brew install google-cloud-sdk  # macOS
# Or: https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login
gcloud auth application-default login

# Create project (if you don't have one, you'll need to set up billing for it)
gcloud projects create YOUR_PROJECT_ID --name="Health API"
# Or use existing project:
gcloud config set project YOUR_PROJECT_ID

# Enable APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com \
  firestore.googleapis.com redis.googleapis.com vpcaccess.googleapis.com

# Initialize Firestore (one-time)
gcloud firestore databases create --location=australia-southeast1 --type=firestore-native

# Create composite index (required, ~1-5 min)
gcloud firestore indexes composite create \
  --collection-group=health_data \
  --query-scope=COLLECTION \
  --field-config field-path=user_id,order=ASCENDING \
  --field-config field-path=timestamp,order=ASCENDING \
  --field-config field-path=__name__,order=ASCENDING
```

### Deployment

**Without Redis:**
```bash
gcloud run deploy health-api \
  --source . \
  --region australia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars JWT_SECRET=your-secret-key-change-in-production
```

**With Memorystore Redis:**
```bash
# Create Redis instance (~5-20 min)
gcloud redis instances create health-redis \
  --size=1 \
  --region=australia-southeast1 \
  --redis-version=redis_7_0

# Get Redis IP (run in same terminal)
REDIS_IP=$(gcloud redis instances describe health-redis \
  --region=australia-southeast1 \
  --format="value(host)")

# Create VPC connector (~5-15 min, one-time per region)
gcloud compute networks vpc-access connectors create cr-connector \
  --region=australia-southeast1 \
  --network=default \
  --range=10.8.0.0/28

# Deploy
gcloud run deploy health-api \
  --source . \
  --region australia-southeast1 \
  --allow-unauthenticated \
  --vpc-connector=cr-connector \
  --set-env-vars REDIS_HOST=$REDIS_IP,REDIS_PORT=6379,JWT_SECRET=your-secret-key-change-in-production
```

**Notes:**
- Use Secret Manager for `JWT_SECRET` in production
- Rate limiting is **enabled by default** in production (disabled locally via `DISABLE_RATE_LIMIT=true` in docker-compose.yml)

## Architecture

**Authentication:** JWT tokens, bcrypt password hashing  
**Database:** Firestore (Native mode)  
**Caching:** Redis (optional, local via Docker, production via Memorystore)  
**Security:** Application Default Credentials, IAM-based Firestore access

## Environment Variables

Configured automatically in `docker-compose.yml` for local development.

| Variable | Description | Required |
|----------|-------------|----------|
| `JWT_SECRET` | JWT signing secret | Yes (prod) |
| `REDIS_HOST` | Redis host | No |
| `REDIS_PORT` | Redis port | No (default: 6379) |
| `FIRESTORE_EMULATOR_HOST` | Firestore emulator host | No |
| `GCP_PROJECT_ID` | GCP project ID | No (uses ADC) |
| `DISABLE_RATE_LIMIT` | Disable rate limiting (for testing) | No (default: false, set to "true" to disable) |

## Testing

**Run tests with coverage:**
```bash
docker-compose up -d
docker-compose exec app pytest --cov=app --cov-report=term --cov-report=html
```

**View coverage report:**
```bash
# Terminal output shows coverage summary
# HTML report available at htmlcov/index.html

open htmlcov/index.html  # macOS
# xdg-open htmlcov/index.html  # Linux
```

**Coverage results:**
- **Overall coverage:** 83% (543 statements, 91 missed)
- **Core coverage:** 93% (excluding rate limiter - infrastructure code)
- **66 tests:** 28 integration tests, 38 unit tests
- **Unit tests:** Service layer logic (`tests/unit/`)
- **Integration tests:** Full API endpoint testing (`tests/integration/`)
- **Coverage report:** Generated in `htmlcov/` directory with detailed line-by-line coverage

**Coverage by module:**
| Module | Statements | Missed | Coverage |
|--------|-----------|--------|----------|
| `app/models/user.py` | 30 | 0 | 100% |
| `app/routers/auth.py` | 25 | 0 | 100% |
| `app/routers/health.py` | 31 | 0 | 100% |
| `app/services/user_service.py` | 55 | 0 | 100% |
| `app/dependencies.py` | 49 | 1 | 98% |
| `app/models/health.py` | 38 | 2 | 95% |
| `app/services/health_service.py` | 137 | 11 | 92% |
| `app/main.py` | 25 | 2 | 92% |
| `app/cache.py` | 54 | 10 | 81% |
| `app/database.py` | 12 | 4 | 67% |
| `app/rate_limiter.py` | 83 | 61 | 27% |

## API Endpoints

**Authentication:**
- `POST /auth/register` - Register user
- `POST /auth/login` - Get JWT token
- `GET /auth/me` - Current user info

**Health Data:**
- `POST /users/{user_id}/health-data` - Create entry
- `GET /users/{user_id}/health-data?start=DD-MM-YYYY&end=DD-MM-YYYY` - List entries (paginated)
- `GET /users/{user_id}/summary?start=DD-MM-YYYY&end=DD-MM-YYYY` - Summary statistics

See `/docs` for interactive API documentation.

## Bonus Features

### Caching Layer (Redis/Memorystore)
- **Implementation:** Redis-based caching with versioning for cache invalidation
- **Location:** `app/cache.py` and `app/services/health_service.py`
- **Features:**
  - GET request caching with configurable TTL (5 minutes default)
  - Atomic cache versioning per user for invalidation on writes
  - Graceful degradation when Redis is unavailable
  - Works with local Redis (Docker) and production Memorystore
- **Usage:** Automatic for health data queries; cache invalidated on data writes

### Input Validation & Error Handling
- **Implementation:** FastAPI + Pydantic models with custom validators
- **Features:**
  - Automatic request validation via Pydantic models (`app/models/`)
  - Custom date format validation (DD-MM-YYYY) with descriptive errors
  - Proper HTTP status codes (400, 401, 403, 404, 429)
  - JWT token validation with clear error messages
  - User authorization checks preventing cross-user data access

### Testing
- **Coverage:** Unit and integration tests in `tests/` directory
- **Unit Tests:** Service layer logic (`tests/unit/`)
- **Integration Tests:** Full API endpoint testing (`tests/integration/`)
- **Run:** `pytest --cov=app --cov-report=html`
- **Coverage:** HTML report generated in `htmlcov/`

### Rate Limiting
- **Implementation:** Redis-based token bucket algorithm (`app/rate_limiter.py`)
- **Features:**
  - Atomic operations via Redis Lua scripts
  - Different limits for authenticated (120/min) vs anonymous (30/min) users
  - IP-based tracking for anonymous users, user_id for authenticated
  - Graceful fail-open if Redis unavailable
  - Rate limit headers in responses (`X-RateLimit-Limit`, `X-RateLimit-Window`)
- **Status Code:** 429 Too Many Requests with `Retry-After` header
- **Configuration:** Enabled by default in production. Set `DISABLE_RATE_LIMIT=true` to disable (useful for local testing)

## Project Structure

```
light-os/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── database.py          # Firestore client configuration
│   ├── dependencies.py      # JWT authentication dependencies
│   ├── cache.py             # Redis caching
│   ├── models/              # Pydantic models
│   ├── routers/             # API route handlers
│   └── services/            # Business logic layer
├── tests/
│   ├── unit/                # Unit tests
│   └── integration/         # Integration tests
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Development

### Key Technologies
- **FastAPI**: Web framework
- **Firestore**: NoSQL database
- **JWT**: Authentication
- **Pydantic**: Data validation
- **pytest**: Testing framework

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `docker-compose: command not found` | Install Docker Desktop/Compose |
| `Cannot connect to Docker daemon` | Start Docker Desktop or `sudo systemctl start docker` |
| `gcloud: command not found` | Install gcloud SDK (see Prerequisites) |
| `Your default credentials were not found` | Run `gcloud auth application-default login` |
| Tests failing | Ensure services running: `docker-compose up -d` |
| Port 8080 in use | Modify `docker-compose.yml` or kill process: `lsof -ti:8080 \| xargs kill` |

## License

MIT License

Copyright (c) 2026 Alejandro Posada

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.